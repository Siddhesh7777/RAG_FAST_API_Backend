import numpy as np
from sentence_transformers import SentenceTransformer

# Use the same model as your old project if you know it.
# Otherwise this small one is fine for learning.
model = SentenceTransformer("all-MiniLM-L6-v2")

sentences = [
    "You can get your money back within 30 days.",  # refund
    "Our refund policy allows returns for a month.",  # refund, different words
    "The server crashed because of a memory leak.",  # unrelated
]
query = "What is the money-back guarantee?"

vecs = model.encode(sentences)
q = model.encode(query)


def cosine(a, b):
    return np.dot(a, b) / (np.linalg.norm(a) * np.linalg.norm(b))


for s, v in zip(sentences, vecs):
    print(f"{cosine(q, v):.3f}  {s}")

print("Vector dimension:", len(q))
