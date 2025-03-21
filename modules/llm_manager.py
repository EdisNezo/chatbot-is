import re
import random
import logging
from typing import List, Dict, Any, Tuple, Optional
from langchain.prompts import PromptTemplate
from langchain_core.prompts import PromptTemplate
from langchain_ollama.llms import OllamaLLM
from langchain_core.runnables import RunnablePassthrough
from langchain.callbacks.base import BaseCallbackHandler
from langchain.chains import LLMChain

# Logging-Konfiguration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Callback-Handler für verbessertes Logging und Überwachung von LLM-Antworten
class LLMCallbackHandler(BaseCallbackHandler):
    def __init__(self):
        self.current_token_count = 0
        self.current_tokens = []
        # Muster für typische Halluzinationsindikatoren
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
        """Wird aufgerufen, wenn das LLM eine Anfrage erhält."""
        self.current_token_count = 0
        self.current_tokens = []
        self.potential_hallucinations = []

    def on_llm_new_token(self, token: str, **kwargs):
        """Wird aufgerufen, wenn das LLM einen neuen Token generiert."""
        self.current_token_count += 1
        self.current_tokens.append(token)

        # Überprüfe auf potenzielle Halluzinationen
        current_text = "".join(self.current_tokens[-50:])  # Überprüfe nur die letzten 50 Tokens
        for pattern in self.hallucination_patterns:
            if re.search(pattern, current_text, re.IGNORECASE):
                self.potential_hallucinations.append((pattern, current_text))
                logger.warning(f"Potenzielle Halluzination erkannt: {pattern} in '{current_text}'")

    def on_llm_end(self, response, **kwargs):
        """Wird aufgerufen, wenn das LLM eine Antwort abgeschlossen hat."""
        full_response = "".join(self.current_tokens)
        logger.info(f"LLM-Antwort abgeschlossen. {self.current_token_count} Tokens generiert.")

        # Zusammenfassung der potenziellen Halluzinationen
        if self.potential_hallucinations:
            logger.warning(f"Insgesamt {len(self.potential_hallucinations)} potenzielle Halluzinationen erkannt.")
        else:
            logger.info("Keine potenziellen Halluzinationen erkannt.")

    def on_llm_error(self, error, **kwargs):
        """Wird aufgerufen, wenn im LLM ein Fehler auftritt."""
        logger.error(f"LLM-Fehler aufgetreten: {error}")


# Fallback-Modell für den Fall, dass Ollama nicht verfügbar ist
class DummyLLM:
    """Ein einfaches Fallback-LLM, das vordefinierte Antworten zurückgibt"""
    
    def __init__(self):
        logger.warning("Verwende DummyLLM aufgrund eines Initialisierungsfehlers mit dem echten LLM")
    
    def __call__(self, prompt):
        """Einfache Implementierung, die eine vordefinierte Antwort zurückgibt"""
        if "frage" in prompt.lower() or "question" in prompt.lower():
            return "Können Sie mir mehr über Ihre täglichen Abläufe im Krankenhaus erzählen, besonders wenn Sie mit Patientendaten oder E-Mails arbeiten?"
        elif "inhalt" in prompt.lower() or "content" in prompt.lower():
            return "Ein typischer Arbeitstag im Krankenhaus beginnt mit dem Überprüfen Ihrer E-Mails und der Patientendaten. Achten Sie dabei besonders auf ungewöhnliche Anfragen oder verdächtige Absender. Bei Verdacht auf Phishing-E-Mails sollten Sie diese nicht öffnen und sofort der IT-Abteilung melden."
        else:
            return "Ich bin ein Hilfeassistent für Informationssicherheit im Gesundheitswesen. Wie kann ich Ihnen bei der Erstellung eines Schulungsskripts helfen?"


