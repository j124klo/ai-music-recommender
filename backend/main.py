import os
import re
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List, Optional
import chromadb
from chromadb.utils import embedding_functions
import numpy as np
from sklearn.cluster import KMeans
from sklearn.metrics import silhouette_score
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import warnings
warnings.filterwarnings("ignore") # Wyłączamy ostrzeżenia scikit-learn

# --- INICJALIZACJA ---
load_dotenv()
app = FastAPI(title="AI Music Recommender API")

from fastapi.middleware.cors import CORSMiddleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"], 
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music_db")

sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)

client = chromadb.PersistentClient(path=db_path)
collection = client.get_or_create_collection(name="spotify_tracks", embedding_function=sentence_transformer_ef)

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
    num_results: int = 12 # Domyślnie proponujemy np 12, aby łatwo dzieliło się przez klastry

class PlaylistLinkQuery(BaseModel):
    playlist_url: str
    num_results: int = 12

class UserProfileQuery(BaseModel):
    time_range: str = "medium_term"  
    num_results: int = 12

# --- ENDPOINTY ---

@app.get("/")
def read_root():
    return {
        "status": "online",
        "message": "AI Music Recommender Engine is running",
        "system_health": {
            "database": {
                "tracks_count": collection.count(),
                "db_path": db_path,
                "status": "ok" if collection.count() > 0 else "empty"
            },
            "spotify_api": {
                "status": "connected" if sp else "disconnected",
                "warning": "Check .env file" if not sp else None
            },
            "ai_engine": {
                "embedding_model": "paraphrase-multilingual-MiniLM-L12-v2",
                "clustering_algorithm": "K-Means (Dynamic with Silhouette Score)"
            }
        }
    }

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
            
    # Ujednolicamy format odpowiedzi do frontendu (Dla mood mamy tylko 1 "pusty" klaster)
    return {
        "query": query.mood_text, 
        "analyzed_tracks_count": 1,
        "clusters": [{"cluster_id": None, "recommendations": recommendations}]
    }

