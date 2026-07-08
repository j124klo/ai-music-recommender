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
#                          MODULAR CONFIGURATION
# =====================================================================
load_dotenv()
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")

sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope="user-top-read playlist-read-private playlist-read-collaborative"))

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
        print(f"WARNING: File {filepath} not found. The blacklist is empty.")
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
        tags = [t['name'].lower() for t in resp.get('toptags', {}).get('tag', [])]
        return tags
    except: pass
    
    return []

def fetch_all_tracks(playlist_id):
    all_items = []
    results = sp.playlist_items(playlist_id, limit=100)
    all_items.extend(results.get('items', []))
    while results.get('next'):
        results = sp.next(results)
        all_items.extend(results.get('items', []))
    return all_items

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
    except Exception as e:
        print(f"Database read error: {e}")
        return set()

# =====================================================================
#                          MAIN LOADER PROCESS
# =====================================================================
if __name__ == "__main__":
    print("========================================")
    print("       SPOTIFY TO CHROMA LOADER         ")
    print("========================================\n")

    banned_tags = load_banned_tags()
    
    existing_signatures = get_existing_signatures()
    print(f"The database currently contains {len(existing_signatures)} unique tracks.\n")

    playlist_url = input("Paste the Spotify playlist link: ")
    playlist_id = playlist_url.split("/")[-1].split("?")[0]

    print("\nFetching full playlist content from Spotify...")
    raw_playlist_items = fetch_all_tracks(playlist_id)
    total_tracks = len(raw_playlist_items)

    if total_tracks == 0:
        print("Error: The playlist is empty or not visible to the API.")
        exit()

    selected_items = []

    if total_tracks <= config.AUTO_DEEP_THRESHOLD:
        print(f"-> Automatic deep mode initiated.")
        selected_items = raw_playlist_items
    else:
        choice = input(f"Use fast mode ({config.FAST_FIRST_COUNT} from start and {config.FAST_LAST_COUNT} from end)? [y/n]: ")
        if choice.lower() == 'y':
            selected_items = raw_playlist_items[:config.FAST_FIRST_COUNT] + raw_playlist_items[-config.FAST_LAST_COUNT:]
        else:
            selected_items = raw_playlist_items

    docs_to_insert = []
    metadatas_to_insert = []
    ids_to_insert = []
    
    total_saved_new_tracks = 0

    print(f"\nStarting analysis of {len(selected_items)} selected tracks...\n")

    for i, list_item in enumerate(selected_items):
        track = list_item.get('track') or list_item.get('item')
        if not track or not isinstance(track, dict) or track.get('is_local'): continue
            
        raw_title = track.get('name', 'Unknown title')
        artists = track.get('artists', [])
        if not artists: continue
        
        artist_name = artists[0].get('name', 'Unknown artist')
        track_id = track.get('id')
        if not track_id: continue
        
        album = track.get('album', {})
        year = album.get('release_date', '')[:4] if album.get('release_date') else 'None'
        
        sig = f"{artist_name.lower().strip()} - {clean_title(raw_title)}"
        print(f"[{i+1}/{len(selected_items)}] {artist_name} - {raw_title}")
        
        if sig in existing_signatures:
            print("   -> Skipping (Track already exists in the database!)")
            continue
            
        tags = get_lastfm_tags(artist_name, clean_title(raw_title))
        time.sleep(0.2) 
        
        valid_tags = [t for t in tags if t not in banned_tags and len(t.split()) <= 4][:10]
        
        if not valid_tags:
            print("   -> Skipping (no valuable tags found)")
            continue

        tags_string = ", ".join(valid_tags)
        
        # English translation of the embedding document text format
        document_text = f"Artist: {artist_name}. Release year: {year}. Genres and mood: {tags_string}."
        
        docs_to_insert.append(document_text)
        metadatas_to_insert.append({"artist": artist_name, "title": raw_title, "spotify_id": track_id})
        ids_to_insert.append(track_id)
        
        existing_signatures.add(sig) 

        # --- CHECKPOINTING ---
        if len(docs_to_insert) >= config.BATCH_SAVE_SIZE:
            print(f"\n[AUTO-SAVE] Reached a batch of {config.BATCH_SAVE_SIZE} tracks. Saving to the vector database...")
            collection.upsert(
                documents=docs_to_insert,
                metadatas=metadatas_to_insert,
                ids=ids_to_insert
            )
            total_saved_new_tracks += len(docs_to_insert)
            print("[AUTO-SAVE] Successfully flushed data to disk. Resuming Last.fm queries...\n")
            
            docs_to_insert = []
            metadatas_to_insert = []
            ids_to_insert = []

    # --- FINAL SAVE ---
    if docs_to_insert:
        print(f"\nStarting final save of the last {len(docs_to_insert)} tracks to ChromaDB...")
        collection.upsert(
            documents=docs_to_insert,
            metadatas=metadatas_to_insert,
            ids=ids_to_insert
        )
        total_saved_new_tracks += len(docs_to_insert)

    if total_saved_new_tracks > 0:
        print(f"\nSuccess! Job finished. Successfully added a total of {total_saved_new_tracks} NEW tracks to the vector database!")
    else:
        print("\nNo new data added (all tracks were duplicates or lacked tags).")