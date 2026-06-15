from fastapi import FastAPI
from pydantic import BaseModel
import chromadb

app = FastAPI(title="AI Music Recommender API")

# Połączenie z bazą przy starcie serwera
client = chromadb.PersistentClient(path="./music_db")
collection = client.get_collection(name="spotify_tracks")

# Model danych wejściowych dla zapytania słownego
class MoodQuery(BaseModel):
    mood_text: str
    num_results: int = 5

@app.get("/")
def read_root():
    return {"status": "AI Engine is running", "tracks_in_db": collection.count()}

@app.post("/api/recommend/mood")
def recommend_by_mood(query: MoodQuery):
    """
    Odpowiednik starego recommender.py - zwraca rekomendacje po wpisanym tekście.
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

# W przyszłości dodamy tu: @app.post("/api/recommend/profile")