@app.post("/api/recommend/profile")
def recommend_by_profile(query: ProfileQuery):
    data = collection.get(ids=query.track_ids, include=["embeddings", "metadatas"])
    
    retrieved_ids = data.get("ids")
    retrieved_embeddings = data.get("embeddings")
    
    # PANCERNE ZABEZPIECZENIE (Naprawia błąd ValueError z tablicami Numpy)
    if retrieved_embeddings is None or len(retrieved_embeddings) == 0:
        raise HTTPException(status_code=404, detail="Brak Twoich utworów w bazie ChromaDB.")
        
    emb_dict = {id_: emb for id_, emb in zip(retrieved_ids, retrieved_embeddings)}
    ordered_embeddings = []
    weights = []
    
    for i, t_id in enumerate(query.track_ids):
        if t_id in emb_dict:
            ordered_embeddings.append(emb_dict[t_id])
            weights.append(max(0.2, 1.0 - (i / len(query.track_ids))))
            
    ordered_embeddings = np.array(ordered_embeddings)
    
    # --- DYNAMICZNE WYZNACZANIE KLASTRÓW (Silhouette Score) ---
    max_k = min(5, len(ordered_embeddings) - 1)
    best_k = 1
    best_kmeans = None
    best_score = -1
    
    if max_k >= 2:
        for k in range(2, max_k + 1):
            kmeans = KMeans(n_clusters=k, random_state=42, n_init="auto")
            labels = kmeans.fit_predict(ordered_embeddings, sample_weight=weights)
            
            # Algorytm sylwetki wymaga co najmniej 2 klas
            if len(set(labels)) > 1:
                score = silhouette_score(ordered_embeddings, labels)
                if score > best_score:
                    best_score = score
                    best_k = k
                    best_kmeans = kmeans
        
        # Jeśli najwyższy wynik jest mniejszy niż 0.1, zbiór jest na tyle spójny, że nie ma sensu go dzielić
        if best_score < 0.1:
            best_k = 1

    if best_k > 1:
        cluster_centers = best_kmeans.cluster_centers_.tolist()
    else:
        cluster_centers = [np.average(ordered_embeddings, axis=0, weights=weights).tolist()]

    # Odpytywanie bazy
    safe_n_results = min(100, collection.count())
    results = collection.query(
        query_embeddings=cluster_centers, 
        n_results=safe_n_results
    )
    
    response_clusters = []
    seen_ids = set(query.track_ids)
    # Śledzimy też sygnatury tekstowe (Wykonawca - Tytuł), aby uniknąć różnych wersji tej samej piosenki!
    seen_sigs = set(query.exclude_signatures)
    
    # Równy podział wyników na liczbę klastrów
    results_per_cluster = max(1, query.num_results // len(cluster_centers))
    remaining = query.num_results % len(cluster_centers)
    
    for cluster_idx in range(len(cluster_centers)):
        if not results['ids'] or len(results['ids']) <= cluster_idx:
            continue
            
        cluster_recs = []
        target_count = results_per_cluster + (1 if cluster_idx < remaining else 0)
            
        for i in range(len(results['ids'][cluster_idx])):
            if len(cluster_recs) >= target_count:
                break # Mamy już odpowiednią liczbę piosenek dla tego klastra
                
            rec_id = results['ids'][cluster_idx][i]
            rec_artist = results['metadatas'][cluster_idx][i]['artist']
            rec_title = results['metadatas'][cluster_idx][i]['title']
            
            rec_sig = f"{rec_artist.lower().strip()} - {clean_title(rec_title)}"
            
            # Weryfikacja duplikatów wewnątrz bazy (ten sam utwór, inne ID)
            if rec_id in seen_ids or rec_sig in seen_sigs: 
                continue
                
            cluster_recs.append({
                "id": rec_id,
                "artist": rec_artist,
                "title": rec_title,
                "distance": float(results['distances'][cluster_idx][i]),
            })
            
            seen_ids.add(rec_id)
            seen_sigs.add(rec_sig)

        # Sortujemy utwory W RAMACH jednego klastra
        cluster_recs.sort(key=lambda x: x["distance"])
        
        response_clusters.append({
            "cluster_id": cluster_idx + 1 if best_k > 1 else None,
            "recommendations": cluster_recs
        })
                
    return {"analyzed_tracks_count": len(ordered_embeddings), "clusters": response_clusters}

@app.post("/api/recommend/playlist-link")
def recommend_by_playlist_link(query: PlaylistLinkQuery):
    if not sp: raise HTTPException(status_code=500, detail="Spotify API nie jest skonfigurowane.")
    try:
        playlist_id = query.playlist_url.split("/")[-1].split("?")[0]
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
        if track_id := track.get('id'):
            track_ids.append(track_id)
            artist_name = track['artists'][0]['name'] if track.get('artists') else ""
            exclude_sigs.append(f"{artist_name.lower().strip()} - {clean_title(track.get('name', ''))}")

    if not track_ids: raise HTTPException(status_code=404, detail="Playlista jest pusta.")
    return recommend_by_profile(ProfileQuery(track_ids=track_ids, exclude_signatures=exclude_sigs, num_results=query.num_results))

@app.post("/api/recommend/user-profile")
def recommend_by_user_profile(query: UserProfileQuery):
    if not sp: raise HTTPException(status_code=500, detail="Spotify API nie jest skonfigurowane")
    try:
        results = sp.current_user_top_tracks(limit=50, time_range=query.time_range)
        items = results.get('items', [])
    except Exception as e:
        raise HTTPException(status_code=400, detail=f"Błąd API Spotify: {e}")

    track_ids, exclude_sigs = [], []
    for track in items:
        if not track or track.get('is_local'): continue
        if track_id := track.get('id'):
            track_ids.append(track_id)
            artist_name = track['artists'][0]['name'] if track.get('artists') else ""
            exclude_sigs.append(f"{artist_name.lower().strip()} - {clean_title(track.get('name', ''))}")

    if not track_ids: raise HTTPException(status_code=404, detail="Brak utworów w profilu.")
    return recommend_by_profile(ProfileQuery(track_ids=track_ids, exclude_signatures=exclude_sigs, num_results=query.num_results))