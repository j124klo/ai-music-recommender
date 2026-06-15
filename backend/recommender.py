import chromadb

# --- KONFIGURACJA BAZY ---
print("Uruchamianie silnika AI...")
client = chromadb.PersistentClient(path="./music_db")
collection = client.get_collection(name="spotify_tracks")

print("Gotowe!\n")
print("========================================")
print("       TWÓJ OSOBISTY DJ AI (Test)       ")
print("========================================")

# --- NIESKOŃCZONA PĘTLA WYSZUKIWANIA ---
while True:
    print("\nOpisz swoimi słowami, na co masz ochotę.")
    print("(Wpisz 'exit' aby zakończyć)")
    
    user_query = input("Twój nastrój/gatunek: ")
    
    if user_query.lower() == 'exit':
        break
        
    print("\nSzukam odpowiednich utworów w bazie...\n")
    
    # AI szuka 5 najbardziej pasujących piosenek do Twojego opisu
    results = collection.query(
        query_texts=[user_query],
        n_results=5 
    )
    
    # Wyświetlanie wyników
    print("--- NAJLEPSZE DOPASOWANIA ---")
    for i in range(len(results['ids'][0])):
        artist = results['metadatas'][0][i]['artist']
        title = results['metadatas'][0][i]['title']
        distance = results['distances'][0][i] # Dystans wektorowy (im mniejszy, tym lepszy)
        
        # Opcjonalnie: Tłumaczymy matematyczny dystans na procentowe dopasowanie (bardzo uproszczone)
        match_score = max(0, int((1.5 - distance) / 1.5 * 100))
        
        print(f"{i+1}. {artist} - {title} (Dopasowanie: ~{match_score}%)")