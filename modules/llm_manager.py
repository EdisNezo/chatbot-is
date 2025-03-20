import re
import logging
from typing import List, Dict, Any, Tuple, Optional
from langchain.chains import LLMChain
from langchain.prompts import PromptTemplate
from langchain_community.llms import Ollama
from langchain.callbacks.base import BaseCallbackHandler

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Callback handler for improved logging and monitoring of LLM responses
class LLMCallbackHandler(BaseCallbackHandler):
    def __init__(self):
        self.current_token_count = 0
        self.current_tokens = []
        self.hallucination_patterns = [
            r"ich weiß nicht",
            r"ich bin mir nicht sicher",
            r"es tut mir leid",
            r"entschuldigung",
            r"ich habe keine information",
            r"ich wurde nicht trainiert",
            r"ich kann nicht",
        ]
        self.potential_hallucinations = []

    def on_llm_start(self, serialized, prompts, **kwargs):
        """Called when the LLM receives a request."""
        self.current_token_count = 0
        self.current_tokens = []
        self.potential_hallucinations = []

    def on_llm_new_token(self, token: str, **kwargs):
        """Called when the LLM generates a new token."""
        self.current_token_count += 1
        self.current_tokens.append(token)

        # Check for potential hallucinations
        current_text = "".join(self.current_tokens[-50:])  # Only check the last 50 tokens
        for pattern in self.hallucination_patterns:
            if re.search(pattern, current_text, re.IGNORECASE):
                self.potential_hallucinations.append((pattern, current_text))
                logger.warning(f"Potential hallucination detected: {pattern} in '{current_text}'")

    def on_llm_end(self, response, **kwargs):
        """Called when the LLM completes a response."""
        full_response = "".join(self.current_tokens)
        logger.info(f"LLM response completed. Generated {self.current_token_count} tokens.")

        # Summary of potential hallucinations
        if self.potential_hallucinations:
            logger.warning(f"Total of {len(self.potential_hallucinations)} potential hallucinations detected.")
        else:
            logger.info("No potential hallucinations detected.")

    def on_llm_error(self, error, **kwargs):
        """Called when an error occurs in the LLM."""
        logger.error(f"LLM error occurred: {error}")


