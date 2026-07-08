import os
import chromadb
import numpy as np
import matplotlib.pyplot as plt
from sklearn.cluster import KMeans
from sklearn.decomposition import PCA
from chromadb.utils import embedding_functions

print("Connecting to ChromaDB vector database...")

# Safe absolute path (same as main.py)
db_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "music_db")

ef = embedding_functions.SentenceTransformerEmbeddingFunction(model_name="paraphrase-multilingual-MiniLM-L12-v2")
client = chromadb.PersistentClient(path=db_path)
collection = client.get_collection(name="spotify_tracks", embedding_function=ef)

# Fetch tracks from database (for analytical purposes)
data = collection.get(include=["embeddings", "metadatas"])
embeddings = np.array(data["embeddings"])

if len(embeddings) < 10:
    print("Not enough tracks in the database to generate a plot!")
    exit()

print(f"Fetched {len(embeddings)} vectors. Starting PCA and K-Means mathematical calculations...")

# 1. PCA (Dimensionality reduction)
# The model outputs 384D vectors. We flatten them to 2D for the plot.
pca = PCA(n_components=2)
embeddings_2d = pca.fit_transform(embeddings)

# 2. K-Means (New AI - Splitting taste into 3 intelligent clusters)
kmeans = KMeans(n_clusters=3, random_state=42, n_init="auto")
labels = kmeans.fit_predict(embeddings)
centers_2d = pca.transform(kmeans.cluster_centers_)

# 3. Simple average (Old AI - center of everything)
mean_all = np.mean(embeddings, axis=0)
mean_2d = pca.transform([mean_all])

print("Generating plot...")
plt.figure(figsize=(12, 8))

# Draw songs
scatter = plt.scatter(embeddings_2d[:, 0], embeddings_2d[:, 1], c=labels, cmap='viridis', alpha=0.5, s=20, label="Tracks in database (split by genres)")

# New AI (3 clusters)
plt.scatter(centers_2d[:, 0], centers_2d[:, 1], c='red', s=250, marker='X', edgecolor='black', linewidth=2, label='New AI (K-Means cluster centers)')

# Old AI (1 averaged point)
plt.scatter(mean_2d[:, 0], mean_2d[:, 1], c='black', s=400, marker='*', edgecolor='white', linewidth=1.5, label='Old AI (Simple average)')

plt.title('AI Optimization Proof: K-Means vs Simple Vector Average', fontsize=16)
plt.xlabel('Principal component (PCA 1)', fontsize=12)
plt.ylabel('Second component (PCA 2)', fontsize=12)
plt.legend(fontsize=12)
plt.grid(True, linestyle='--', alpha=0.5)

# Save file
plt.savefig('dowod_kmeans.png', dpi=300, bbox_inches='tight')
print("Success! Plot saved as 'dowod_kmeans.png' in your main folder.")
plt.show()