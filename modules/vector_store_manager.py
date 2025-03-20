import logging
import os
from typing import List, Dict, Any, Set
import torch
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_community.vectorstores import FAISS
import faiss

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class VectorStoreManager:
    """Manages the vector database for document retrieval."""

    def __init__(self, persist_directory: str = "./data/faiss_index"):
        """Initialize the VectorStoreManager."""
        self.persist_directory = persist_directory
        
        # Initialize the embedding model (same as before)
        self.embeddings = HuggingFaceEmbeddings(
            model_name="BAAI/bge-small-en-v1.5",
            model_kwargs={'device': 'cuda' if torch.cuda.is_available() else 'cpu'},
            encode_kwargs={'normalize_embeddings': True}
        )
        
        self.vectorstore = None

    def create_vectorstore(self, documents: List[Document]) -> None:
        try:
            # Create the FAISS index
            self.vectorstore = FAISS.from_documents(
                documents=documents,
                embedding=self.embeddings
            )
            
            # Save to disk
            self.vectorstore.save_local(self.persist_directory)
            
            logger.info(f"Vector database created and saved to {self.persist_directory}")
        except Exception as e:
            logger.error(f"Error creating vector database: {e}")
            raise

    def load_vectorstore(self) -> bool:
        """Load an existing vector database."""
        try:
            # Check if index files exist
            index_file = os.path.join(self.persist_directory, "index.faiss")
            docstore_file = os.path.join(self.persist_directory, "index.pkl")
            
            if os.path.exists(index_file) and os.path.exists(docstore_file):
                # Load the FAISS index
                self.vectorstore = FAISS.load_local(
                    folder_path=self.persist_directory,
                    embeddings=self.embeddings
                )
                logger.info("Existing FAISS vector database loaded")
                return True
            else:
                logger.warning(f"No existing FAISS index found at {self.persist_directory}")
                return False
        except Exception as e:
            logger.error(f"Error loading vector database: {e}")
            return False

    def get_retriever(self, search_type: str = "mmr", search_kwargs: Dict[str, Any] = None):
        """
        Get a retriever for the vector database.

        Args:
            search_type: Type of search (e.g., "mmr" for Maximum Marginal Relevance)
            search_kwargs: Additional search parameters

        Returns:
            Retriever object
        """
        if self.vectorstore is None:
            raise ValueError("Vector database has not been initialized")

        if search_kwargs is None:
            search_kwargs = {"k": 5}

        return self.vectorstore.as_retriever(
            search_type=search_type,
            search_kwargs=search_kwargs
        )

    def retrieve_documents(self, query: str, filter: Dict[str, Any] = None, k: int = 5) -> List[Document]:
        """
        Perform a search in the vector database.

        Args:
            query: Search query
            filter: Filter for the search
            k: Number of documents to return

        Returns:
            List of found Document objects
        """
        if self.vectorstore is None:
            raise ValueError("Vector database has not been initialized")

        results = self.vectorstore.similarity_search(
            query=query,
            filter=filter,
            k=k
        )

        return results

    def retrieve_with_multiple_queries(self, queries: List[str], filter: Dict[str, Any] = None, top_k: int = 3) -> List[Document]:
        """
        Perform multiple retrieval queries and aggregate the results.

        Args:
            queries: List of search queries
            filter: Filter for the search
            top_k: Number of documents to return per query

        Returns:
            List of aggregated Document objects
        """
        all_docs = []
        seen_ids = set()  # Prevent duplicates

        for query in queries:
            docs = self.retrieve_documents(query, filter, top_k)

            for doc in docs:
                # Skip if document already exists
                doc_id = f"{doc.metadata.get('source')}_{doc.metadata.get('chunk_id')}"
                if doc_id in seen_ids:
                    continue

                seen_ids.add(doc_id)
                all_docs.append(doc)

        # Limit the total number
        return all_docs[:top_k*2]