class LLMManager:
    """
    Verwaltet die Interaktion mit dem Large Language Model.
    """

    def __init__(self, model_name: str = "mistral"):
        """
        Initialisiert den LLMManager.

        Args:
            model_name: Name des zu verwendenden LLM-Modells
        """
        # LLM-Callback für verbesserte Überwachung
        self.callback_handler = LLMCallbackHandler()

        # Initialisiere das LLM mit Callback
        self.llm = OllamaLLM(
            model=model_name,
            callbacks=[self.callback_handler],
        )
        
        # Teste die LLM-Verbindung
        try:
            test_result = self.llm('Test')
            logger.info(f'LLM erfolgreich initialisiert mit Modell {model_name}')
        except Exception as e:
            logger.error(f'Fehler bei der Verbindung zu Ollama: {e}')
            logger.warning('Fallback auf Dummy-LLM. Überprüfen Sie, ob Ollama läuft.')
            self.llm = DummyLLM()

        # Definiere Standardprompts für verschiedene Aufgaben
        self.prompts = {
            "question_generation": self._create_question_generation_prompt(),
            "content_generation": self._create_content_generation_prompt(),
            "hallucination_check": self._create_hallucination_check_prompt(),
            "key_info_extraction": self._create_key_info_extraction_prompt()
        }

        # Erstelle LLM-Chains für die verschiedenen Aufgaben
        self.chains = {
            name: LLMChain(llm=self.llm, prompt=prompt)
            for name, prompt in self.prompts.items()
        }

    def _create_question_generation_prompt(self) -> PromptTemplate:
        """
        Erstellt eine Prompt-Vorlage für die Fragengenerierung mit Fokus auf den Gesundheitsbereich.

        Returns:
            PromptTemplate Objekt
        """
        template = """
        Du bist ein freundlicher Berater, der auf Deutsch mit Kunden aus dem Gesundheitsbereich kommuniziert. Alle deine Antworten MÜSSEN auf Deutsch sein.

        Deine Aufgabe ist es, eine präzise Frage zu stellen, die einem Mitarbeiter im Krankenhaus hilft, über konkrete Prozesse, Abläufe und Risiken in seinem Arbeitsalltag zu sprechen. Der Mitarbeiter hat KEIN Fachwissen über Informationssicherheit und kennt Begriffe wie "Threat Awareness" oder "Bedrohungsbewusstsein" nicht.

        Formuliere eine freundliche, leicht verständliche Frage auf Deutsch, die sich auf konkrete Alltagssituationen im Krankenhaus bezieht.
        Das Thema gehört zum Bereich: {section_title}
        Die Beschreibung dieses Bereichs ist: {section_description}

        Berücksichtige dabei:
        - Organisation: {organization} (Gesundheitseinrichtung)
        - Zielgruppe: {audience} (z.B. Ärzte, Pflegepersonal, Verwaltung)
        - Relevanter Kontext: {context_text}

        WICHTIG: Formuliere Fragen, die folgende Aspekte ansprechen:

        Für "Threat Awareness / Bedrohungsbewusstsein":
        - Frage nach typischen Arbeitssituationen, in denen sensible Patientendaten genutzt werden
        - Frage nach dem täglichen Umgang mit digitalen Geräten, E-Mails oder medizinischen Systemen
        - Beispiel: "Wie sieht ein typischer Arbeitstag für Sie aus, wenn Sie mit Patientendaten arbeiten oder E-Mails bearbeiten?"

        Für "Threat Identification / Bedrohungserkennung":
        - Frage nach auffälligen oder verdächtigen Situationen, die schon einmal vorgekommen sind
        - Frage nach ungewöhnlichen E-Mails, Anfragen oder Verhalten von Personen
        - Beispiel: "Ist Ihnen schon einmal eine E-Mail oder Anfrage seltsam vorgekommen? Was genau hat Sie misstrauisch gemacht?"

        Für "Threat Impact Assessment / Bedrohungsausmaß":
        - Frage nach möglichen Folgen, wenn sensible Daten verloren gehen oder in falsche Hände geraten
        - Frage nach Auswirkungen auf die Patientenversorgung bei IT-Ausfällen
        - Beispiel: "Was würde in Ihrem Arbeitsbereich passieren, wenn plötzlich alle Patientendaten nicht mehr verfügbar wären?"

        Für "Tactic Choice / Taktische Maßnahmenauswahl":
        - Frage nach bestehenden Vorgehensweisen bei ungewöhnlichen Situationen
        - Frage nach aktuellen Sicherheitsmaßnahmen im Arbeitsalltag
        - Beispiel: "Wie gehen Sie aktuell vor, wenn Sie unsicher sind, ob eine E-Mail echt ist oder ein Sicherheitsrisiko darstellt?"

        Für "Tactic Justification / Maßnahmenrechtfertigung":
        - Frage nach Gründen für bestimmte Sicherheitsmaßnahmen
        - Frage nach dem wahrgenommenen Nutzen bestehender Sicherheitsregeln
        - Beispiel: "Warum halten Sie bestimmte Sicherheitsmaßnahmen in Ihrem Arbeitsalltag für besonders wichtig?"

        Für "Tactic Mastery / Maßnahmenbeherrschung":
        - Frage nach konkreten Schritten und Prozessen bei der täglichen Arbeit
        - Frage nach dem Umgang mit spezifischen Situationen (z.B. verdächtige E-Mails)
        - Beispiel: "Welche konkreten Schritte unternehmen Sie, wenn Sie eine verdächtige E-Mail erhalten?"

        Für "Tactic Check & Follow-Up / Anschlusshandlungen":
        - Frage nach Nachbereitung von Vorfällen oder Problemen
        - Frage nach Informationsfluss und Kommunikation nach einem Vorfall
        - Beispiel: "Was passiert in Ihrer Einrichtung, nachdem ein IT-Sicherheitsvorfall gemeldet wurde? Wie bleiben alle informiert?"

        Deine Frage sollte:
        1. Sich auf den täglichen Klinik- oder Krankenhauskontext beziehen
        2. Auf die spezifische Zielgruppe ({audience}) zugeschnitten sein
        3. Offen formuliert sein und ausführliche Antworten fördern
        4. Für einen Nicht-IT-Experten verständlich sein
        5. So formuliert sein, dass der Mitarbeiter aus seiner eigenen Erfahrung berichten kann
        6. Immer auf Deutsch gestellt sein!
        
        Gib nur die Frage zurück, keine Erklärungen oder Einleitungen.
        """

        return PromptTemplate(
            template=template,
            input_variables=["section_title", "section_description", "context_text",
                            "organization", "audience"]
        )

    def _create_content_generation_prompt(self) -> PromptTemplate:
        """
        Erstellt eine Prompt-Vorlage für die Inhaltsgenerierung mit Fokus auf den Gesundheitsbereich.
        
        Returns:
            PromptTemplate Objekt
        """
        template = """
        Erstelle den Inhalt für den Abschnitt "{section_title}" eines E-Learning-Kurses zur Informationssicherheit für den Gesundheitsbereich.

        WICHTIG: Der gesamte Inhalt MUSS auf Deutsch sein! Verwende durchgehend eine klare, präzise deutsche Sprache ohne Fachbegriffe aus dem Englischen.

        Die Antwort des Kunden zu diesem Thema/Abschnitt war:
        "{user_response}"

        Basierend auf dieser Antwort sollst du einen Skriptabschnitt erstellen, der:
        1. Speziell auf den Gesundheitsbereich und das beschriebene Krankenhaus-Umfeld zugeschnitten ist
        2. Konkrete, alltagsnahe Beispiele aus dem Klinikalltag enthält
        3. Prägnante, handlungsorientierte Anleitungen bietet
        4. Eine logische Struktur aufweist, die leicht zu verstehen und zu befolgen ist
        5. Auf genau einen konkreten Bedrohungsvektor oder Sicherheitsaspekt fokussiert ist
        6. In einem direkten, anleitenden Ton geschrieben ist (wie ein Schulungsskript für ein Video)

        Halte dich am folgenden STRUKTUR-FORMAT für jeden Abschnitt:
        1. Für "Threat Awareness / Bedrohungsbewusstsein": Beschreibe eine typische Arbeitssituation im Krankenhaus, in der ein Sicherheitsrisiko auftreten könnte
        2. Für "Threat Identification / Bedrohungserkennung": Erkläre anhand konkreter Merkmale, wie man die spezifische Bedrohung erkennt
        3. Für "Threat Impact Assessment / Bedrohungsausmaß": Liste die möglichen Konsequenzen der Bedrohung für das Krankenhaus und die Patientenversorgung auf
        4. Für "Tactic Choice / Taktische Maßnahmenauswahl": Beschreibe die konkreten Handlungsoptionen (2-3) zur Bedrohungsabwehr
        5. Für "Tactic Justification / Maßnahmenrechtfertigung": Begründe, warum die vorgeschlagenen Maßnahmen wirksam und angemessen sind
        6. Für "Tactic Mastery / Maßnahmenbeherrschung": Gib eine schrittweise Anleitung zur Umsetzung der Maßnahmen
        7. Für "Tactic Check & Follow-Up / Anschlusshandlungen": Erkläre, welche weiteren Maßnahmen nach dem Vorfall zu ergreifen sind

        Wichtige Stilregeln:
        - Verwende eine direkte, ansprechende Sprache
        - Halte Absätze kurz (max. 3-4 Sätze)
        - Verwende Aufzählungspunkte für Listen und Schritte
        - Beziehe dich auf Rollen im Krankenhaus (z.B. Ärzte, Pflegepersonal, Verwaltungsmitarbeiter)
        - Verwende aktivierende Verben (z.B. "überprüfen Sie", "achten Sie auf", "kontaktieren Sie")
        - Vermeide abstrakte Konzepte; nutze stattdessen konkrete Beispiele
        - Füge "Nice to know"-Abschnitte ein, wo es sinnvoll ist

        Orientiere dich an diesem BEISPIELFORMAT:
        ```
        Ein neuer Arbeitstag beginnt in der Klinik und wie jeden Morgen überprüfen Sie zunächst Ihr E-Mail-Postfach. Sie erhalten täglich zahlreiche wichtige Nachrichten von Kolleginnen und Kollegen sowie von externen Dienstleistern.

        [Hier kommt der inhaltliche Teil des Abschnitts, der dem oben beschriebenen Format entspricht]

        Nice to know: [Hier ein zusätzlicher Tipp oder Hintergrundwissen, falls relevant]
        ```

        Kontext und weitere Informationen:
        - Organisation: {organization}
        - Zielgruppe: {audience}
        - Dauer: {duration}
        - Relevante Fachinformationen: {context_text}

        Gib nur den fertigen Inhalt für den Abschnitt zurück, keine Einleitungen oder zusätzlichen Erklärungen. Stellen Sie sicher, dass der Inhalt für eine Person ohne IT-Hintergrund verständlich ist.
        """

        return PromptTemplate(
            template=template,
            input_variables=["section_title", "section_description", "user_response",
                            "organization", "audience", "duration", "context_text"]
        )
        
    def _create_hallucination_check_prompt(self) -> PromptTemplate:
        """
        Erstellt eine Prompt-Vorlage für die Halluzinationsüberprüfung mit Fokus auf den Gesundheitsbereich.

        Returns:
            PromptTemplate Objekt
        """
        template = """
        Überprüfe den folgenden Inhalt für einen E-Learning-Kurs zur Informationssicherheit im Gesundheitswesen auf mögliche Ungenauigkeiten, falsche Informationen oder Halluzinationen.

        Zu prüfender Text:
        {content}

        Kontext aus der Kundenantwort:
        {user_input}

        Verfügbare Fachinformationen:
        {context_text}

        Bitte identifiziere:
        1. Aussagen über Informationssicherheit, die nicht durch die verfügbaren Fachinformationen gestützt werden
        2. Empfehlungen oder Maßnahmen, die für den beschriebenen Krankenhaus-Kontext ungeeignet oder unrealistisch sein könnten
        3. Technische Begriffe oder Konzepte, die falsch verwendet wurden oder im Gesundheitsbereich anders interpretiert werden
        4. Widersprüche zu bewährten Sicherheitspraktiken im Gesundheitswesen
        5. Unzutreffende Behauptungen über Bedrohungen oder deren Auswirkungen auf die Patientenversorgung

        WICHTIG: Achte besonders darauf, dass alle Inhalte spezifisch auf das Gesundheitswesen zugeschnitten sind und nicht zu allgemein oder für andere Branchen formuliert wurden.

        Für jede identifizierte Problemstelle:
        - Zitiere die betreffende Textpassage
        - Erkläre, warum dies problematisch ist
        - Schlage eine fachlich korrekte Alternative vor, die besser auf den Krankenhaus-Kontext passt

        Falls keine inhaltlichen Probleme gefunden wurden, prüfe noch folgende Aspekte:
        1. Hat der Text die richtige Struktur nach den Vorgaben des E-Learning-Formats?
        2. Ist der Text spezifisch genug auf den Krankenhaus-Kontext zugeschnitten?
        3. Enthält der Text konkrete und praktische Beispiele aus dem klinischen Alltag?

        Falls der Text vollständig korrekt ist, sowohl inhaltlich als auch strukturell, antworte mit "KEINE_PROBLEME".
        """

        return PromptTemplate(
            template=template,
            input_variables=["content", "user_input", "context_text"]
        )

    def _create_key_info_extraction_prompt(self) -> PromptTemplate:
        """
        Erstellt eine Prompt-Vorlage für die Extraktion von Schlüsselinformationen mit Fokus auf den Gesundheitsbereich.

        Returns:
            PromptTemplate Objekt
        """
        template = """
        Analysiere die folgende Antwort eines Mitarbeiters aus dem Gesundheitsbereich, der über die Prozesse und den Kontext seiner Arbeit im Krankenhaus spricht.
        Der Mitarbeiter hat auf eine Frage zu "{section_type}" geantwortet, für die wir passende Informationssicherheitsinhalte erstellen wollen.

        Mitarbeiterantwort:
        "{user_response}"

        Extrahiere die wichtigsten Informationen zu folgenden Aspekten:
        1. Spezifische medizinische Prozesse oder Arbeitsabläufe, die erwähnt werden
        2. Umgang mit Patientendaten und sensiblen Informationen
        3. Potenzielle Sicherheitsrisiken oder Schwachstellen im beschriebenen Arbeitsablauf
        4. Erwähnte Kommunikationswege (z.B. E-Mail, Telefon, Fax, medizinische Systeme)
        5. Anzeichen von Awareness oder fehlendem Bewusstsein für Sicherheitsrisiken
        6. Spezifische Herausforderungen im Krankenhausalltag, die Sicherheitsrisiken erhöhen könnten

        Gib nur eine Liste von 5-8 konkreten Schlüsselinformationen zurück, die für die Erstellung von Schulungsinhalten zum Thema "{section_type}" im Gesundheitsbereich relevant sind. Bevorzuge dabei spezifische Aspekte, die in der Antwort tatsächlich vorkommen, statt allgemeine Annahmen.

        Format: Gib jede Schlüsselinformation als kurzen, prägnanten Punkt zurück.
        """

        return PromptTemplate(
            template=template,
            input_variables=["section_type", "user_response"]
        )
        
    def generate_question(self, section_title: str, section_description: str,
                         context_text: str, organization: str, audience: str) -> str:
        """
        Generiert eine Frage für einen Abschnitt der Vorlage.

        Args:
            section_title: Titel des Abschnitts
            section_description: Beschreibung des Abschnitts
            context_text: Kontextinformationen aus dem Retrieval
            organization: Art der Organisation
            audience: Zielgruppe für das Training

        Returns:
            Generierte Frage
        """

        try:
            # Formatiere den Prompt
            prompt = self.prompts["question_generation"].format(
                section_title=section_title,
                section_description=section_description,
                context_text=context_text,
                organization=organization,
                audience=audience,
                user_response="",  # Nicht benötigt für die Fragengenerierung
                duration=""  # Nicht benötigt für die Fragengenerierung
            )
            
            # Rufe das LLM auf
            response = self.llm(prompt)
            
            # Überprüfe Antworttyp
            if not isinstance(response, str):
                logger.error(f"LLM hat keine String-Antwort für die Fragengenerierung zurückgegeben: {type(response)}")
                # Stelle eine Fallback-Frage basierend auf dem Abschnittstitel bereit
                return f"Können Sie mir mehr über Ihren Umgang mit {section_title} im Krankenhausalltag erzählen?"
                
            return response.strip()
        except Exception as e:
            logger.error(f"Fehler bei der Fragengenerierung: {e}")
            # Fallback-Frage mit Fokus auf Gesundheitswesen
            return f"Wie gehen Sie in Ihrem Krankenhausalltag mit dem Thema {section_title} um? Können Sie konkrete Beispiele nennen?"

    def generate_content(self, section_title: str, section_description: str,
                        user_response: str, organization: str, audience: str,
                        duration: str, context_text: str) -> str:
        """
        Generiert Inhalte für einen Abschnitt des Trainings.

        Args:
            section_title: Titel des Abschnitts
            section_description: Beschreibung des Abschnitts
            user_response: Antwort des Benutzers
            organization: Art der Organisation
            audience: Zielgruppe für das Training
            duration: Maximale Dauer des Trainings
            context_text: Kontextinformationen aus dem Retrieval

        Returns:
            Generierter Inhalt
        """
        try:
            response = self.chains["content_generation"].run({
                "section_title": section_title,
                "section_description": section_description,
                "user_response": user_response,
                "organization": organization,
                "audience": audience,
                "duration": duration,
                "context_text": context_text
            })
            
            # Stelle sicher, dass wir einen String zurückgeben
            if not isinstance(response, str):
                logger.error(f"Inhaltsgenerierung hat keinen String zurückgegeben: {type(response)}")
                return "Ein Fehler ist bei der Generierung des Inhalts aufgetreten. Bitte versuchen Sie es erneut."
                
            return response.strip()
        
        except Exception as e:
            logger.error(f"Fehler bei der Inhaltsgenerierung: {e}")
            
            # Stelle Fallback-Inhalt bereit
            fallback_intro = f"Ein neuer Arbeitstag beginnt in {organization} und wie jeden Morgen überprüfen Sie zunächst Ihr E-Mail-Postfach."
            fallback_content = f"""
            {fallback_intro}
            
            Als {audience} müssen Sie besonders auf die Sicherheit von Patientendaten achten. Achten Sie auf verdächtige E-Mails, ungewöhnliche Anhänge oder Links. Im Zweifel kontaktieren Sie immer die IT-Abteilung.
            
            Die Folgen eines Sicherheitsvorfalls können schwerwiegend sein, von Datenverlust bis hin zur Beeinträchtigung der Patientenversorgung.
            
            Prüfen Sie stets:
            • Den Absender jeder E-Mail
            • Die Plausibilität der Anfrage
            • Die Echtheit von Anhängen und Links
            
            Im Falle eines Verdachts, melden Sie den Vorfall umgehend.
            """
            
            return fallback_content.strip()

    def check_hallucinations(self, content: str, user_input: str, context_text: str) -> Tuple[bool, str]:
        """
        Überprüft den generierten Inhalt auf Halluzinationen.

        Args:
            content: Generierter Inhalt
            user_input: Ursprüngliche Benutzereingabe
            context_text: Kontextinformationen aus dem Retrieval

        Returns:
            Tuple aus (hat_probleme, korrigierter_inhalt)
        """
        try:
            response = self.chains["hallucination_check"].run({
                "content": content,
                "user_input": user_input,
                "context_text": context_text
            })

            # Überprüfe, ob Probleme gefunden wurden
            hat_probleme = "KEINE_PROBLEME" not in response

            # Korrigiere den Inhalt basierend auf der Überprüfung
            if hat_probleme:
                korrigierter_inhalt = self.generate_content_with_corrections(content, response)
            else:
                korrigierter_inhalt = content

            return hat_probleme, korrigierter_inhalt
            
        except Exception as e:
            logger.error(f"Fehler bei der Halluzinationsüberprüfung: {e}")
            # Bei einem Fehler nehmen wir an, dass es möglicherweise Probleme gibt, und geben den ursprünglichen Inhalt zurück
            return True, content

    def generate_content_with_corrections(self, original_content: str, correction_feedback: str) -> str:
        """
        Generiert korrigierten Inhalt basierend auf Feedback.

        Args:
            original_content: Ursprünglicher Inhalt
            correction_feedback: Feedback für die Korrektur

        Returns:
            Korrigierter Inhalt
        """
        correction_prompt = f"""
        Überarbeite den folgenden E-Learning-Inhalt für ein Schulungsskript im Gesundheitsbereich basierend auf dem Feedback:

        Originaltext:
        {original_content}

        Feedback zur Überarbeitung:
        {correction_feedback}

        Erstelle eine verbesserte Version des Textes, die:
        1. Die identifizierten Probleme behebt
        2. Fachlich korrekt und präzise ist
        3. Spezifisch auf den Krankenhaus-Kontext zugeschnitten ist
        4. Dem Stil und Format eines E-Learning-Skripts entspricht
        5. Konkrete Beispiele aus dem Klinikalltag enthält
        6. Klare, handlungsorientierte Anweisungen bietet
        7. Das Design der Beispielskripte "Example_Skript_Phishing_HZI_V1" und "Ärzte – Verwaltende Aufgaben" übernimmt

        Achte besonders darauf, dass der Text wie ein Schulungsskript für ein Video klingt, nicht wie ein allgemeiner Artikel über Informationssicherheit.

        Gib nur den überarbeiteten Text zurück, keine zusätzlichen Erklärungen.
        """

        try:
            corrected_content = self.llm(correction_prompt)
            
            # Stelle sicher, dass wir einen String zurückgeben
            if not isinstance(corrected_content, str):
                logger.error(f"Korrektur hat keinen String zurückgegeben: {type(corrected_content)}")
                return original_content
                
            return corrected_content.strip()
            
        except Exception as e:
            logger.error(f"Fehler bei der Inhaltskorrektur: {e}")
            return original_content

    def extract_key_information(self, section_type: str, user_response: str) -> List[str]:
        """
        Extrahiert Schlüsselinformationen aus der Antwort des Benutzers.
        
        Returns:
            Liste von Schlüsselbegriffen als Strings
        """
        try:
            # Formatiere den Prompt
            prompt = self.prompts["key_info_extraction"].format(
                section_type=section_type,
                user_response=user_response
            )
            
            # Rufe das LLM auf
            response = self.llm(prompt)
            
            # Überprüfe Antworttyp
            if not isinstance(response, str):
                logger.error(f"LLM hat keine String-Antwort für die Schlüsselextraktion zurückgegeben: {type(response)}")
                return []  # Gib leere Liste als Fallback zurück
                
            # Verarbeite die Antwort zu einer Liste
            key_concepts = []
            for concept in response.strip().split("\n"):
                if concept.strip():
                    key_concepts.append(concept.strip())
                    
            # Abschließende Validierung
            if not isinstance(key_concepts, list):
                logger.error(f"Verarbeitete key_concepts ist keine Liste: {type(key_concepts)}")
                return []
                
            return key_concepts
        except Exception as e:
            logger.error(f"Fehler bei der Extraktion von Schlüsselinformationen: {e}")
            return []  # Gib leere Liste als Fallback zurück

    def advanced_hallucination_detection(self, content: str) -> Dict[str, Any]:
        """
        Führt eine erweiterte Halluzinationserkennung durch.

        Args:
            content: Zu überprüfender Inhalt

        Returns:
            Dictionary mit Analyseergebnissen
        """
        # Muster für typische Halluzinationsindikatoren
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
            ],
            "Gesundheitswesen-spezifische Ungenauigkeiten": [
                r"patient record", r"EHR", r"electronic health record",
                r"HIPAA", r"HITECH", r"GDPR", r"patient portal"
            ]
        }

        results = {
            "detected_patterns": {},
            "confidence_score": 1.0,  # Anfangswert, wird für jedes gefundene Muster reduziert
            "suspicious_sections": []
        }

        # Überprüfe den Text auf Muster
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

                    # Reduziere den Vertrauenswert für jeden Fund
                    results["confidence_score"] = max(0.1, results["confidence_score"] - 0.05)

                    # Speichere den Abschnitt als verdächtig
                    results["suspicious_sections"].append(context)

            if category_matches:
                results["detected_patterns"][category] = category_matches

        # Überprüfe auf einen Mangel an gesundheitsspezifischer Terminologie
        if not any(term in content_lower for term in ["krankenhaus", "klinik", "patient", "arzt", "pflege"]):
            results["suspicious_sections"].append("Mangel an krankenhausspezifischer Terminologie")
            results["confidence_score"] = max(0.1, results["confidence_score"] - 0.2)
            if "Fehlender Bezug zum Gesundheitswesen" not in results["detected_patterns"]:
                results["detected_patterns"]["Fehlender Bezug zum Gesundheitswesen"] = []
            results["detected_patterns"]["Fehlender Bezug zum Gesundheitswesen"].append({
                "pattern": "Keine Gesundheitsbezüge",
                "context": "Im gesamten Text fehlen spezifische Bezüge zum Krankenhaus-Kontext"
            })

        return results