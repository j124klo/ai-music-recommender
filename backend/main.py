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
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope="playlist-read-private playlist-read-collaborative user-top-read"))
except Exception as e:
    print(f"Błąd inicjalizacji Spotify: {e}")
    sp = None

# --- FUNKCJE POMOCNICZE ---
def clean_title(title):
    """Usuwa radiowe śmieci z tytułów (zgodnie z loaderem)"""
    title = title.split(" - ")[0]
    title = re.sub(r'\(.*?\)', '', title)
    title = re.sub(r'\[.*?\]', '', title)
    return title.strip().lower()

# --- MODELE DANYCH ---
class MoodQuery(BaseModel):
    mood_text: str
    exclude_text: Optional[str] = None  # NOWOŚĆ: Pole na słowa wykluczone (opcjonalne)
    num_results: int = 5

class ProfileQuery(BaseModel):
    track_ids: List[str]
    exclude_signatures: List[str] = [] # NOWOŚĆ: Lista tekstowych sygnatur do wykluczenia
    num_results: int = 10

class PlaylistLinkQuery(BaseModel):
    playlist_url: str
    num_results: int = 10

# --- ENDPOINTY ---

@app.get("/")
def read_root():
    return {"status": "AI Engine is running", "tracks_in_db": collection.count()}

@app.post("/api/recommend/mood")
def recommend_by_mood(query: MoodQuery):
    # 1. Przygotowujemy podstawowe parametry wyszukiwania
    query_kwargs = {
        "query_texts": [query.mood_text],
        "n_results": query.num_results
    }
    
    # 2. Jeśli użytkownik wpisał, czego NIE chce - budujemy filtr!
    if query.exclude_text:
        # Dzielimy wpisany tekst po przecinkach i czyścimy ze spacji (np. "metal, smutne")
        bad_words = [w.strip().lower() for w in query.exclude_text.split(",") if w.strip()]
        
        # ChromaDB wymaga specjalnej składni do filtrowania ($not_contains)
        if len(bad_words) == 1:
            query_kwargs["where_document"] = {"$not_contains": bad_words[0]}
        elif len(bad_words) > 1:
            # Jeśli słów jest więcej, używamy operatora logicznego $and
            query_kwargs["where_document"] = {
                "$and": [{"$not_contains": word} for word in bad_words]
            }

    # 3. Wykonujemy zapytanie do bazy z dynamicznie zbudowanymi parametrami
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
        raise HTTPException(status_code=404, detail="Nie znaleziono podanych utworów w bazie.")
        
    taste_vector = np.mean(embeddings, axis=0).tolist()
    
    # Pobieramy z zapasem, bo filtracja sygnatur może odrzucić sporo piosenek
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
            
            # Tworzymy sygnaturę rekomendacji
            rec_sig = f"{rec_artist.lower().strip()} - {clean_title(rec_title)}"
            
            # ZABEZPIECZENIE 1: Zwykłe ID
            if rec_id in query.track_ids: 
                continue
                
            # ZABEZPIECZENIE 2: Nazwa artysty i tytuł (Ochrona przed Ghost IDs)
            if rec_sig in query.exclude_signatures:
                continue
            
            recommendations.append({
                "id": rec_id,
                "artist": rec_artist,
                "title": rec_title,
                "distance": float(results['distances'][0][i])
            })
            
            if len(recommendations) == query.num_results: 
                break
                
    return {"analyzed_tracks_count": len(embeddings), "recommendations": recommendations}

@app.post("/api/recommend/playlist-link")
def recommend_by_playlist_link(query: PlaylistLinkQuery):
    if not sp:
        raise HTTPException(status_code=500, detail="Spotify API nie jest skonfigurowane w pliku .env")
        
    print("\n--- ANALIZA PLAYLISTY SPOTIFY ---")
    
    try:
        playlist_id = query.playlist_url.split("/")[-1].split("?")[0]
        print(f"Wycięte ID playlisty: {playlist_id}")
    except Exception:
        raise HTTPException(status_code=400, detail="Nieprawidłowy format linku.")

    # PAGINACJA: Pobieramy wszystkie piosenki, żeby zbudować pełną listę wykluczeń
    try:
        all_items = []
        results = sp.playlist_items(playlist_id, limit=100)
        all_items.extend(results.get('items', []))
        
        while results.get('next'):
            results = sp.next(results)
            all_items.extend(results.get('items', []))
            
    except Exception as e:
        print(f"Błąd odpytywania Spotify API: {e}")
        raise HTTPException(status_code=400, detail=f"Błąd API Spotify: {e}")

    track_ids = []
    exclude_sigs = [] # Lista na nasze tekstowe sygnatury
    
    print(f"Spotify zwróciło łącznie {len(all_items)} elementów na playliście.")
    
    for list_item in all_items:
        track = list_item.get('track') or list_item.get('item')
        if not track or not isinstance(track, dict): 
            continue
            
        track_id = track.get('id')
        if not track_id or track.get('is_local'):
            continue
            
        track_ids.append(track_id)
        
        # Wyciągamy artystę i tworzymy sygnaturę do wykluczenia
        artist_name = track['artists'][0]['name'] if track.get('artists') else ""
        title = track.get('name', "")
        sig = f"{artist_name.lower().strip()} - {clean_title(title)}"
        exclude_sigs.append(sig)

    print(f"Zbudowano listę wykluczeń (Ghost IDs) dla {len(exclude_sigs)} utworów.")

    if not track_ids:
        raise HTTPException(status_code=404, detail="Playlista jest pusta lub zawiera wyłącznie pliki lokalne (bez ID).")

    # Przekazujemy oba sita bezpieczeństwa (ID oraz tekstowe)
    return recommend_by_profile(ProfileQuery(
        track_ids=track_ids, 
        exclude_signatures=exclude_sigs,
        num_results=query.num_results
    ))