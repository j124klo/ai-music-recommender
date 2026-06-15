import os
import time
import re
import requests
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth
import chromadb

# =====================================================================
#                          KONFIGURACJA MODUŁOWA
# =====================================================================
load_dotenv()
LASTFM_API_KEY = os.getenv("LASTFM_API_KEY")

# Progi operacyjne (Możesz je swobodnie zmieniać w zależności od potrzeb)
AUTO_DEEP_THRESHOLD = 34  # Do tylu utworów zawsze idzie tryb dogłębny
FAST_FIRST_COUNT = 17     # Ile utworów z początku w trybie szybkim
FAST_LAST_COUNT = 17      # Ile utworów z końca w trybie szybkim

# Initializacja klientów API
sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope="user-top-read playlist-read-private playlist-read-collaborative"))
client = chromadb.PersistentClient(path="./music_db")
collection = client.get_or_create_collection(name="spotify_tracks")

# =====================================================================
#                          FUNKCJE POMOCNICZE
# =====================================================================

def load_banned_tags(filepath="banned_tags.txt"):
    """Wczytuje listę zakazanych tagów z pliku zewnętrznego."""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            return [line.strip().lower() for line in f if line.strip()]
    except FileNotFoundError:
        print(f"UWAGA: Nie znaleziono pliku {filepath}. Czarna lista jest pusta.")
        return []

def clean_title(title):
    """Usuwa radiowe śmieci z tytułów utworów."""
    title = title.split(" - ")[0]
    title = re.sub(r'\(.*?\)', '', title)
    title = re.sub(r'\[.*?\]', '', title)
    return title.strip()

def get_lastfm_tags(artist, track):
    """Pobiera tagi z Last.fm stosując kaskadę ratunkową."""
    base_url = "http://ws.audioscrobbler.com/2.0/"
    
    # Próba 1: Tagi konkretnego utworu
    params = {"method": "track.getTopTags", "artist": artist, "track": track, "api_key": LASTFM_API_KEY, "format": "json"}
    try:
        resp = requests.get(base_url, params=params).json()
        tags = [t['name'].lower() for t in resp.get('toptags', {}).get('tag', [])]
        if tags: return tags
    except: pass
    
    # Próba 2: Tagi ogólne artysty
    params = {"method": "artist.getTopTags", "artist": artist, "api_key": LASTFM_API_KEY, "format": "json"}
    try:
        resp = requests.get(base_url, params=params).json()
        tags = [t['name'].lower() for t in resp.get('toptags', {}).get('tag', [])]
        return tags
    except: pass
    
    return []

def fetch_all_tracks(playlist_id):
    """Pobiera absolutnie wszystkie utwory z playlisty, obsługując paginację Spotify."""
    all_items = []
    # Pobieramy pierwszą paczkę (max 100 sztuk)
    results = sp.playlist_items(playlist_id, limit=100)
    all_items.extend(results.get('items', []))
    
    # Pętla paginacji - dopóki istnieje link do następnej strony, pobieraj dalej
    while results.get('next'):
        results = sp.next(results)
        all_items.extend(results.get('items', []))
        
    return all_items

# =====================================================================
#                          GŁÓWNY PROCES LOADERA
# =====================================================================
if __name__ == "__main__":
    print("========================================")
    print("       SPOTIFY TO CHROMA LOADER         ")
    print("========================================\n")

    banned_tags = load_banned_tags()

    playlist_url = input("Wklej link do playlisty Spotify: ")
    playlist_id = playlist_url.split("/")[-1].split("?")[0]

    print("\nPobieranie pełnej zawartości playlisty ze Spotify...")
    raw_playlist_items = fetch_all_tracks(playlist_id)
    total_tracks = len(raw_playlist_items)

    if total_tracks == 0:
        print("Błąd: Playlista jest pusta lub niewidoczna dla API.")
        exit()

    # --- LOGIKA WYBORU TRYBU (MODUŁOWA) ---
    selected_items = []
    
    if total_tracks <= AUTO_DEEP_THRESHOLD:
        print(f"-> Playlista ma {total_tracks} utworów (Rozmiar <= {AUTO_DEEP_THRESHOLD}).")
        print("-> Automatyczne uruchomienie trybu dogłębnego (Analiza całości).")
        selected_items = raw_playlist_items
    else:
        print(f"-> Playlista ma aż {total_tracks} utworów.")
        choice = input(f"Czy chcesz użyć trybu szybkiego (pierwsze {FAST_FIRST_COUNT} i ostatnie {FAST_LAST_COUNT} utworów)? [y/n]: ")
        
        if choice.lower() == 'y':
            print("\nUruchamiam tryb SZYBKI (Próbkowanie krańców playlisty)...")
            # Wycinamy początek i koniec
            first_part = raw_playlist_items[:FAST_FIRST_COUNT]
            last_part = raw_playlist_items[-FAST_LAST_COUNT:]
            selected_items = first_part + last_part
        else:
            print("\nUruchamiam tryb DOGŁĘBNY (To może chwilę potrwać)...")
            selected_items = raw_playlist_items

    # --- ANALIZA I ZAPIS DO CHROMA ---
    docs_to_insert = []
    metadatas_to_insert = []
    ids_to_insert = []

    print(f"\nRozpoczynam analizę {len(selected_items)} wybranych utworów...\n")

    for i, list_item in enumerate(selected_items):
        track = list_item.get('track') or list_item.get('item')
        if not track or not isinstance(track, dict): continue
            
        raw_title = track.get('name', 'Nieznany tytuł')
        clean_name = clean_title(raw_title)
        artists = track.get('artists', [])
        if not artists: continue
        
        artist_name = artists[0].get('name', 'Nieznany artysta')
        track_id = track.get('id')
        if not track_id: continue
        
        print(f"[{i+1}/{len(selected_items)}] {artist_name} - {clean_name}")
        
        tags = get_lastfm_tags(artist_name, clean_name)
        time.sleep(0.2) # Ochrona przed banem 503
        
        # Filtrowanie tagów na bazie długości oraz czarnej listy
        valid_tags = []
        for t in tags:
            if t not in banned_tags and len(t.split()) <= 3:
                valid_tags.append(t)
                
        valid_tags = valid_tags[:4] # bierzemy tylko 4 najpopularniejsze słowa
        
        if not valid_tags:
            print("   -> Pomijam (brak wartościowych tagów)")
            continue

        tags_string = ", ".join(valid_tags)
        
        docs_to_insert.append(tags_string)
        metadatas_to_insert.append({"artist": artist_name, "title": raw_title, "spotify_id": track_id})
        ids_to_insert.append(track_id)

    print(f"\nSukces! Przeanalizowano i przygotowano {len(docs_to_insert)} utworów.")
    print("Zapisywanie bazy na dysku...")

    if docs_to_insert:
        collection.upsert(
            documents=docs_to_insert,
            metadatas=metadatas_to_insert,
            ids=ids_to_insert
        )
        print("Baza wektorowa została pomyślnie zaktualizowana!")
    else:
        print("Nie znaleziono odpowiednich danych do zapisu.")