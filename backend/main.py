import os
import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import chromadb
import numpy as np
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# --- INICJALIZACJA ---
load_dotenv()

app = FastAPI(title="AI Music Recommender API")

client = chromadb.PersistentClient(path="./music_db")
collection = client.get_collection(name="spotify_tracks")

try:
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope="user-top-read playlist-read-private playlist-read-collaborative"))
except Exception as e:
    print(f"Błąd inicjalizacji Spotify: {e}")
    sp = None

# --- FUNKCJE POMOCNICZE ---
def clean_title(title):
    title = title.split(" - ")[0]
    title = re.sub(r'\(.*?\)', '', title)
    title = re.sub(r'\[.*?\]', '', title)
    return title.strip().lower()

# --- MODELE DANYCH ---
class MoodQuery(BaseModel):
    mood_text: str
    exclude_text: Optional[str] = None
    num_results: int = 5

class ProfileQuery(BaseModel):
    track_ids: List[str]
    exclude_signatures: List[str] = []
    num_results: int = 10

class PlaylistLinkQuery(BaseModel):
    playlist_url: str
    num_results: int = 10

# NOWOŚĆ: Model dla wyszukiwania po profilu zalogowanego użytkownika
class UserProfileQuery(BaseModel):
    time_range: str = "medium_term"  # short_term, medium_term, long_term
    num_results: int = 10

# --- ENDPOINTY ---

@app.get("/")
def read_root():
    return {"status": "AI Engine is running", "tracks_in_db": collection.count()}

@app.post("/api/recommend/mood")
def recommend_by_mood(query: MoodQuery):
    query_kwargs = {"query_texts": [query.mood_text], "n_results": query.num_results}
    if query.exclude_text:
        bad_words = [w.strip().lower() for w in query.exclude_text.split(",") if w.strip()]
        if len(bad_words) == 1:
            query_kwargs["where_document"] = {"$not_contains": bad_words[0]}
        elif len(bad_words) > 1:
            query_kwargs["where_document"] = {"$and": [{"$not_contains": word} for word in bad_words]}

    results = collection.query(**query_kwargs)
    recommendations = []
    if results['ids'] and len(results['ids']) > 0:
        for i in range(len(results['ids'][0])):
            recommendations.append({
                "id": results['ids'][0][i],
                "artist": results['metadatas'][0][i]['artist'],
                "title": results['metadatas'][0][i]['title'],
                "distance": float(results['distances'][0][i])
            })
    return {"query": query.mood_text, "excluded": query.exclude_text, "recommendations": recommendations}

@app.post("/api/recommend/profile")
def recommend_by_profile(query: ProfileQuery):
    data = collection.get(ids=query.track_ids, include=["embeddings", "metadatas"])
    embeddings = data.get("embeddings")
    
    if embeddings is None or len(embeddings) == 0:
        raise HTTPException(status_code=404, detail="Żaden z utworów z Twojego profilu/playlisty nie znajduje się jeszcze w bazie ChromaDB. Użyj najpierw loadera, aby zasilić bazę utworami.")
        
    taste_vector = np.mean(embeddings, axis=0).tolist()
    safe_n_results = min((query.num_results * 2) + len(query.track_ids), collection.count())
    
    if safe_n_results == 0:
        raise HTTPException(status_code=400, detail="Baza danych jest pusta!")

    results = collection.query(query_embeddings=[taste_vector], n_results=safe_n_results)
    
    recommendations = []
    if results['ids'] and len(results['ids']) > 0:
        for i in range(len(results['ids'][0])):
            rec_id = results['ids'][0][i]
            rec_artist = results['metadatas'][0][i]['artist']
            rec_title = results['metadatas'][0][i]['title']
            
            rec_sig = f"{rec_artist.lower().strip()} - {clean_title(rec_title)}"
            
            if rec_id in query.track_ids: continue
            if rec_sig in query.exclude_signatures: continue
            
            recommendations.append({
                "id": rec_id,
                "artist": rec_artist,
                "title": rec_title,
                "distance": float(results['distances'][0][i])
            })
            if len(recommendations) == query.num_results: break
                
    return {"analyzed_tracks_count": len(embeddings), "recommendations": recommendations}

