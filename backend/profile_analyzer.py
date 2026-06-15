import chromadb
import numpy as np

# Inicjalizacja bazy
client = chromadb.PersistentClient(path="./music_db")
collection = client.get_collection(name="spotify_tracks")

def recommend_based_on_history(track_ids_list):
    """
    Przyjmuje listę ID utworów ze Spotify (np. z ulubionej playlisty),
    oblicza ich średni wektor w ChromaDB i zwraca rekomendacje.
    """
    # 1. Pobieramy z bazy osadzenia (wektory) dla znanych nam ID piosenek
    # Zwróci tylko te, które fizycznie są w naszej bazie wektorowej
    data = collection.get(
        ids=track_ids_list,
        include=["embeddings", "metadatas"]
    )
    
    embeddings = data.get("embeddings")
    if not embeddings:
        print("Nie znaleziono podanych utworów w naszej bazie ChromaDB. Użyj najpierw loadera!")
        return
        
    print(f"Znaleziono {len(embeddings)} utworów pasujących do Twojego profilu w bazie.")
    
    # 2. Obliczamy ŚREDNI WEKTOR (To jest matematyczny reprezentant gustu!)
    # axis=0 oznacza, że wyciągamy średnią z każdej kolumny wymiaru wektora
    taste_vector = np.mean(embeddings, axis=0).tolist()
    
    # 3. Szukamy w bazie utworów znajdujących się najbliżej tego uśrednionego punktu
    print("Szukam podobnych utworów...\n")
    results = collection.query(
        query_embeddings=[taste_vector],
        n_results=10 # Pobieramy 10 propozycji
    )
    
    print("--- REKOMENDACJE NA BAZIE PLAYLISTY ---")
    for i in range(len(results['ids'][0])):
        rec_id = results['ids'][0][i]
        
        # Pomijamy utwory, które były danymi wejściowymi (żeby nie polecać tego, co już znasz)
        if rec_id in track_ids_list:
            continue
            
        artist = results['metadatas'][0][i]['artist']
        title = results['metadatas'][0][i]['title']
        distance = results['distances'][0][i]
        
        print(f"-> {artist} - {title} (Dystans wektorowy: {distance:.4f})")

# === TESTOWANIE ===
if __name__ == "__main__":
    # Symulacja: Pobrałeś te ID ze Spotify API jako "Top Tracks" lub utwory z playlisty
    # WAŻNE: Podmień na prawdziwe Spotify ID utworów, które wczytałeś loaderem do bazy!
    sample_favorite_tracks = [
        "11dFghVXANMlKmJXsNCbNl", # Przykładowe ID
        "6RQMD2n13M1RofBR4z2UGL"  # Przykładowe ID
    ]
    
    recommend_based_on_history(sample_favorite_tracks)