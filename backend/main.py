import os
import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import chromadb
from chromadb.utils import embedding_functions
import numpy as np
from sklearn.cluster import KMeans
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# --- INICJALIZACJA ---
load_dotenv()

app = FastAPI(title="AI Music Recommender API")

from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], # Pozwala na łączenie się dowolnego frontendu (np. z portu 5173)
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicjalizacja wielojęzycznego modelu AI dla wektorów
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music_db")
client = chromadb.PersistentClient(path=db_path)
collection = client.get_or_create_collection(
    name="spotify_tracks",
    embedding_function=sentence_transformer_ef
)

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
    retrieved_ids = data.get("ids", [])
    retrieved_embeddings = data.get("embeddings", [])
    
    if retrieved_embeddings is None or len(retrieved_embeddings) == 0:
        raise HTTPException(status_code=404, detail="Żaden z utworów z Twojego profilu/playlisty nie znajduje się jeszcze w bazie ChromaDB. Użyj najpierw loadera, aby zasilić bazę utworami.")
        
    # Budowanie słownika dla zachowania oryginalnej kolejności i przypisania wag
    emb_dict = {id_: emb for id_, emb in zip(retrieved_ids, retrieved_embeddings)}
    
    ordered_embeddings = []
    weights = []
    
    # Przypisywanie wag (wyższe na liście = większa waga)
    for i, t_id in enumerate(query.track_ids):
        if t_id in emb_dict:
            ordered_embeddings.append(emb_dict[t_id])
            weight = max(0.2, 1.0 - (i / len(query.track_ids)))
            weights.append(weight)
            
    ordered_embeddings = np.array(ordered_embeddings)
    
    # Zabezpieczenie przed zbyt małą liczbą próbek do klastrowania
    n_clusters = min(3, len(ordered_embeddings))
    
    if n_clusters > 1:
        kmeans = KMeans(n_clusters=n_clusters, random_state=42, n_init="auto")
        kmeans.fit(ordered_embeddings, sample_weight=weights)
        cluster_centers = kmeans.cluster_centers_.tolist()
    else:
        # Fallback jeśli mamy tylko 1 utwór
        cluster_centers = [np.average(ordered_embeddings, axis=0, weights=weights).tolist()]

    # Odpytywanie dla każdego z klastrów
    results_per_cluster = max(1, (query.num_results * 2) // n_clusters)
    safe_n_results = min(results_per_cluster + len(query.track_ids), collection.count())
    
    if collection.count() == 0:
        raise HTTPException(status_code=400, detail="Baza danych jest pusta!")

    results = collection.query(
        query_embeddings=cluster_centers, 
        n_results=safe_n_results
    )
    
    all_recommendations = []
    seen_ids = set(query.track_ids)
    
    # Zbieranie unikalnych wyników z wielu klastrów
    for cluster_idx in range(len(cluster_centers)):
        if not results['ids'] or len(results['ids']) <= cluster_idx:
            continue
            
        for i in range(len(results['ids'][cluster_idx])):
            rec_id = results['ids'][cluster_idx][i]
            rec_artist = results['metadatas'][cluster_idx][i]['artist']
            rec_title = results['metadatas'][cluster_idx][i]['title']
            
            rec_sig = f"{rec_artist.lower().strip()} - {clean_title(rec_title)}"
            
            if rec_id in seen_ids or rec_sig in query.exclude_signatures: 
                continue
                
            all_recommendations.append({
                "id": rec_id,
                "artist": rec_artist,
                "title": rec_title,
                "distance": float(results['distances'][cluster_idx][i])
            })
            seen_ids.add(rec_id)

    # Sortowanie poległości względem poszczególnych klastrów (im mniej tym lepiej)
    all_recommendations.sort(key=lambda x: x["distance"])
    
    final_recommendations = all_recommendations[:query.num_results]
                
    return {"analyzed_tracks_count": len(ordered_embeddings), "recommendations": final_recommendations}

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

@app.post("/api/recommend/user-profile")
def recommend_by_user_profile(query: UserProfileQuery):
    if not sp:
        raise HTTPException(status_code=500, detail="Spotify API nie jest skonfigurowane w pliku .env")
        
    if query.time_range not in ["short_term", "medium_term", "long_term"]:
        raise HTTPException(status_code=400, detail="time_range musi być jednym z: short_term, medium_term, long_term")

    print(f"\n--- ANALIZA PROFILU UŻYTKOWNIKA ({query.time_range}) ---")

    try:
        results = sp.current_user_top_tracks(limit=50, time_range=query.time_range)
        items = results.get('items', [])
    except Exception as e:
        print(f"Błąd pobierania profilu: {e}")
        raise HTTPException(status_code=400, detail=f"Błąd API Spotify podczas odczytu profilu: {e}")

    print(f"Spotify zwróciło {len(items)} najpopularniejszych utworów użytkownika.")

    track_ids = []
    exclude_sigs = []

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

    return recommend_by_profile(ProfileQuery(
        track_ids=track_ids,
        exclude_signatures=exclude_sigs,
        num_results=query.num_results
    ))