@app.post("/api/recommend/playlist-link")
def recommend_by_playlist_link(query: PlaylistLinkQuery):
    if not sp: raise HTTPException(status_code=500, detail="Spotify API nie jest skonfigurowane.")
    try:
        playlist_id = query.playlist_url.split("/")[-1].split("?")[0]
    except Exception:
        raise HTTPException(status_code=400, detail="Nieprawidłowy format linku.")

    try:
        all_items = []
        results = sp.playlist_items(playlist_id, limit=100)
        all_items.extend(results.get('items', []))
        while results.get('next'):
            results = sp.next(results)
            all_items.extend(results.get('items', []))
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Błąd API Spotify: {e}")

    track_ids, exclude_sigs = [], []
    for list_item in all_items:
        track = list_item.get('track') or list_item.get('item')
        if not track or not isinstance(track, dict) or track.get('is_local'): continue
        track_id = track.get('id')
        if not track_id: continue
        
        track_ids.append(track_id)
        artist_name = track['artists'][0]['name'] if track.get('artists') else ""
        exclude_sigs.append(f"{artist_name.lower().strip()} - {clean_title(track.get('name', ''))}")

    if not track_ids: raise HTTPException(status_code=404, detail="Playlista jest pusta.")
    return recommend_by_profile(ProfileQuery(track_ids=track_ids, exclude_signatures=exclude_sigs, num_results=query.num_results))

# --- NOWY ENDPOINT: REKOMENDACJA NA PODSTAWIE PROFILU UŻYTKOWNIKA ---
@app.post("/api/recommend/user-profile")
def recommend_by_user_profile(query: UserProfileQuery):
    if not sp:
        raise HTTPException(status_code=500, detail="Spotify API nie jest skonfigurowane w pliku .env")
        
    # Walidacja przekazanego okresu czasu
    if query.time_range not in ["short_term", "medium_term", "long_term"]:
        raise HTTPException(status_code=400, detail="time_range musi być jednym z: short_term, medium_term, long_term")

    print(f"\n--- ANALIZA PROFILU UŻYTKOWNIKA ({query.time_range}) ---")

    # 1. Pobieramy top 50 utworów zalogowanego użytkownika ze Spotify
    try:
        results = sp.current_user_top_tracks(limit=50, time_range=query.time_range)
        items = results.get('items', [])
    except Exception as e:
        print(f"Błąd pobierania profilu: {e}")
        raise HTTPException(status_code=400, detail=f"Błąd API Spotify podczas odczytu profilu: {e}")

    print(f"Spotify zwróciło {len(items)} najpopularniejszych utworów użytkownika.")

    track_ids = []
    exclude_sigs = []

    # 2. Budujemy listy ID oraz tekstowych sygnatur wykluczeń (Ghost IDs)
    for track in items:
        if not track or track.get('is_local'): 
            continue
        track_id = track.get('id')
        if not track_id: 
            continue
            
        track_ids.append(track_id)
        artist_name = track['artists'][0]['name'] if track.get('artists') else ""
        sig = f"{artist_name.lower().strip()} - {clean_title(track.get('name', ''))}"
        exclude_sigs.append(sig)

    if not track_ids:
        raise HTTPException(status_code=404, detail="Twój profil Spotify nie zwrócił żadnych utworów dla tego okresu.")

    print(f"Wyodrębniono {len(track_ids)} utworów do stworzenia Wektora Gustu.")

    # 3. Przekazujemy zebrane utwory użytkownika do naszego silnika wektorowego
    return recommend_by_profile(ProfileQuery(
        track_ids=track_ids,
        exclude_signatures=exclude_sigs,
        num_results=query.num_results
    ))