class LLMManager:
    """
    Manages the interaction with the Large Language Model.
    """

    def __init__(self, model_name: str = "mistral"):
        """
        Initializes the LLMManager.

        Args:
            model_name: Name of the LLM model to use
        """
        # LLM callback for improved monitoring
        self.callback_handler = LLMCallbackHandler()

        # Initialize the LLM with callback
        self.llm = Ollama(
            model=model_name,
            callbacks=[self.callback_handler],
        )

        # Define standard prompts for different tasks
        self.prompts = {
            "question_generation": self._create_question_generation_prompt(),
            "content_generation": self._create_content_generation_prompt(),
            "hallucination_check": self._create_hallucination_check_prompt(),
            "key_info_extraction": self._create_key_info_extraction_prompt()
        }

        # Create LLM chains for the different tasks
        self.chains = {
            name: LLMChain(llm=self.llm, prompt=prompt)
            for name, prompt in self.prompts.items()
        }

    def _create_question_generation_prompt(self) -> PromptTemplate:
        """
        Creates a prompt template for question generation.

        Returns:
            PromptTemplate object
        """
        template = """
        Du bist ein freundlicher Berater, der auf Deutsch mit Kunden kommuniziert. Alle deine Antworten MÜSSEN auf Deutsch sein.

        Deine Aufgabe ist es, Fragen zu stellen, die einem nicht-technischen Kunden helfen, über die Prozesse und den Kontext seines Unternehmens
        zu sprechen. Der Kunde hat KEIN Fachwissen über Informationssicherheit und kennt Begriffe wie "Threat Awareness" oder "Bedrohungsbewusstsein" nicht.

        Formuliere eine freundliche, leicht verständliche Frage auf Deutsch, die sich auf konkrete Alltagssituationen bezieht, statt auf abstrakte Sicherheitskonzepte.
        Das Thema gehört zum Bereich: {section_title}
        Die Beschreibung dieses Bereichs ist: {section_description}

        Berücksichtige dabei:
        - Organisation: {organization}
        - Zielgruppe: {audience}
        - Relevanter Kontext: {context_text}

        WICHTIG: Vermeide komplizierte Fachbegriffe. Ersetze sie durch konkrete, alltagsnahe Begriffe:
        - Statt "Threat Awareness / Bedrohungsbewusstsein" frage nach "typischen Situationen im Arbeitsalltag, die riskant sein könnten"
        - Statt "Threat Identification" frage nach "Anzeichen, dass etwas nicht stimmt" oder "verdächtigen Dingen"
        - Statt "Threat Impact Assessment" frage nach "Auswirkungen wenn etwas schiefgeht"
        - Statt "Tactic Choice" frage nach "üblichen Vorgehensweisen" oder "Handlungsmöglichkeiten"
        - Statt "Tactic Justification" frage nach "Gründen für bestimmte Vorgehensweisen"
        - Statt "Tactic Mastery" frage nach "konkreten Schritten im Alltag"
        - Statt "Tactic Check & Follow-Up" frage nach "was nach einem Vorfall passiert"

        Die Frage sollte:
        1. Sich auf die Geschäftsprozesse, tägliche Abläufe oder den Arbeitskontext des Kunden beziehen
        2. In einfacher, nicht-technischer Sprache formuliert sein
        3. Offen sein und ausführliche Antworten fördern
        4. KEINEN Fachjargon aus der Informationssicherheit enthalten
        5. So formuliert sein, dass der Kunde über seine eigenen Erfahrungen sprechen kann, ohne Sicherheitswissen zu benötigen
        6. Stelle die Fragen immer auf Deutsch!

        Beispielfragen:
        - "Wie sieht ein typischer Arbeitstag bei Ihnen aus, wenn Sie E-Mails bearbeiten oder mit externen Anfragen umgehen?"
        - "Gab es schon mal Situationen, in denen Sie bei einer Mitteilung oder Anfrage ein komisches Gefühl hatten?"
        - "Was würde in Ihrem Arbeitsbereich passieren, wenn plötzlich wichtige Daten oder Systeme nicht mehr verfügbar wären?"
        
        Gib nur die Frage zurück, keine Erklärungen oder Einleitungen.

        WICHTIG: Deine Antwort muss auf Deutsch sein! Verwende NICHT die englischen Fachbegriffe im Abschnittstitel.
        """

        return PromptTemplate(
            template=template,
            input_variables=["section_title", "section_description", "context_text",
                            "organization", "audience"]
        )

    def _create_content_generation_prompt(self) -> PromptTemplate:
        template = """
        Erstelle den Inhalt für den Abschnitt "{section_title}" eines E-Learning-Kurses zur Informationssicherheit.

        WICHTIG: Der gesamte Inhalt MUSS auf Deutsch sein! Verwende durchgehend die deutsche Sprache.

        Die Antwort des Kunden auf deine Frage nach den Unternehmensprozessen war:
        "{user_response}"

        Basierend auf dieser Antwort sollst du nun relevante Informationssicherheitsinhalte generieren, die:
        1. Speziell auf die beschriebenen Prozesse, Herausforderungen und den Unternehmenskontext zugeschnitten sind
        2. Praktische Sicherheitsmaßnahmen und bewährte Verfahren enthalten, die für diese Prozesse relevant sind
        3. Klare Anweisungen und Empfehlungen bieten, die die Zielgruppe verstehen und umsetzen kann
        4. Technische Konzepte auf eine zugängliche, nicht einschüchternde Weise erklären

        Kontext und weitere Informationen:
        - Abschnittsbeschreibung: {section_description}
        - Organisation: {organization}
        - Zielgruppe: {audience}
        - Dauer: {duration}
        - Relevante Informationen aus unserer Wissensdatenbank: {context_text}

        Der Inhalt sollte dem Format des Beispielskripts entsprechen und für Abschnitt "{section_title}" angemessen sein.

        Gib nur den fertigen Inhalt zurück, keine zusätzlichen Erklärungen.

        WICHTIG: Deine Antwort muss vollständig auf Deutsch sein!
        """

        return PromptTemplate(
            template=template,
            input_variables=["section_title", "section_description", "user_response",
                            "organization", "audience", "duration", "context_text"]
        )
        
    def _create_hallucination_check_prompt(self) -> PromptTemplate:
        """
        Creates a prompt template for hallucination checking.

        Returns:
            PromptTemplate object
        """
        template = """
        Überprüfe den folgenden Inhalt für einen E-Learning-Kurs zur Informationssicherheit auf mögliche Ungenauigkeiten oder Halluzinationen.

        Zu prüfender Text:
        {content}

        Kontext aus der Kundenantwort:
        {user_input}

        Verfügbare Fachinformationen:
        {context_text}

        Bitte identifiziere:
        1. Aussagen über Informationssicherheit, die nicht durch die verfügbaren Fachinformationen gestützt werden
        2. Empfehlungen oder Maßnahmen, die für den beschriebenen Unternehmenskontext ungeeignet sein könnten
        3. Technische Begriffe oder Konzepte, die falsch verwendet wurden
        4. Widersprüche zu bewährten Sicherheitspraktiken
        5. Unzutreffende Behauptungen über Bedrohungen oder deren Auswirkungen

        Für jede identifizierte Problemstelle:
        - Zitiere die betreffende Textpassage
        - Erkläre, warum dies problematisch ist
        - Schlage eine fachlich korrekte Alternative vor

        Falls keine Probleme gefunden wurden, antworte mit "KEINE_PROBLEME".
        """

        return PromptTemplate(
            template=template,
            input_variables=["content", "user_input", "context_text"]
        )

    def _create_key_info_extraction_prompt(self) -> PromptTemplate:
        """
        Creates a prompt template for extracting key information.

        Returns:
            PromptTemplate object
        """
        template = """
        Analysiere die folgende Antwort eines Kunden, der über die Prozesse und den Kontext seines Unternehmens spricht.
        Der Kunde hat auf eine Frage zu "{section_type}" geantwortet, für die wir passende Informationssicherheitsinhalte erstellen wollen.

        Kundenantwort:
        "{user_response}"

        Extrahiere:
        1. Die wichtigsten Geschäftsprozesse, Arbeitsabläufe oder Systeme, die erwähnt werden
        2. Potenzielle Informationssicherheits-Schwachstellen oder Risiken, die mit diesen Prozessen verbunden sein könnten
        3. Besondere Anforderungen oder Einschränkungen, die berücksichtigt werden sollten
        4. Branchenspezifische Aspekte, die relevant sein könnten
        5. Informationswerte oder schützenswerte Daten, die im Kontext wichtig sind

        Gib nur eine Liste von 5-8 Schlüsselbegriffen oder kurzen Phrasen zurück, die für die Suche nach relevanten Informationssicherheitsinhalten verwendet werden können. Schreibe keine Einleitungen oder Erklärungen.
        """

        return PromptTemplate(
            template=template,
            input_variables=["section_type", "user_response"]
        )
        
    def generate_question(self, section_title: str, section_description: str,
                         context_text: str, organization: str, audience: str) -> str:
        """
        Generates a question for a section of the template.

        Args:
            section_title: Title of the section
            section_description: Description of the section
            context_text: Context information from retrieval
            organization: Type of organization
            audience: Target audience for the training

        Returns:
            Generated question
        """
        max_context_length = 1000
        if len(context_text) > max_context_length:
            context_text = context_text[:max_context_length] + "..."

        try:
            response = self.chains["question_generation"].run({
                "section_title": section_title,
                "section_description": section_description,
                "context_text": context_text,
                "organization": organization,
                "audience": audience
            })
            return response.strip()
        except Exception as e:
            logger.error(f"Error during question generation: {e}")
            # Fallback on error
            return f"Können Sie mir etwas über {section_title} in Ihrem Unternehmen erzählen?"

    def generate_content(self, section_title: str, section_description: str,
                        user_response: str, organization: str, audience: str,
                        duration: str, context_text: str) -> str:
        """
        Generates content for a section of the training.

        Args:
            section_title: Title of the section
            section_description: Description of the section
            user_response: User's response
            organization: Type of organization
            audience: Target audience for the training
            duration: Maximum duration of the training
            context_text: Context information from retrieval

        Returns:
            Generated content
        """
        response = self.chains["content_generation"].run({
            "section_title": section_title,
            "section_description": section_description,
            "user_response": user_response,
            "organization": organization,
            "audience": audience,
            "duration": duration,
            "context_text": context_text
        })

        return response.strip()

    def check_hallucinations(self, content: str, user_input: str, context_text: str) -> Tuple[bool, str]:
        """
        Checks the generated content for hallucinations.

        Args:
            content: Generated content
            user_input: Original user input
            context_text: Context information from retrieval

        Returns:
            Tuple of (has_issues, corrected_content)
        """
        response = self.chains["hallucination_check"].run({
            "content": content,
            "user_input": user_input,
            "context_text": context_text
        })

        # Check if problems were found
        has_issues = "KEINE_PROBLEME" not in response

        # Correct the content based on the check
        if has_issues:
            corrected_content = self.generate_content_with_corrections(content, response)
        else:
            corrected_content = content

        return has_issues, corrected_content

    def generate_content_with_corrections(self, original_content: str, correction_feedback: str) -> str:
        """
        Generates corrected content based on feedback.

        Args:
            original_content: Original content
            correction_feedback: Feedback for correction

        Returns:
            Corrected content
        """
        correction_prompt = f"""
        Überarbeite den folgenden E-Learning-Inhalt basierend auf dem Feedback:

        Originaltext:
        {original_content}

        Feedback zur Überarbeitung:
        {correction_feedback}

        Erstelle eine verbesserte Version des Textes, die die identifizierten Probleme behebt, fachlich korrekt ist und trotzdem verständlich und ansprechend bleibt.
        Achte darauf, dass der Text weiterhin didaktisch gut aufbereitet ist und alle wichtigen Informationen enthält.

        Gib nur den überarbeiteten Text zurück, keine zusätzlichen Erklärungen.
        """

        corrected_content = self.llm(correction_prompt)

        return corrected_content.strip()

    def extract_key_information(self, section_type: str, user_response: str) -> List[str]:
        """
        Extracts key information from the user's response.

        Args:
            section_type: Type of section (e.g., "learning_objectives")
            user_response: User's response

        Returns:
            List of key terms
        """
        response = self.chains["key_info_extraction"].run({
            "section_type": section_type,
            "user_response": user_response
        })

        # Process the response into a list
        key_concepts = [
            concept.strip()
            for concept in response.strip().split("\n")
            if concept.strip()
        ]

        return key_concepts

    def advanced_hallucination_detection(self, content: str) -> Dict[str, Any]:
        """
        Performs advanced hallucination detection.

        Args:
            content: Content to check

        Returns:
            Dictionary with analysis results
        """
        # Patterns for typical hallucination indicators
        hallucination_patterns = {
            "Unsicherheit": [
                r"könnte sein", r"möglicherweise", r"eventuell", r"vielleicht",
                r"unter umständen", r"es ist denkbar", r"in der regel"
            ],
            "Widersprüche": [
                r"einerseits.*andererseits", r"jedoch", r"allerdings",
                r"im gegensatz dazu", r"wiederum"
            ],
            "Vage Aussagen": [
                r"irgendwie", r"gewissermaßen", r"im großen und ganzen",
                r"im allgemeinen", r"mehr oder weniger"
            ]
        }

        results = {
            "detected_patterns": {},
            "confidence_score": 1.0,  # Initial value, reduced for each pattern found
            "suspicious_sections": []
        }

        # Check the text for patterns
        content_lower = content.lower()

        for category, patterns in hallucination_patterns.items():
            category_matches = []
            for pattern in patterns:
                matches = re.finditer(pattern, content_lower)
                for match in matches:
                    start_pos = max(0, match.start() - 40)
                    end_pos = min(len(content_lower), match.end() + 40)
                    context = content_lower[start_pos:end_pos]
                    category_matches.append({
                        "pattern": pattern,
                        "context": context
                    })

                    # Reduce the confidence score for each finding
                    results["confidence_score"] = max(0.1, results["confidence_score"] - 0.05)

                    # Store the section as suspicious
                    results["suspicious_sections"].append(context)

            if category_matches:
                results["detected_patterns"][category] = category_matches

        return results