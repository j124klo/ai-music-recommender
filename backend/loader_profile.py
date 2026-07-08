import os
import time
import re
import requests
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import chromadb
from chromadb.utils import embedding_functions
import config

# =====================================================================
#                          CONFIGURATION
# =====================================================================
load_dotenv()
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(
    scope="user-top-read playlist-read-private playlist-read-collaborative",
    open_browser=False
))

sentence_transformer_ef = embedding_functions.SentenceTransformerEmbeddingFunction(
    model_name=config.MODEL_NAME 
)

client = chromadb.PersistentClient(path=config.DB_PATH)
collection = client.get_or_create_collection(
    name=config.COLLECTION_NAME,
    embedding_function=sentence_transformer_ef
)

# =====================================================================
#                          HELPER FUNCTIONS
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
#                          MAIN LOADER PROCESS
# =====================================================================
if __name__ == "__main__":
    print("========================================")
    print("      USER PROFILE TO CHROMA LOADER     ")
    print("========================================\n")

    banned_tags = load_banned_tags()
    existing_signatures = get_existing_signatures()
    print(f"The database currently contains {len(existing_signatures)} unique tracks.\n")

    time_ranges = ["short_term", "medium_term", "long_term"]
    unique_tracks = {}

    print("Connecting to your Spotify account...")
    
    for tr in time_ranges:
        print(f"Fetching top 50 tracks for time range: {tr}...")
        try:
            results = sp.current_user_top_tracks(limit=50, time_range=tr)
            for track in results.get('items', []):
                if track and not track.get('is_local') and track.get('id'):
                    unique_tracks[track['id']] = track
        except Exception as e:
            print(f"Error fetching {tr}: {e}")

    selected_items = list(unique_tracks.values())
    print(f"\nFound {len(selected_items)} UNIQUE favorite tracks on your profile (after removing duplicates).\n")

    docs_to_insert = []
    metadatas_to_insert = []
    ids_to_insert = []

    print("Starting analysis and querying Last.fm...\n")

    for i, track in enumerate(selected_items):
        raw_title = track.get('name', 'Unknown title')
        artists = track.get('artists', [])
        if not artists: continue
        
        artist_name = artists[0].get('name', 'Unknown artist')
        track_id = track.get('id')
        
        album = track.get('album', {})
        year = album.get('release_date', '')[:4] if album.get('release_date') else 'None'
        
        sig = f"{artist_name.lower().strip()} - {clean_title(raw_title)}"
        print(f"[{i+1}/{len(selected_items)}] {artist_name} - {raw_title}")
        
        if sig in existing_signatures:
            print("   -> Skipping (Track already exists in the database!)")
            continue
            
        tags = get_lastfm_tags(artist_name, clean_title(raw_title))
        time.sleep(0.2) 
        
        valid_tags = [t for t in tags if t not in banned_tags and len(t.split()) <= 3][:10]
        
        if not valid_tags:
            print("   -> Skipping (no valuable tags found)")
            continue

        tags_string = ", ".join(valid_tags)
        
        document_text = f"Artist: {artist_name}. Release year: {year}. Genres and mood: {tags_string}."
        
        docs_to_insert.append(document_text)
        metadatas_to_insert.append({"artist": artist_name, "title": raw_title, "spotify_id": track_id})
        ids_to_insert.append(track_id)
        
        existing_signatures.add(sig) 

    if docs_to_insert:
        print(f"\nStarting to save {len(docs_to_insert)} of your favorite tracks to ChromaDB...")
        collection.upsert(
            documents=docs_to_insert,
            metadatas=metadatas_to_insert,
            ids=ids_to_insert
        )
        print(f"\nSuccess! Your music taste has been loaded into the AI engine!")
    else:
        print("\nNo new data added. It looks like all your top tracks were already in the database!")