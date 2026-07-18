import chromadb
from chromadb.config import Settings
import uuid
from utils.logger import NovaLogger

logger = NovaLogger()

class PersistentMemory:
    def __init__(self, collection_name="nova_memory"):
        self.client = chromadb.PersistentClient(path="./chroma_db", settings=Settings(anonymized_telemetry=False))
        self.collection = self.client.get_or_create_collection(name=collection_name)

    def add_memory(self, content, metadata=None):
        if not content.strip(): return
        self.collection.add(documents=[content], metadatas=[metadata or {}], ids=[str(uuid.uuid4())])

    def retrieve_relevant(self, query, n_results=5):
        results = self.collection.query(query_texts=[query], n_results=n_results)
        return results.get("documents", [[]])[0]