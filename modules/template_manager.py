import json
import copy
import logging
from typing import Dict, Any, List, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TemplateManager:
    """
    Manages the template for the e-learning course.
    """

    def __init__(self, template_path: str = None):
        """
        Initializes the TemplateManager.

        Args:
            template_path: Path to the template file
        """
        self.template_path = template_path
        self.template = self.load_template()

    def load_template(self) -> Dict[str, Any]:
        """
        Loads the template from the specified file or creates a default template
        based on the example script.

        Returns:
            Template as a dictionary
        """
        # Use a template adapted to the example script
        default_template = {
            "title": "E-Learning-Kurs zur Informationssicherheit",
            "description": "Ein maßgeschneiderter Kurs zur Stärkung des Sicherheitsbewusstseins",
            "sections": [
                {
                    "id": "threat_awareness",
                    "title": "Threat Awareness",
                    "description": "Bedrohungsbewusstsein: Kontext und Ausgangssituationen, in denen Gefahren auftreten können",
                    "type": "threat_awareness"
                },
                {
                    "id": "threat_identification",
                    "title": "Threat Identification",
                    "description": "Bedrohungserkennung: Merkmale und Erkennungshinweise für potenzielle Gefahren",
                    "type": "threat_identification"
                },
                {
                    "id": "threat_impact_assessment",
                    "title": "Threat Impact Assessment",
                    "description": "Bedrohungsausmaß: Konsequenzen, die aus der Bedrohung entstehen können",
                    "type": "threat_impact_assessment"
                },
                {
                    "id": "tactic_choice",
                    "title": "Tactic Choice",
                    "description": "Taktische Maßnahmenauswahl: Handlungsoptionen zur Bedrohungsabwehr",
                    "type": "tactic_choice"
                },
                {
                    "id": "tactic_justification",
                    "title": "Tactic Justification",
                    "description": "Maßnahmenrechtfertigung: Begründung für die gewählten Maßnahmen",
                    "type": "tactic_justification"
                },
                {
                    "id": "tactic_mastery",
                    "title": "Tactic Mastery",
                    "description": "Maßnahmenbeherrschung: Konkrete Schritte zur Umsetzung der gewählten Handlungen",
                    "type": "tactic_mastery"
                },
                {
                    "id": "tactic_check_follow_up",
                    "title": "Tactic Check & Follow-Up",
                    "description": "Anschlusshandlungen: Schritte nach der Ausführung der Maßnahmen",
                    "type": "tactic_check_follow_up"
                }
            ]
        }

        template = default_template
        
        if self.template_path:
            try:
                with open(self.template_path, "r", encoding="utf-8") as f:
                    template = json.load(f)

                logger.info(f"Template loaded: {self.template_path}")
            except Exception as e:
                logger.error(f"Error loading template: {e}")
                logger.info("Using default template based on the example script")
        else:
            logger.info("No template path specified. Using default template based on the example script")
        
        # WICHTIGE VERBESSERUNG: Stelle sicher, dass alle section IDs Strings sind
        try:
            if "sections" in template and isinstance(template["sections"], list):
                for i, section in enumerate(template["sections"]):
                    if "id" in section and not isinstance(section["id"], str):
                        original_id = section["id"]
                        section["id"] = str(original_id)
                        logger.warning(f"Converted section ID {original_id} (type: {type(original_id).__name__}) to string at index {i}")
                        
                    # Stelle sicher, dass auch "type" ein String ist
                    if "type" in section and not isinstance(section["type"], str):
                        original_type = section["type"]
                        section["type"] = str(original_type)
                        logger.warning(f"Converted section type {original_type} (type: {type(original_type).__name__}) to string at index {i}")
        except Exception as e:
            logger.error(f"Error while ensuring section IDs are strings: {e}")
        
        return template

    def get_section_by_id(self, section_id: str) -> Optional[Dict[str, Any]]:
        """
        Returns a section of the template by its ID.

        Args:
            section_id: ID of the section

        Returns:
            Section as a dictionary or None if not found
        """
        for section in self.template["sections"]:
            if section["id"] == section_id:
                return section

        return None

    def get_next_section(self, completed_sections: List[str]) -> Optional[Dict[str, Any]]:
        """
        Returns the next section that hasn't been completed.

        Args:
            completed_sections: List of already completed sections

        Returns:
            Next section as a dictionary or None if all are completed
        """
        for section in self.template["sections"]:
            if section["id"] not in completed_sections:
                return section

        return None

    def create_script_from_responses(self, section_responses: Dict[str, str], context_info: Dict[str, str]) -> Dict[str, Any]:
        """
        Creates a script from the given responses.

        Args:
            section_responses: Dictionary with section IDs as keys and contents as values
            context_info: Dictionary with context information

        Returns:
            Complete script as a dictionary
        """
        script = copy.deepcopy(self.template)

        # Adjust title and description
        organization = context_info.get("Für welche Art von Organisation erstellen wir den E-Learning-Kurs (z.B. Krankenhaus, Bank, Behörde)?", "")
        audience = context_info.get("Welche Mitarbeitergruppen sollen geschult werden?", "")

        if organization:
            script["title"] = f'Skript „Umgang mit Informationssicherheit für {organization}"'
            script["description"] = f"Willkommen zum Trainingsmodul, in dem Sie lernen, wie Beschäftigte in {organization} mit Informationssicherheit umgehen."

        # Add contents to the sections
        for section in script["sections"]:
            section_id = section["id"]
            if section_id in section_responses:
                section["content"] = section_responses[section_id]

        return script