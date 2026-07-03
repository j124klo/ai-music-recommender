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
#                          KONFIGURACJA MODUŁOWA
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
#                          FUNKCJE POMOCNICZE
# =====================================================================

def load_banned_tags(filepath="banned_tags.txt"):
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return [line.strip().lower() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"UWAGA: Nie znaleziono pliku {filepath}. Czarna lista jest pusta.")
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
        print(f"Błąd odczytu bazy: {e}")
        return set()

# =====================================================================
#                          GŁÓWNY PROCES LOADERA
# =====================================================================
if __name__ == "__main__":
    print("========================================")
    print("       SPOTIFY TO CHROMA LOADER         ")
    print("========================================\n")

    banned_tags = load_banned_tags()
    
    existing_signatures = get_existing_signatures()
    print(f"Baza zawiera obecnie {len(existing_signatures)} unikalnych utworów.\n")

    playlist_url = input("Wklej link do playlisty Spotify: ")
    playlist_id = playlist_url.split("/")[-1].split("?")[0]

    print("\nPobieranie pełnej zawartości playlisty ze Spotify...")
    raw_playlist_items = fetch_all_tracks(playlist_id)
    total_tracks = len(raw_playlist_items)

    if total_tracks == 0:
        print("Błąd: Playlista jest pusta lub niewidoczna dla API.")
        exit()

    selected_items = []

    if total_tracks <= config.AUTO_DEEP_THRESHOLD:
        print(f"-> Automatyczne uruchomienie trybu dogłębnego.")
        selected_items = raw_playlist_items
    else:
        choice = input(f"Czy użyć trybu szybkiego ({config.FAST_FIRST_COUNT} z początku i {config.FAST_LAST_COUNT} z końca)? [y/n]: ")
        if choice.lower() == 'y':
            selected_items = raw_playlist_items[:config.FAST_FIRST_COUNT] + raw_playlist_items[-config.FAST_LAST_COUNT:]
        else:
            selected_items = raw_playlist_items

    docs_to_insert = []
    metadatas_to_insert = []
    ids_to_insert = []
    
    total_saved_new_tracks = 0

    print(f"\nRozpoczynam analizę {len(selected_items)} wybranych utworów...\n")

    for i, list_item in enumerate(selected_items):
        track = list_item.get('track') or list_item.get('item')
        if not track or not isinstance(track, dict) or track.get('is_local'): continue
            
        raw_title = track.get('name', 'Nieznany tytuł')
        artists = track.get('artists', [])
        if not artists: continue
        
        artist_name = artists[0].get('name', 'Nieznany artysta')
        track_id = track.get('id')
        if not track_id: continue
        
        album = track.get('album', {})
        year = album.get('release_date', '')[:4] if album.get('release_date') else 'Brak'
        
        sig = f"{artist_name.lower().strip()} - {clean_title(raw_title)}"
        print(f"[{i+1}/{len(selected_items)}] {artist_name} - {raw_title}")
        
        if sig in existing_signatures:
            print("   -> Pomijam (Utwór już istnieje w bazie!)")
            continue
            
        tags = get_lastfm_tags(artist_name, clean_title(raw_title))
        time.sleep(0.2) 
        
        valid_tags = [t for t in tags if t not in banned_tags and len(t.split()) <= 4][:10]
        
        if not valid_tags:
            print("   -> Pomijam (brak wartościowych tagów)")
            continue

        tags_string = ", ".join(valid_tags)
        
        document_text = f"Wykonawca: {artist_name}. Rok wydania: {year}. Gatunki i klimat: {tags_string}."
        
        docs_to_insert.append(document_text)
        metadatas_to_insert.append({"artist": artist_name, "title": raw_title, "spotify_id": track_id})
        ids_to_insert.append(track_id)
        
        existing_signatures.add(sig) 

        # --- CHECKPOINTING ---
        if len(docs_to_insert) >= config.BATCH_SAVE_SIZE:
            print(f"\n[AUTO-ZAPIS] Osiągnięto paczkę {config.BATCH_SAVE_SIZE} utworów. Zapisuję do bazy wektorowej...")
            collection.upsert(
                documents=docs_to_insert,
                metadatas=metadatas_to_insert,
                ids=ids_to_insert
            )
            total_saved_new_tracks += len(docs_to_insert)
            print("[AUTO-ZAPIS] Pomyślnie zrzucono dane na dysk. Wznawiam odpytywanie Last.fm...\n")
            
            docs_to_insert = []
            metadatas_to_insert = []
            ids_to_insert = []

    # --- ZAPIS KOŃCOWY ---
    if docs_to_insert:
        print(f"\nRozpoczynam zapis końcowy ostatnich {len(docs_to_insert)} utworów do bazy ChromaDB...")
        collection.upsert(
            documents=docs_to_insert,
            metadatas=metadatas_to_insert,
            ids=ids_to_insert
        )
        total_saved_new_tracks += len(docs_to_insert)

    if total_saved_new_tracks > 0:
        print(f"\nSukces! Zakończono pracę. Pomyślnie dodano łącznie {total_saved_new_tracks} NOWYCH utworów do bazy wektorowej!")
    else:
        print("\nNie dodano nowych danych (wszystkie utwory były duplikatami lub brakło tagów).")