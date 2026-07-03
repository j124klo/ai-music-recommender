import os

# --- AI & BAZA DANYCH ---
MODEL_NAME = "./ai_muzyczne_v3"
DB_FOLDER_NAME = "music_db"
COLLECTION_NAME = "spotify_tracks"

# Automatyczne budowanie ścieżki do bazy (bezpieczne dla Windows/Mac/Linux)
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_PATH = os.path.join(BASE_DIR, DB_FOLDER_NAME)

# --- REKOMENDACJE (API DEFAULTS) ---
DEFAULT_PROFILE_RECS = 15
DEFAULT_PLAYLIST_RECS = 15
DEFAULT_MOOD_RECS = 15

# --- USTAWIENIA LOADERÓW (Pobieranie ze Spotify) ---
AUTO_DEEP_THRESHOLD = 34
FAST_FIRST_COUNT = 17
FAST_LAST_COUNT = 17
BATCH_SAVE_SIZE = 1000