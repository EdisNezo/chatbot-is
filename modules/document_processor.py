import logging
from pathlib import Path
from typing import List, Optional
from langchain.docstore.document import Document
from langchain.text_splitter import RecursiveCharacterTextSplitter

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class DocumentProcessor:
    """
    Responsible for loading, processing, and indexing documents
    for the RAG-based e-learning generator for information security.
    """

    def __init__(self, documents_dir: str, chunk_size: int = 1000, chunk_overlap: int = 200):
        """
        Initialize the DocumentProcessor.

        Args:
            documents_dir: Directory where documents to be indexed are stored
            chunk_size: Size of text chunks for indexing
            chunk_overlap: Overlap between text chunks
        """
        self.documents_dir = Path(documents_dir)
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.text_splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=["\n\n", "\n", ". ", " ", ""]
        )

    def load_documents(self) -> List[Document]:
        """
        Load all documents from the specified directory.

        Returns:
            List of Document objects
        """
        documents = []

        # Ensure directory exists
        if not self.documents_dir.exists():
            logger.warning(f"Document directory {self.documents_dir} does not exist.")
            return documents

        # Loop through all files in the directory
        file_count = 0
        for file_path in self.documents_dir.glob("**/*.*"):
            if file_path.is_file():
                try:
                    # Read file content
                    with open(file_path, "r", encoding="utf-8") as f:
                        content = f.read()

                    # Determine document type based on filename/path
                    doc_type = self._determine_document_type(file_path)

                    # Create Document object with metadata
                    doc = Document(
                        page_content=content,
                        metadata={
                            "source": str(file_path),
                            "file_name": file_path.name,
                            "doc_type": doc_type
                        }
                    )

                    documents.append(doc)
                    logger.info(f"Document loaded: {file_path}")
                    file_count += 1

                except Exception as e:
                    logger.error(f"Error loading {file_path}: {e}")

        logger.info(f"{file_count} documents successfully loaded")
        return documents

    def _determine_document_type(self, file_path: Path) -> str:
        """
        Determine the document type based on the file path or name.

        Args:
            file_path: Path to the file

        Returns:
            String with the document type
        """
        path_str = str(file_path).lower()

        if "template" in path_str:
            return "template"
        elif "policy" in path_str or "richtlinie" in path_str:
            return "policy"
        elif "compliance" in path_str or "vorschrift" in path_str:
            return "compliance"
        elif "best_practice" in path_str or "empfehlung" in path_str:
            return "best_practice"
        elif "beispiel" in path_str or "example" in path_str:
            return "example"
        elif "threat" in path_str or "bedrohung" in path_str or "risiko" in path_str:
            return "threat"
        elif "learning_theory" in path_str or "lerntheorie" in path_str:
            return "learning_theory"
        elif "security" in path_str or "sicherheit" in path_str:
            return "security_content"
        elif "industry" in path_str or "branche" in path_str:
            return "industry_specific"
        elif "process" in path_str or "prozess" in path_str:
            return "process"
        # New document types for the improved structure
        elif "awareness" in path_str:
            return "threat_awareness"
        elif "identification" in path_str:
            return "threat_identification"
        elif "assessment" in path_str or "impact" in path_str:
            return "threat_impact_assessment"
        elif "choice" in path_str or "tactic_choice" in path_str:
            return "tactic_choice"
        elif "justification" in path_str:
            return "tactic_justification"
        elif "mastery" in path_str:
            return "tactic_mastery"
        elif "follow" in path_str or "check" in path_str:
            return "tactic_check_follow_up"
        else:
            # Try to determine based on directory name
            parent_dir = file_path.parent.name.lower()
            for doc_type in ["policies", "compliance", "templates", "examples", "threats", "best_practices",
                           "security", "learning_theories", "industries", "processes"]:
                if parent_dir.startswith(doc_type) or doc_type in parent_dir:
                    return doc_type[:-1] if doc_type.endswith("s") else doc_type

            return "generic"

    def process_documents(self, documents: List[Document]) -> List[Document]:
        """
        Process documents for indexing: chunking and metadata enrichment.

        Args:
            documents: List of Document objects

        Returns:
            List of processed Document objects
        """
        processed_docs = []

        for doc in documents:
            # Split document into chunks
            chunks = self.text_splitter.split_documents([doc])

            # Add additional metadata if needed
            for i, chunk in enumerate(chunks):
                # Take over metadata from original document
                chunk.metadata = doc.metadata.copy()
                # Add chunk-specific metadata
                chunk.metadata["chunk_id"] = i
                chunk.metadata["chunk_total"] = len(chunks)

                # Extract section type if possible
                if doc.metadata["doc_type"] == "template":
                    section_type = self._extract_section_type(chunk.page_content)
                    if section_type:
                        chunk.metadata["section_type"] = section_type

                processed_docs.append(chunk)

        logger.info(f"Documents processed: {len(documents)} documents split into {len(processed_docs)} chunks")
        return processed_docs

    def _extract_section_type(self, content: str) -> Optional[str]:
        """
        Extract the section type from the content of a template chunk.

        Args:
            content: Text content of the chunk

        Returns:
            String with the section type or None if not found
        """
        # Improved heuristic for extraction based on the example script
        content_lower = content.lower()

        # Specific section types from the example script
        if any(term in content_lower for term in ["threat awareness", "bedrohungsbewusstsein"]):
            return "threat_awareness"
        elif any(term in content_lower for term in ["threat identification", "bedrohungserkennung"]):
            return "threat_identification"
        elif any(term in content_lower for term in ["threat impact assessment", "bedrohungsausmaß"]):
            return "threat_impact_assessment"
        elif any(term in content_lower for term in ["tactic choice", "taktische maßnahmenauswahl"]):
            return "tactic_choice"
        elif any(term in content_lower for term in ["tactic justification", "maßnahmenrechtfertigung"]):
            return "tactic_justification"
        elif any(term in content_lower for term in ["tactic mastery", "maßnahmenbeherrschung"]):
            return "tactic_mastery"
        elif any(term in content_lower for term in ["tactic check", "follow-up", "anschlusshandlungen"]):
            return "tactic_check_follow_up"

        # More general heuristic as fallback
        elif any(term in content_lower for term in ["lernziel", "learning objective", "ziel"]):
            return "learning_objectives"
        elif any(term in content_lower for term in ["inhalt", "content", "thema"]):
            return "content"
        elif any(term in content_lower for term in ["methode", "didaktik", "method", "format"]):
            return "methods"
        elif any(term in content_lower for term in ["prüfung", "assessment", "evaluation", "test", "quiz"]):
            return "assessment"
        elif any(term in content_lower for term in ["bedrohung", "threat", "risiko", "risk", "vulnerability"]):
            return "threats"
        elif any(term in content_lower for term in ["maßnahme", "control", "schutz", "protection"]):
            return "controls"
        elif any(term in content_lower for term in ["kontext", "context", "umgebung", "environment"]):
            return "context"
        elif any(term in content_lower for term in ["prozess", "process", "workflow", "ablauf"]):
            return "process"

        return None