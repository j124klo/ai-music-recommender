from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from typing import List
import chromadb
import numpy as np

app = FastAPI(title="AI Music Recommender API")

# Połączenie z bazą przy starcie serwera
client = chromadb.PersistentClient(path="./music_db")
collection = client.get_collection(name="spotify_tracks")

# --- MODELE DANYCH (Co frontend wysyła do serwera) ---
class MoodQuery(BaseModel):
    mood_text: str
    num_results: int = 5

class ProfileQuery(BaseModel):
    track_ids: List[str]  # Lista identyfikatorów Spotify (np. z ulubionej playlisty)
    num_results: int = 10 # Domyślnie zwracamy 10 propozycji

# --- ENDPOINTY (Trasy API) ---

@app.get("/")
def read_root():
    return {"status": "AI Engine is running", "tracks_in_db": collection.count()}

@app.post("/api/recommend/mood")
def recommend_by_mood(query: MoodQuery):
    """
    Rekomendacja na podstawie wpisanego nastroju / gatunku (tekst).
    """
    results = collection.query(
        query_texts=[query.mood_text],
        n_results=query.num_results
    )
    
    recommendations = []
    for i in range(len(results['ids'][0])):
        recommendations.append({
            "id": results['ids'][0][i],
            "artist": results['metadatas'][0][i]['artist'],
            "title": results['metadatas'][0][i]['title'],
            "distance": float(results['distances'][0][i])
        })
        
    return {"query": query.mood_text, "recommendations": recommendations}

@app.post("/api/recommend/profile")
def recommend_by_profile(query: ProfileQuery):
    """
    Rekomendacja hybrydowa na podstawie uśrednionego wektora gustu (np. z playlisty).
    """
    # 1. Pobieramy osadzenia (wektory) dla przekazanych ID utworów
    data = collection.get(
        ids=query.track_ids,
        include=["embeddings", "metadatas"]
    )
    
    embeddings = data.get("embeddings")
    
    # ZABEZPIECZENIE 1: Zmieniony warunek sprawdzania pustych wektorów (naprawa ValueError)
    if embeddings is None or len(embeddings) == 0:
        raise HTTPException(status_code=404, detail="Nie znaleziono podanych utworów w bazie. Najpierw dodaj je loaderem.")
        
    # 2. Obliczamy ŚREDNI WEKTOR GUSTU (Serce naszego systemu!)
    # Zamieniamy wszystkie wektory piosenek z playlisty w jeden punkt w przestrzeni AI
    taste_vector = np.mean(embeddings, axis=0).tolist()
    
    # ZABEZPIECZENIE 2: Sprawdzamy rozmiar bazy (ochrona przed błędem zbyt małej bazy)
    db_size = collection.count()
    requested_results = query.num_results + len(query.track_ids)
    safe_n_results = min(requested_results, db_size)
    
    if safe_n_results == 0:
        raise HTTPException(status_code=400, detail="Baza danych jest całkowicie pusta!")

    # 3. Szukamy w bazie utworów znajdujących się najbliżej uśrednionego punktu
    results = collection.query(
        query_embeddings=[taste_vector],
        n_results=safe_n_results 
    )
    
    recommendations = []
    # Sprawdzamy czy ChromaDB w ogóle zwróciła jakiekolwiek 'ids'
    if results['ids'] and len(results['ids']) > 0:
        for i in range(len(results['ids'][0])):
            rec_id = results['ids'][0][i]
            
            # Filtrujemy utwory, które były danymi wejściowymi
            if rec_id in query.track_ids:
                continue
                
            recommendations.append({
                "id": rec_id,
                "artist": results['metadatas'][0][i]['artist'],
                "title": results['metadatas'][0][i]['title'],
                "distance": float(results['distances'][0][i])
            })
            
            # Jeśli zebraliśmy już tyle unikalnych rekomendacji, ile chciał użytkownik - przerywamy
            if len(recommendations) == query.num_results:
                break
            
    return {
        "analyzed_tracks_count": len(embeddings),
        "recommendations": recommendations
    }