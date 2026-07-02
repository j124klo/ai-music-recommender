import os
import time
import re
import requests
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import chromadb
from chromadb.utils import embedding_functions

# =====================================================================
#                          KONFIGURACJA
# =====================================================================
load_dotenv()
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    scope="user-top-read playlist-read-private playlist-read-collaborative",
    open_browser=False
))

# Nowy, wielojęzyczny model NLP
sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name="paraphrase-multilingual-MiniLM-L12-v2"
)

db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music_db")
client = chromadb.PersistentClient(path=db_path)
collection = client.get_or_create_collection(
    name="spotify_tracks",
    embedding_function=sentence_transformer_ef
)

# =====================================================================
#                          FUNKCJE POMOCNICZE
# =====================================================================

def load_banned_tags(filepath="banned_tags.txt"):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return [line.strip().lower() for line in f if line.strip()]
    except FileNotFoundError:
        return []

def clean_title(title):
    title = title.split(" - ")[0]
    title = re.sub(r'\(.*?\)', '', title)
    title = re.sub(r'\[.*?\]', '', title)
    return title.strip().lower()

def get_lastfm_tags(artist, track):
    base_url = "http://ws.audioscrobbler.com/2.0/"
    params = {"method": "track.getTopTags", "artist": artist, "track": track, "api_key": LASTFM_API_KEY, "format": "json"}
    try:
        resp = requests.get(base_url, params=params).json()
        tags = [t['name'].lower() for t in resp.get('toptags', {}).get('tag', [])]
        if tags: return tags
    except: pass
    
    params = {"method": "artist.getTopTags", "artist": artist, "api_key": LASTFM_API_KEY, "format": "json"}
    try:
        resp = requests.get(base_url, params=params).json()
        return [t['name'].lower() for t in resp.get('toptags', {}).get('tag', [])]
    except: pass
    return []

def get_existing_signatures():
    try:
        existing_data = collection.get(include=["metadatas"])
        signatures = set()
        if existing_data and existing_data.get('metadatas'):
            for meta in existing_data['metadatas']:
                if meta:
                    sig = f"{meta['artist'].lower().strip()} - {clean_title(meta['title'])}"
                    signatures.add(sig)
        return signatures
    except Exception:
        return set()

# =====================================================================
#                          GŁÓWNY PROCES LOADERA
# =====================================================================
if __name__ == "__main__":
    print("========================================")
    print("      USER PROFILE TO CHROMA LOADER     ")
    print("========================================\n")

    banned_tags = load_banned_tags()
    existing_signatures = get_existing_signatures()
    print(f"Baza zawiera obecnie {len(existing_signatures)} unikalnych utworów.\n")

    time_ranges = ["short_term", "medium_term", "long_term"]
    unique_tracks = {}

    print("Łączenie z Twoim kontem Spotify...")
    
    for tr in time_ranges:
        print(f"Pobieranie top 50 utworów z okresu: {tr}...")
        try:
            results = sp.current_user_top_tracks(limit=50, time_range=tr)
            for track in results.get('items', []):
                if track and not track.get('is_local') and track.get('id'):
                    unique_tracks[track['id']] = track
        except Exception as e:
            print(f"Błąd podczas pobierania {tr}: {e}")

    selected_items = list(unique_tracks.values())
    print(f"\nZnaleziono {len(selected_items)} UNIKALNYCH ulubionych utworów na Twoim profilu (po usunięciu powtórek).\n")

    docs_to_insert = []
    metadatas_to_insert = []
    ids_to_insert = []

    print("Rozpoczynam analizę i odpytywanie Last.fm...\n")

    for i, track in enumerate(selected_items):
        raw_title = track.get('name', 'Nieznany tytuł')
        artists = track.get('artists', [])
        if not artists: continue
        
        artist_name = artists[0].get('name', 'Nieznany artysta')
        track_id = track.get('id')
        
        # Pobieranie roku z albumu na Spotify
        album = track.get('album', {})
        year = album.get('release_date', '')[:4] if album.get('release_date') else 'Brak'
        
        sig = f"{artist_name.lower().strip()} - {clean_title(raw_title)}"
        print(f"[{i+1}/{len(selected_items)}] {artist_name} - {raw_title}")
        
        if sig in existing_signatures:
            print("   -> Pomijam (Utwór już istnieje w bazie!)")
            continue
            
        tags = get_lastfm_tags(artist_name, clean_title(raw_title))
        time.sleep(0.2) 
        
        valid_tags = [t for t in tags if t not in banned_tags and len(t.split()) <= 3][:10]
        
        if not valid_tags:
            print("   -> Pomijam (brak wartościowych tagów)")
            continue

        tags_string = ", ".join(valid_tags)
        
        # Tworzenie wzbogaconego zdania
        document_text = f"Wykonawca: {artist_name}. Rok wydania: {year}. Gatunki i klimat: {tags_string}."
        
        docs_to_insert.append(document_text)
        metadatas_to_insert.append({"artist": artist_name, "title": raw_title, "spotify_id": track_id})
        ids_to_insert.append(track_id)
        
        existing_signatures.add(sig) 

    if docs_to_insert:
        print(f"\nRozpoczynam zapis {len(docs_to_insert)} Twoich ulubionych utworów do bazy ChromaDB...")
        collection.upsert(
            documents=docs_to_insert,
            metadatas=metadatas_to_insert,
            ids=ids_to_insert
        )
        print(f"\nSukces! Twój gust muzyczny został wczytany do silnika AI!")
    else:
        print("\nNie dodano nowych danych. Wygląda na to, że wszystkie Twoje topowe utwory były już w bazie!")