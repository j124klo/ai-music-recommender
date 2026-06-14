import os
from dotenv import load_dotenv
import spotipy
from spotipy.oauth2 import SpotifyOAuth

# 1. Załadowanie kluczy z pliku .env
load_dotenv()

# 2. Definiujemy "scope" - czyli o jakie uprawnienia prosimy użytkownika.
# 'user-top-read' pozwala na legalne pobranie listy najczęściej słuchanych piosenek.
scope = "user-top-read"

print("Inicjalizacja połączenia ze Spotify...")

# Spotipy automatycznie pobierze SPOTIPY_CLIENT_ID, SECRET i REDIRECT_URI z pliku .env
try:
    sp = spotipy.Spotify(auth_manager=SpotifyOAuth(scope=scope))

    print("\n[INFO] Jeśli uruchamiasz to po raz pierwszy, otworzy się okno przeglądarki.")
    print("[INFO] Zaloguj się i zaakceptuj uprawnienia dla aplikacji.\n")

    # 3. Pobranie TOP 10 utworów użytkownika (średni dystans czasowy ~6 miesięcy)
    top_tracks = sp.current_user_top_tracks(limit=10, time_range='medium_term')

    print("--- SUKCES! TWOJE PRAWDZIWE TOP 10 UTWORÓW ---")
    for i, track in enumerate(top_tracks['items']):
        artist = track['artists'][0]['name']
        name = track['name']
        popularity = track['popularity']
        print(f"{i+1}. {artist} - {name} (Popularność: {popularity}/100)")
    print("---------------------------------------------")

except Exception as e:
    print(f"\n[BŁĄD] Coś poszło nie tak podczas autoryzacji.")
    print(f"Treść błędu: {e}")
    print("\nUpewnij się, że:")
    print("1. Adres e-mail konta, na które się logujesz, jest dodany w zakładce 'Users and Access'.")
    print("2. W pliku .env masz poprawny SPOTIPY_REDIRECT_URI='http://127.0.0.1:8000/callback'")