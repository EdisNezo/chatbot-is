import json
import copy
import logging
import random
import re
from typing import Dict, Any, List, Optional

# Logging-Konfiguration
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

class TemplateManager:
    """
    Verwaltet die Vorlage für den E-Learning-Kurs.
    """

    def __init__(self, template_path: str = None):
        """
        Initialisiert den TemplateManager.

        Args:
            template_path: Pfad zur Vorlagendatei
        """
        self.template_path = template_path
        self.template = self.load_template()

    def load_template(self) -> Dict[str, Any]:
        """
        Lädt die Vorlage aus der angegebenen Datei oder erstellt eine Standardvorlage
        basierend auf dem Beispielskript.

        Returns:
            Vorlage als Dictionary
        """
        # Verwende eine an das Beispielskript angepasste Vorlage
        default_template = {
            "title": "E-Learning-Kurs zur Informationssicherheit",
            "description": "Ein maßgeschneiderter Kurs zur Stärkung des Sicherheitsbewusstseins",
            "sections": [
                {
                    "id": "threat_awareness",
                    "title": "Threat Awareness / Bedrohungsbewusstsein",
                    "description": "Kontext und Ausgangssituationen, in denen Gefahren auftreten können",
                    "type": "threat_awareness"
                },
                {
                    "id": "threat_identification",
                    "title": "Threat Identification / Bedrohungserkennung",
                    "description": "Merkmale und Erkennungshinweise für potenzielle Gefahren",
                    "type": "threat_identification"
                },
                {
                    "id": "threat_impact_assessment",
                    "title": "Threat Impact Assessment / Bedrohungsausmaß",
                    "description": "Konsequenzen, die aus der Bedrohung entstehen können",
                    "type": "threat_impact_assessment"
                },
                {
                    "id": "tactic_choice",
                    "title": "Tactic Choice / Taktische Maßnahmenauswahl",
                    "description": "Handlungsoptionen zur Bedrohungsabwehr",
                    "type": "tactic_choice"
                },
                {
                    "id": "tactic_justification",
                    "title": "Tactic Justification / Maßnahmenrechtfertigung",
                    "description": "Begründung für die gewählten Maßnahmen",
                    "type": "tactic_justification"
                },
                {
                    "id": "tactic_mastery",
                    "title": "Tactic Mastery / Maßnahmenbeherrschung",
                    "description": "Konkrete Schritte zur Umsetzung der gewählten Handlungen",
                    "type": "tactic_mastery"
                },
                {
                    "id": "tactic_check_follow_up",
                    "title": "Tactic Check & Follow-Up / Anschlusshandlungen",
                    "description": "Schritte nach der Ausführung der Maßnahmen",
                    "type": "tactic_check_follow_up"
                }
            ]
        }

        template = default_template
        
        if self.template_path:
            try:
                with open(self.template_path, "r", encoding="utf-8") as f:
                    template = json.load(f)

                logger.info(f"Vorlage geladen: {self.template_path}")
            except Exception as e:
                logger.error(f"Fehler beim Laden der Vorlage: {e}")
                logger.info("Verwende Standardvorlage basierend auf dem Beispielskript")
        else:
            logger.info("Kein Vorlagenpfad angegeben. Verwende Standardvorlage basierend auf dem Beispielskript")
        
        # WICHTIGE VERBESSERUNG: Stelle sicher, dass alle section IDs Strings sind
        try:
            if "sections" in template and isinstance(template["sections"], list):
                for i, section in enumerate(template["sections"]):
                    if "id" in section and not isinstance(section["id"], str):
                        original_id = section["id"]
                        section["id"] = str(original_id)
                        logger.warning(f"ID des Abschnitts {original_id} (Typ: {type(original_id).__name__}) in String umgewandelt bei Index {i}")
                        
                    # Stelle sicher, dass auch "type" ein String ist
                    if "type" in section and not isinstance(section["type"], str):
                        original_type = section["type"]
                        section["type"] = str(original_type)
                        logger.warning(f"Typ des Abschnitts {original_type} (Typ: {type(original_type).__name__}) in String umgewandelt bei Index {i}")
        except Exception as e:
            logger.error(f"Fehler beim Sicherstellen, dass Abschnitts-IDs Strings sind: {e}")
        
        return template

    def get_section_by_id(self, section_id: str) -> Optional[Dict[str, Any]]:
        """
        Gibt einen Abschnitt der Vorlage anhand seiner ID zurück.

        Args:
            section_id: ID des Abschnitts

        Returns:
            Abschnitt als Dictionary oder None, wenn nicht gefunden
        """
        for section in self.template["sections"]:
            if section["id"] == section_id:
                return section

        return None

    def get_next_section(self, completed_sections: List[str]) -> Optional[Dict[str, Any]]:
        """
        Gibt den nächsten Abschnitt zurück, der noch nicht abgeschlossen wurde.

        Args:
            completed_sections: Liste der bereits abgeschlossenen Abschnitte

        Returns:
            Nächster Abschnitt als Dictionary oder None, wenn alle abgeschlossen sind
        """
        for section in self.template["sections"]:
            if section["id"] not in completed_sections:
                return section

        return None

    def create_script_from_responses(self, section_responses: Dict[str, str], context_info: Dict[str, str]) -> Dict[str, Any]:
        """
        Erstellt ein Skript aus den gegebenen Antworten basierend auf den Beispielformaten.

        Args:
            section_responses: Dictionary mit Abschnitts-IDs als Schlüssel und Inhalten als Werte
            context_info: Dictionary mit Kontextinformationen

        Returns:
            Vollständiges Skript als Dictionary
        """
        script = copy.deepcopy(self.template)

        # Passe Titel und Beschreibung an
        organization = context_info.get("Für welche Art von Organisation erstellen wir den E-Learning-Kurs (z.B. Krankenhaus, Bank, Behörde)?", "")
        audience = context_info.get("Welche Mitarbeitergruppen sollen geschult werden?", "")

        # Formatiere den Titel, um den Beispielskripten zu entsprechen (kein doppeltes "Für")
        if organization.startswith("Für "):
            organization = organization[4:]  # Entferne das "Für "-Präfix, falls vorhanden
        
        script["title"] = f'Skript „Umgang mit Informationssicherheit für {organization}"'
        
        # Erstelle eine ansprechendere Beschreibung basierend auf der Zielgruppe
        if audience:
            script["description"] = f"Willkommen zum Trainingsmodul, in dem Sie lernen, wie {audience} in {organization} mit Informationssicherheit umgehen und typische Risiken im Klinikalltag erkennen und vermeiden können."
        else:
            script["description"] = f"Willkommen zum Trainingsmodul, in dem Sie lernen, wie Beschäftigte in {organization} mit Informationssicherheit umgehen."

        # Füge Inhalte zu den Abschnitten mit richtiger Formatierung hinzu
        for section in script["sections"]:
            section_id = section["id"]
            if section_id in section_responses:
                content = section_responses[section_id]
                
                # Wende abschnittsspezifische Formatierung und Bereinigung an
                content = self._format_section_content(content, section_id)
                section["content"] = content

        return script

    def _format_section_content(self, content: str, section_id: str) -> str:
        """
        Formatiert den Abschnittsinhalt, um dem Beispielformat zu entsprechen.
        
        Args:
            content: Roher Abschnittsinhalt
            section_id: Abschnitts-Kennung
            
        Returns:
            Formatierter Inhalt
        """
        if not isinstance(content, str):
            logger.warning(f"Inhalt für Abschnitt {section_id} ist kein String: {type(content)}")
            content = str(content) if content is not None else ""
        
        # Entferne potenzielle Markdown-Header, die vom LLM hinzugefügt wurden
        content = re.sub(r'^#+ .*$', '', content, flags=re.MULTILINE)
        
        # Bereinige übermäßige Zeilenumbrüche
        content = re.sub(r'\n{3,}', '\n\n', content)
        
        # Füge abschnittsspezifische Formatierung hinzu
        if section_id == "threat_awareness":
            # Stelle sicher, dass der Abschnitt mit einem Szenario beginnt
            if not re.search(r'^Ein neuer Arbeitstag|^Als Sie Ihren Arbeitstag|^Im klinischen Alltag', content, re.IGNORECASE):
                content = f"Ein typischer Arbeitstag im Krankenhaus beginnt und Sie müssen mit sensiblen Patientendaten umgehen.\n\n{content}"
        
        elif section_id == "threat_identification":
            # Stelle sicher, dass der Abschnitt Aufzählungspunkte für Identifikationskriterien enthält
            if "•" not in content and "-" not in content and not re.search(r'\d+\.\s', content) and not re.search(r'Schritt \d+', content, re.IGNORECASE):
                # Extrahiere potenzielle nummerierte Punkte und konvertiere sie in Aufzählungsformat
                bullet_points = re.findall(r'([A-Za-z].*?)(?=\n\n|\n[A-Za-z]|\Z)', content)
                if bullet_points and len(bullet_points) > 1:
                    formatted_bullets = "\n".join([f"• {point.strip()}" for point in bullet_points if point.strip()])
                    content = f"Folgende Hinweise deuten auf ein Informationssicherheitsrisiko hin:\n\n{formatted_bullets}"
        
        elif section_id == "threat_impact_assessment":
            # Stelle sicher, dass der Impact-Abschnitt nummerierte Konsequenzen enthält
            if "konsequenzen" not in content.lower() and "folgen" not in content.lower():
                content += "\n\nSolche Vorfälle würden für das Krankenhaus neben dem Verlust von Patientendaten auch einen erheblichen Reputationsverlust bedeuten."
            
            # Füge eine nummerierte Liste für Konsequenzen hinzu, falls nicht vorhanden
            if not re.search(r'\d+\.\s', content) and not re.search(r'•', content):
                impact_paragraphs = content.split("\n\n")
                if len(impact_paragraphs) > 1:
                    # Formatiere Konsequenzenliste
                    content = impact_paragraphs[0] + "\n\n"
                    content += "Die Konsequenzen können schwerwiegend sein:\n"
                    content += "1. Verlust oder Offenlegung sensibler Patientendaten\n"
                    content += "2. Unterbrechung kritischer medizinischer Systeme\n"
                    content += "3. Rechtliche Konsequenzen durch Verstöße gegen Datenschutzbestimmungen\n"
                    
                    # Füge verbleibenden Inhalt hinzu
                    if len(impact_paragraphs) > 2:
                        content += "\n" + "\n\n".join(impact_paragraphs[2:])
    
        elif section_id == "tactic_choice":
            # Stelle sicher, dass der Choice-Abschnitt klare Optionen präsentiert
            if "option" not in content.lower() and "maßnahme" not in content.lower() and "wahl" not in content.lower():
                content = f"Um sich bestmöglich zu schützen, sollten Sie folgende Maßnahmen ergreifen:\n\n{content}"
            
            # Füge Aufzählungspunkte für Optionen hinzu, falls nicht vorhanden
            if "•" not in content and "-" not in content and not re.search(r'\d+\.', content):
                options = re.split(r'\n\n+', content)
                if len(options) >= 2:
                    first_part = options[0]
                    rest = " ".join([opt.strip() for opt in options[1:]])
                    # Teile den Rest in Aufzählungspunkte nach Sätzen
                    sentences = re.split(r'(?<=[.!?])\s+', rest)
                    formatted_options = "\n".join([f"• {sentence.strip()}" for sentence in sentences if sentence.strip()])
                    content = f"{first_part}\n\n{formatted_options}"
        
        elif section_id == "tactic_mastery":
            # Stelle sicher, dass der Mastery-Abschnitt nummerierte Schritte enthält
            if not re.search(r'\d+\.\s', content) and not re.search(r'Schritt \d+', content, re.IGNORECASE):
                steps = re.split(r'\n\n+', content)
                if len(steps) >= 2:
                    # Behalte den ersten Absatz als Einleitung
                    intro = steps[0]
                    # Formatiere die restlichen Absätze als nummerierte Schritte
                    formatted_steps = "\n".join([f"{i+1}. {step.strip()}" for i, step in enumerate(steps[1:]) if step.strip()])
                    content = f"{intro}\n\n{formatted_steps}"
        
        elif section_id == "tactic_check_follow_up":
            # Stelle sicher, dass es eine klare Folgeanweisung gibt
            if "weitermelden" not in content.lower() and "benachrichtigen" not in content.lower() and "informieren" not in content.lower():
                content += "\n\nInformieren Sie immer Ihre IT-Sicherheitsabteilung über Vorfälle und halten Sie sich über aktuelle Entwicklungen im Bereich der Informationssicherheit auf dem Laufenden."
    
        # Füge einen "Nice to know"-Abschnitt hinzu, falls nicht vorhanden und angemessen
        if "nice to know" not in content.lower() and random.random() < 0.5:  # 50% Chance hinzuzufügen
            nice_to_know_tips = {
                "threat_awareness": "Nice to know: Phishing-Angriffe auf Krankenhäuser haben in den letzten Jahren um mehr als 300% zugenommen. Gerade im Gesundheitssektor sind die Daten besonders wertvoll.",
                "threat_identification": "Nice to know: Professionelle Phishing-Mails enthalten oft keine offensichtlichen Rechtschreibfehler mehr, dafür aber subtile Unstimmigkeiten in Logos oder Formulierungen.",
                "threat_impact_assessment": "Nice to know: Die durchschnittlichen Kosten eines Datenschutzvorfalls im Gesundheitswesen liegen bei über 7 Millionen Euro – höher als in jeder anderen Branche.",
                "tactic_choice": "Nice to know: Das \"Vier-Augen-Prinzip\" bei sensiblen Entscheidungen reduziert das Risiko erfolgreicher Social-Engineering-Angriffe um mehr als 70%.",
                "tactic_justification": "Nice to know: Studien zeigen, dass regelmäßige kurze Schulungen effektiver sind als seltene, längere Trainings.",
                "tactic_mastery": "Nice to know: Über 90% der Malware wird via E-Mail verbreitet. Die sorgfältige Prüfung jeder E-Mail ist daher der effektivste Schutz.",
                "tactic_check_follow_up": "Nice to know: Die gesetzliche Meldefrist für Datenschutzverletzungen beträgt nur 72 Stunden nach Bekanntwerden des Vorfalls."
            }
            
            if section_id in nice_to_know_tips:
                content += f"\n\n{nice_to_know_tips[section_id]}"
        
        return content