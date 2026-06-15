import chromadb

client = chromadb.PersistentClient(path="./music_db")
collection = client.get_collection(name="spotify_tracks")

print("--- INSPEKTOR BAZY WEKTOROWEJ ---")
print(f"Całkowita liczba utworów w bazie: {collection.count()}\n")

while True:
    artist_query = input("Podaj nazwę artysty do sprawdzenia (lub 'exit'): ")
    if artist_query.lower() == 'exit':
        break
        
    # Szukamy w metadanych (ignoruje wielkość liter tylko jeśli podamy dokładną nazwę)
    results = collection.get(
        where={"artist": artist_query}
    )
    
    if results['ids']:
        print(f"\nZnaleziono utwory wykonawcy: {artist_query} ({len(results['ids'])} szt.)")
        for i in range(len(results['ids'])):
            title = results['metadatas'][i]['title']
            tags = results['documents'][i]
            print(f"- {title}")
            print(f"  Tagi: [{tags}]")
    else:
        print(f"\nBrak artysty '{artist_query}' w bazie (pamiętaj o wielkich/małych literach!).")
    print("-" * 40)