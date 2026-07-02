import os
import chromadb
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from chromadb.utils import embedding_functions

print("Łączenie z bazą wektorową ChromaDB...")

# Ustawienie bezpiecznej ścieżki absolutnej do bazy (tak jak w main.py)
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music_db")

ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="paraphrase-multilingual-MiniLM-L12-v2")
client = chromadb.PersistentClient(path=db_path)
collection = client.get_collection(name="spotify_tracks", embedding_function=ef)

# Pobieramy utwory z bazy (do celów analitycznych)
data = collection.get(include=["embeddings", "metadatas"])
embeddings = np.array(data["embeddings"])

if len(embeddings) < 10:
    print("Za mało utworów w bazie, aby wygenerować wykres!")
    exit()

print(f"Pobrano {len(embeddings)} wektorów. Rozpoczynam obliczenia matematyczne PCA i K-Means...")

# 1. PCA (Redukcja wymiarów)
# Model wypluwa wektory 384D. My spłaszczamy je do 2D na wykres.
pca = PCA(n_components=2)
embeddings_2d = pca.fit_transform(embeddings)

# 2. K-Means (Nowe AI - Dzielenie gustu na 3 inteligentne klastry)
kmeans = KMeans(n_clusters=3, random_state=42, n_init="auto")
labels = kmeans.fit_predict(embeddings)
centers_2d = pca.transform(kmeans.cluster_centers_)

# 3. Zwykła średnia (Stare AI - środek wszystkiego)
mean_all = np.mean(embeddings, axis=0)
mean_2d = pca.transform([mean_all])

print("Generowanie wykresu...")
plt.figure(figsize=(12, 8))

# Rysujemy piosenki
scatter = plt.scatter(embeddings_2d[:, 0], embeddings_2d[:, 1], c=labels, cmap='viridis', alpha=0.5, s=20, label="Utwory w bazie (podzielone na gatunki)")

# Nowe AI (3 klastry)
plt.scatter(centers_2d[:, 0], centers_2d[:, 1], c='red', s=250, marker='X', edgecolor='black', linewidth=2, label='Nowe AI (Środki klastrów K-Means)')

# Stare AI (1 uśredniony punkt)
plt.scatter(mean_2d[:, 0], mean_2d[:, 1], c='black', s=400, marker='*', edgecolor='white', linewidth=1.5, label='Stare AI (Zwykła średnia)')

plt.title('Dowód optymalizacji AI: K-Means vs Zwykła Średnia Wektorowa', fontsize=16)
plt.xlabel('Główna oś zmienności (PCA 1)', fontsize=12)
plt.ylabel('Druga oś zmienności (PCA 2)', fontsize=12)
plt.legend(fontsize=12)
plt.grid(True, linestyle='--', alpha=0.5)

# Zapisanie pliku
plt.savefig('dowod_kmeans.png', dpi=300, bbox_inches='tight')
print("Sukces! Zapisano wykres jako 'dowod_kmeans.png' w Twoim głównym folderze.")
plt.show()