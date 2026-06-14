import chromadb

print("1. Łączenie z bazą danych...")
# PersistentClient sprawia, że baza zapisze się na stałe na dysku w folderze "music_db"
client = chromadb.PersistentClient(path="./music_db")

print("2. Tworzenie kolekcji (przestrzeni wektorowej)...")
# get_or_create zapobiega błędom - tworzy kolekcję lub otwiera ją, jeśli już istnieje
collection = client.get_or_create_collection(name="spotify_tracks")

print("3. Dodawanie utworów i automatyczne wektoryzowanie tagów...")
# Tutaj symulujemy to, co w przyszłości połączymy z Last.fm i Spotify
collection.add(
    documents=[
        "rock, alternative, grunge, loud guitars, 90s",     # W przyszłości: tagi z Last.fm
        "pop, dance, electronic, upbeat, party", 
        "chill, lo-fi, study, calm piano, relaxing",
        "j-pop, anime, energetic, vocaloid, fast"
    ],
    metadatas=[
        {"artist": "Nirvana", "title": "Smells Like Teen Spirit"}, # W przyszłości: dane ze Spotify
        {"artist": "Lady Gaga", "title": "Poker Face"},
        {"artist": "Lofi Girl", "title": "Morning Coffee"},
        {"artist": "Eve", "title": "Nonsense Bungaku"}
    ],
    ids=["id_1", "id_2", "id_3", "id_4"]
)

print("   [Sukces] Dane zapisane na dysku!\n")

# --- TEST INTELIGENCJI BAZY ---
user_query = "potrzebuję czegoś dynamicznego do biegania, może być azjatyckie"

print(f"Zapytanie użytkownika: '{user_query}'")
print("Szukam najbliższego dopasowania w wektorach...")

results = collection.query(
    query_texts=[user_query],
    n_results=1 # Zwróć tylko 1 najlepszy wynik
)

best_artist = results['metadatas'][0][0]['artist']
best_title = results['metadatas'][0][0]['title']

print("\n========================================")
print(f"REKOMENDACJA AI: {best_artist} - {best_title}")
print("========================================")