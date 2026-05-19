# backend/db/chroma.py
import chromadb
from chromadb.utils import embedding_functions
from typing import List, Optional

# Initialize ChromaDB — runs locally, zero cost, no API needed
# Data is persisted in the ./chroma_data folder
client = chromadb.PersistentClient(path="./chroma_data")
print("✅ ChromaDB client initialized")

# Use default embedding function (sentence transformers, runs locally)
# In Week 2 we'll upgrade to Nomic Embed API for better quality
embedding_fn = embedding_functions.DefaultEmbeddingFunction()

# Collections — like tables but for vectors
# Each collection stores embeddings for a different domain
incidents_collection = client.get_or_create_collection(
    name="incidents",
    embedding_function=embedding_fn,
    metadata={"description": "Past incident reports for Scout RAG"}
)

pr_collection = client.get_or_create_collection(
    name="pr_history", 
    embedding_function=embedding_fn,
    metadata={"description": "Historical PR diffs for risk pattern matching"}
)

slack_collection = client.get_or_create_collection(
    name="slack_decisions",
    embedding_function=embedding_fn,
    metadata={"description": "Past Slack decisions for Weaver"}
)

print(f"✅ ChromaDB collections ready: incidents({incidents_collection.count()}), "
      f"pr_history({pr_collection.count()}), slack_decisions({slack_collection.count()})")


def add_incident(incident_id: str, title: str, description: str, 
                  affected_service: str, files_involved: list):
    """
    Adds a past incident to ChromaDB.
    Scout uses this to find similar incidents when scoring PR risk.
    
    The text is embedded (converted to a vector) automatically.
    ChromaDB stores both the vector and the original metadata.
    """
    document = f"""
    Incident: {title}
    Service: {affected_service}
    Description: {description}
    Files involved: {', '.join(files_involved)}
    """
    
    incidents_collection.add(
        documents=[document],
        metadatas=[{
            "incident_id": incident_id,
            "title": title,
            "affected_service": affected_service,
            "files_involved": str(files_involved)
        }],
        ids=[incident_id]
    )
    print(f"[ChromaDB] ✅ Added incident: {title}")


def search_similar_incidents(pr_files: list, pr_title: str, n_results: int = 3) -> list:
    """
    Finds past incidents similar to the current PR.
    This is the core of Scout's RAG — semantic search over incident history.
    
    How it works:
    1. We build a query string from the PR's files and title
    2. ChromaDB embeds that query into a vector
    3. It finds the most similar incident vectors (cosine similarity)
    4. Returns the top N matches with their metadata
    """
    query = f"PR touching files: {', '.join(pr_files)}. Title: {pr_title}"
    
    if incidents_collection.count() == 0:
        return []
    
    results = incidents_collection.query(
        query_texts=[query],
        n_results=min(n_results, incidents_collection.count())
    )
    
    similar = []
    if results and results["documents"]:
        for i, doc in enumerate(results["documents"][0]):
            similar.append({
                "document": doc,
                "metadata": results["metadatas"][0][i],
                "distance": results["distances"][0][i]
            })
    
    return similar


def add_slack_decision(decision_id: str, content: str, author: str, channel: str, date: str):
    """Adds a Slack decision/discussion to ChromaDB for Weaver to search."""
    slack_collection.add(
        documents=[content],
        metadatas=[{
            "decision_id": decision_id,
            "author": author,
            "channel": channel,
            "date": date
        }],
        ids=[decision_id]
    )


def search_slack_decisions(query: str, n_results: int = 3) -> list:
    """Weaver uses this to find relevant past decisions."""
    if slack_collection.count() == 0:
        return []
    
    results = slack_collection.query(
        query_texts=[query],
        n_results=min(n_results, slack_collection.count())
    )
    
    similar = []
    if results and results["documents"]:
        for i, doc in enumerate(results["documents"][0]):
            similar.append({
                "document": doc,
                "metadata": results["metadatas"][0][i]
            })
    
    return similar