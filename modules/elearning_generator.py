import os
import json
import logging
from typing import Dict, Any, List, Optional
from datetime import datetime
from pathlib import Path

# Import the component modules
from modules.document_processor import DocumentProcessor
from modules.vector_store_manager import VectorStoreManager
from modules.llm_manager import LLMManager
from modules.template_manager import TemplateManager
from modules.dialog_manager import DialogManager

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class ELearningCourseGenerator:
    """
    Main class that integrates all components of the e-learning course generator.
    """

    def __init__(self, config_path: str = "./config.json"):
        """
        Initializes the ELearningCourseGenerator.

        Args:
            config_path: Path to the configuration file
        """
        # Load the configuration
        self.config = self.load_config(config_path)

        # Create required directories
        self.create_directories()

        # Initialize the components
        self.document_processor = DocumentProcessor(
            documents_dir=self.config["documents_dir"],
            chunk_size=self.config["chunk_size"],
            chunk_overlap=self.config["chunk_overlap"]
        )

        self.vector_store_manager = VectorStoreManager(
            persist_directory=self.config["vectorstore_dir"]
        )

        self.llm_manager = LLMManager(
            model_name=self.config["model_name"]
        )

        self.template_manager = TemplateManager(
            template_path=self.config.get("template_path")
        )

        self.dialog_manager = None

        # Statistics for evaluation
        self.generated_scripts_count = 0

    def load_config(self, config_path: str) -> Dict[str, Any]:
        """
        Loads the configuration from a JSON file.

        Args:
            config_path: Path to the configuration file

        Returns:
            Configuration as a dictionary
        """
        default_config = {
            "documents_dir": "./data/documents",
            "vectorstore_dir": "./data/vectorstore",
            "output_dir": "./data/output",
            "model_name": "llama3:8b",
            "chunk_size": 1000,
            "chunk_overlap": 200
        }

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # Add missing default values
            for key, value in default_config.items():
                if key not in config:
                    config[key] = value

            return config
        except Exception as e:
            logger.warning(f"Error loading configuration: {e}. Using default configuration.")
            return default_config

    def create_directories(self) -> None:
        """Creates the required directories if they don't exist."""
        directories = [
            self.config["documents_dir"],
            self.config["vectorstore_dir"],
            self.config["output_dir"]
        ]

        for directory in directories:
            os.makedirs(directory, exist_ok=True)

    def setup(self) -> None:
        """
        Sets up the generator by loading documents and creating the vector database.
        """
        # Try to load an existing vector database
        database_loaded = self.vector_store_manager.load_vectorstore()

        if not database_loaded:
            # If no database exists, create a new one
            documents = self.document_processor.load_documents()
            processed_docs = self.document_processor.process_documents(documents)
            self.vector_store_manager.create_vectorstore(processed_docs)

        # Initialize the dialog manager
        self.dialog_manager = DialogManager(
            template_manager=self.template_manager,
            llm_manager=self.llm_manager,
            vector_store_manager=self.vector_store_manager
        )

    def start_conversation(self) -> str:
        """
        Starts the conversation with the user.

        Returns:
            First question for the user
        """
        if self.dialog_manager is None:
            self.setup()

        return self.dialog_manager.get_next_question()

    def process_user_input(self, user_input: str) -> str:
        """
        Processes the user's input and returns the next question.

        Args:
            user_input: User's input

        Returns:
            Next question or message
        """
        if self.dialog_manager is None:
            self.setup()

        response = self.dialog_manager.process_user_response(user_input)

        # Check if a script was generated
        if "Hier ist der entworfene E-Learning-Kurs" in response:
            self.generated_scripts_count += 1
            logger.info(f"Script {self.generated_scripts_count} generated!")

        return response

    def save_generated_script(self, filename: str = None, format: str = "txt") -> str:
        """
        Saves the generated course and returns the path.

        Args:
            filename: Name of the output file (optional)
            format: Format of the output ("txt", "json", or "html")

        Returns:
            Path to the saved file
        """
        if self.dialog_manager is None:
            raise ValueError("Dialog manager has not been initialized")

        if filename is None:
            # Generate a filename based on the context
            organization = self.dialog_manager.conversation_state["context_info"].get(
                "Für welche Art von Organisation erstellen wir den E-Learning-Kurs (z.B. Krankenhaus, Bank, Behörde)?", "")
            audience = self.dialog_manager.conversation_state["context_info"].get(
                "Welche Mitarbeitergruppen sollen geschult werden?", "")

            sanitized_organization = ''.join(c for c in organization if c.isalnum() or c.isspace()).strip().replace(' ', '_')
            sanitized_audience = ''.join(c for c in audience if c.isalnum() or c.isspace()).strip().replace(' ', '_')

            timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
            filename = f"elearning_{sanitized_organization}_{sanitized_audience}_{timestamp}.{format}"

        output_path = os.path.join(self.config["output_dir"], filename)
        self.dialog_manager.save_script(output_path, format)

        return output_path

    def reset_conversation(self) -> None:
        """
        Resets the conversation to create a new course.
        """
        if self.dialog_manager is not None:
            # Create a new dialog manager with the same components
            self.dialog_manager = DialogManager(
                template_manager=self.template_manager,
                llm_manager=self.llm_manager,
                vector_store_manager=self.vector_store_manager
            )

    def reindex_documents(self):
        """
        Deletes the existing vector database and creates a new one with all current documents.
        """
        logger.info("Starting document reindexing...")

        # Reload all documents
        documents = self.document_processor.load_documents()
        processed_docs = self.document_processor.process_documents(documents)

        # Delete the old vector database if it exists
        if os.path.exists(self.config["vectorstore_dir"]):
            import shutil
            try:
                shutil.rmtree(self.config["vectorstore_dir"])
            except PermissionError:
                logger.warning("Permission error when trying to delete vectorstore directory. Trying alternative approach.")
                # Try to delete files individually
                for root, dirs, files in os.walk(self.config["vectorstore_dir"]):
                    for file in files:
                        try:
                            os.remove(os.path.join(root, file))
                        except Exception as e:
                            logger.error(f"Could not remove file {file}: {e}")
        
        # Make sure the directory exists with proper permissions
        os.makedirs(self.config["vectorstore_dir"], exist_ok=True)
        
        # Try to ensure we have write permissions (works on Unix-like systems)
        try:
            os.chmod(self.config["vectorstore_dir"], 0o777)  # Full permissions for everyone
        except Exception as e:
            logger.warning(f"Could not set permissions on vectorstore directory: {e}")
        
        # Create new vector database
        self.vector_store_manager.create_vectorstore(processed_docs)
        logger.info(f"Reindexing completed. {len(processed_docs)} documents indexed.")

        return len(processed_docs)