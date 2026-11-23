from fileinput import filename

from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_chroma import Chroma

# embeddings = HuggingFaceEmbeddings(
#     model_name="sentence-transformers/all-MiniLM-L6-v2",
#     encode_kwargs={"normalize_embeddings": True},
# )
embeddings = HuggingFaceEmbeddings(
    model_name="sentence-transformers/all-MiniLM-L6-v2",
    model_kwargs={"device": "cpu"},
    encode_kwargs={"normalize_embeddings": True},
)
store = Chroma(
    collection_name="chunks",
    embedding_function=embeddings,
    persist_directory="./chroma_db",
    collection_metadata={"hnsw:space": "cosine"},
)


# store=Chroma(collection_name="chunks",embedding_function=embeddings,persist_directory="./chroma_db",collection_metadata={"hnsw:space": "cosine"})
def add_chunk(chunks, thread_id, file_name):
    doc = [
        Document(
            page_content=c["text"],
            metadata={"thread_id": thread_id, "filename": file_name, "page": c["page"]},
        )
        for c in chunks
    ]
    store.add_documents(doc)


def search(thread_id, query, k=4):
    # result = store.similarity_search(query, filter={"thread_id": thread_id}, k=k)
    result = store.similarity_search(query, k=k)

    return result
