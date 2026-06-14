import os
import requests
from dotenv import load_dotenv

# 1. Załadowanie kluczy z pliku .env
load_dotenv()
API_KEY = os.getenv("LASTFM_API_KEY")

if not API_KEY:
    print("[BŁĄD] Brak LASTFM_API_KEY w pliku .env!")
    exit()

# 2. Parametry zapytania (szukamy tagów dla utworu "Blinding Lights" - The Weeknd)
artist_name = "The Weeknd"
track_name = "Blinding Lights"

# URL do API Last.fm
url = "http://ws.audioscrobbler.com/2.0/"

# Parametry wymagane przez dokumentację Last.fm
params = {
    "method": "track.getTopTags",
    "artist": artist_name,
    "track": track_name,
    "api_key": API_KEY,
    "format": "json" # chcemy wynik w formacie JSON, łatwym do przetworzenia w Pythonie
}

print(f"Pobieranie tagów z Last.fm dla: {artist_name} - {track_name}...")

# 3. Wykonanie zapytania HTTP GET
response = requests.get(url, params=params)

if response.status_code == 200:
    data = response.json()
    
    # Wyciągamy listę tagów z odpowiedzi
    try:
        tags = data["toptags"]["tag"]
        
        print("\n--- SUKCES! TOP 10 TAGÓW Z LAST.FM ---")
        # Wyświetlamy 10 najpopularniejszych tagów (często określają gatunek lub vibe)
        for i, tag in enumerate(tags[:10]):
            name = tag["name"]
            count = tag["count"] # waga tagu (jak wielu użytkowników go dodało)
            print(f"{i+1}. {name} (waga: {count})")
        print("---------------------------------------")
        
    except KeyError:
        print("[BŁĄD] Nie znaleziono tagów dla tego utworu lub utwór nie istnieje w bazie Last.fm.")
else:
    print(f"[BŁĄD HTTP] Kod odpowiedzi: {response.status_code}")