from ai.embeddings.embedding_generator import generate_embedding


complaint = "Water pipe near Block B is leaking."

embedding = generate_embedding(complaint)

print("Complaint:")
print(complaint)

print("\nEmbedding dimension:")
print(len(embedding))

print("\nFirst 10 values:")
print(embedding[:10])