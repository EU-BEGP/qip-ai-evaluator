import re
from typing import List, Dict, Any, Tuple, Optional
from rapidfuzz import process, fuzz

class MetadataAnalyzer:
    """
    Analyzes Markdown documents:
    - SECTIONS: Found strictly via Headers (## Title). Content validation happens here
    - METRICS: Found via Regex anywhere in the text (ELH, EQF, BTL, SMCTS)
    - VALIDATION: Checks mathematical consistency for SMCTS (ECTS) and the presence of subtitles and necessary elements
    """

    def __init__(self):
        # 1. SECTION HEADERS
        self.SECTION_SYNONYMS = {
            "Teachers": [
                "teachers", "authors", "instructors", "contact", "team", "lecturer", "faculty",
                "profesores", "docentes", "autores", "instructores", "contacto", "equipo",
                "lärare", "författare", "instruktörer", "kontakt", "kursansvarig",
                "enseignants", "auteurs", "équipe", "dozenten", "professores"
            ],
            "Keywords": [
                "keywords", "tags", "key concepts", "topics",
                "palabras clave", "etiquetas", "conceptos clave", "temas",
                "nyckelord", "taggar", "nyckelbegrepp", "ämnen",
                "mots-clés", "schlüsselwörter", "palavras-chave"
            ],
            "Estimated Learning Hours": [
                "estimated learning hours", "duration", "workload", "time", "expected learning hours", "effort", "hours", "study time",
                "horas estimadas", "duración", "carga de trabajo", "tiempo", "horas", "esfuerzo",
                "beräknad studietid", "tid", "arbetsinsats", "omfattning", "timmar", "varaktighet",
                "durée", "charge de trabajo", "dauer", "arbeitsaufwand", "carga horária"
            ],
            "Intended Learning Outcomes": [
                "intended learning outcomes", "learning outcomes", "objectives", "ilos", "learning objectives", "competencies", "goals", "aims", "outcomes",
                "resultados de aprendizaje", "objetivos", "competencias", "metas",
                "lärandemål", "mål", "syfte", "kompetenser", "kursmål",
                "acquis d'apprentissage", "lernziele", "resultados de aprendizagem"
            ]
        }

        # 2. ILO Subsections
        self.ILO_SUBSECTIONS = {
            "Knowledge": ["knowledge", "conocimiento", "kunskap", "savoir", "wissen", "conhecimento"],
            "Skills": ["skills", "habilidades", "färdigheter", "aptitudes", "fertigkeiten"],
            "Responsibility": ["responsibility", "autonomy", "responsabilidad", "autonomía", "ansvar", "autonomi", "responsabilité", "verantwortung"]
        }

        # 3. GLOBAL METRICS
        self.METRICS_REGEX_STRICT = {
            "ELH": r"(?i)(?:ELH|Hours|Horas|Timmar|Heures|Stunden|Workload|Duration|Expected|Estimated).*?[:=]\s*([\d\.]+(?:\s*(?:h|hours|horas|timmar|heures|stunden))?)",
            "EQF": r"(?i)(?:EQF|European|Nivel|Level|Nivå|Niveau|Stufe|Certificate|Study\s+Level).*?[:=]?\s*(\d+)",
            "BTL": r"(?i)(?:BTL|Bloom).*?[:=]?\s*(\d+)",
            "SMCTS": r"(?i)(?:SMCTS|Credits|Créditos|Poäng|Crédits|Credits).*?[:=]\s*([\d\.]+)"
        }

        self.METRICS_REGEX_LOOSE = {
            "EQF": r"(?i)(?:EQF|European|Nivel|Level|Nivå|Niveau|Stufe|Certificate|Study\s+Level)",
            "BTL": r"(?i)(?:BTL|Bloom)",
            "SMCTS": r"(?i)(?:SMCTS|Credits|Créditos|Poäng|Crédits|Credits)"
        }

    def _parse_sections_from_markdown(self, text: str) -> Dict[str, str]:
        parts = re.split(r'(?m)^##\s+(.+)$', text)
        sections = {}
        if parts:
            sections["HEADER_INTRO"] = parts[0].strip()
        for i in range(1, len(parts), 2):
            sections[parts[i].strip()] = parts[i+1].strip() if i+1 < len(parts) else ""
        return sections

    def _find_section_header(self, target_key: str, parsed_sections: Dict[str, str]) -> Tuple[str, str]:
        synonyms = self.SECTION_SYNONYMS.get(target_key, [])
        headers = list(parsed_sections.keys())
        best_header = None
        best_score = 0

        for header in headers:
            if header == "HEADER_INTRO": continue
            match = process.extractOne(header.lower(), synonyms, scorer=fuzz.token_set_ratio)
            if match and match[1] > 85 and match[1] > best_score:
                best_score = match[1]
                best_header = header

        if best_header:
            return best_header, parsed_sections[best_header]
        return None, None

    def _check_ilo_content(self, text: str) -> List[str]:
        missing = []
        lower_text = text.lower()
        for cat, keywords in self.ILO_SUBSECTIONS.items():
            if not any(k in lower_text for k in keywords):
                missing.append(cat)
        return missing

    def _extract_float(self, text: str) -> Optional[float]:
        try:
            match = re.search(r"([\d\.]+)", str(text))
            if match:
                return float(match.group(1))
        except (ValueError, TypeError):
            return None
        return None

    def _create_result(self, status: str, title: str, description: str, content: Optional[str] = None) -> Dict[str, str]:
        res = {
            "status": status,
            "title": title,
            "description": description
        }
        if content is not None:
            res["content"] = str(content).strip()
        return res

    def analyze(self, documents: List[Any]) -> List[Dict[str, str]]:
        if not documents:
            return [self._create_result("MISSING", "Global", "No documents provided.")]

        # 1. Context
        context_text = "".join(doc.page_content + "\n" for doc in documents[:3])

        # 2. Parse
        parsed_sections = self._parse_sections_from_markdown(context_text)
        found_headers = set()
        results = []

        # TEACHERS 
        t_header, t_content = self._find_section_header("Teachers", parsed_sections)
        if t_header:
            found_headers.add(t_header)
            emails = re.findall(r'[\w\.-]+@[\w\.-]+\.\w+', t_content)
            if not emails:
                results.append(self._create_result("CRITICAL", "Teachers", "Section found, but no email address was detected."))
            else:
                results.append(self._create_result("GOOD", "Teachers", f"Teachers identified ({len(emails)} emails found)."))
        else:
            results.append(self._create_result("MISSING", "Teachers", "Teachers section is missing."))

        # KEYWORDS 
        k_header, k_content = self._find_section_header("Keywords", parsed_sections)
        if k_header:
            found_headers.add(k_header)
            if k_content:
                results.append(self._create_result("GOOD", "Keywords", "Keywords section is present.", content=k_content))
            else:
                results.append(self._create_result("MISSING", "Keywords", "Keywords section exists but is empty."))
        else:
            results.append(self._create_result("MISSING", "Keywords", "Keywords section is missing."))

        # ILOs 
        ilo_header, ilo_content = self._find_section_header("Intended Learning Outcomes", parsed_sections)
        if ilo_header:
            found_headers.add(ilo_header)
            if not ilo_content:
                results.append(self._create_result("MISSING", "Intended Learning Outcomes", "Section exists but is empty."))
            else:
                missing_subs = self._check_ilo_content(ilo_content)
                if missing_subs:
                    results.append(self._create_result("CRITICAL", "Intended Learning Outcomes", f"Missing subsections: {', '.join(missing_subs)}."))
                else:
                    results.append(self._create_result("GOOD", "Intended Learning Outcomes", "Complete (Knowledge, Skills, Responsibility)."))
        else:
            results.append(self._create_result("MISSING", "Intended Learning Outcomes", "Intended Learning Outcomes section is missing."))

        detected_elh_value = None

        # ELH 
        elh_regex_match = re.search(self.METRICS_REGEX_STRICT["ELH"], context_text)
        if elh_regex_match:
            val_str = elh_regex_match.group(1)
            detected_elh_value = self._extract_float(val_str)
            results.append(self._create_result("GOOD", "Estimated Learning Hours", f"Workload found: {val_str}", content=val_str))
        else:
            elh_header, elh_content = self._find_section_header("Estimated Learning Hours", parsed_sections)
            if elh_header:
                found_headers.add(elh_header)
                detected_elh_value = self._extract_float(elh_content)
                results.append(self._create_result("CRITICAL", "Estimated Learning Hours", "Section exists, but numeric value is unclear.", content=elh_content))
            else:
                results.append(self._create_result("MISSING", "Estimated Learning Hours", "Estimated Learning Hours are missing."))

        #  OTHER METRICS (EQF, BTL, SMCTS) 
        for metric in ["EQF", "BTL", "SMCTS"]:

            strict_match = re.search(self.METRICS_REGEX_STRICT[metric], context_text)

            if strict_match:
                val_str = strict_match.group(1)

                # SMCTS validation
                if metric == "SMCTS" and detected_elh_value:
                    smcts_val = self._extract_float(val_str)
                    if smcts_val is not None:
                        expected_smcts = round(detected_elh_value / 27.5, 2)
                        if round(smcts_val, 2) > expected_smcts:
                             results.append(self._create_result(
                                 "CRITICAL",
                                 "SMCTS",
                                 f"The formula is ELH/27.5, rounded to two decimals. You entered {smcts_val} but maximum expected is {expected_smcts}!",
                                 content=val_str
                             ))
                             continue
                        else:
                             pass

                results.append(self._create_result("GOOD", metric, f"Found: {val_str}", content=val_str))
                continue

            loose_match = re.search(self.METRICS_REGEX_LOOSE[metric], context_text)
            if loose_match:
                results.append(self._create_result("CRITICAL", metric, f"{metric} label found, but value is missing."))
            else:
                results.append(self._create_result("MISSING", metric, f"{metric} is missing."))

        # EXTRA SECTIONS 
        for header, content in parsed_sections.items():
            if header == "HEADER_INTRO" or header in found_headers: continue

            if content:
                results.append(self._create_result("GOOD", header.title(), "Additional section detected."))
            else:
                results.append(self._create_result("MISSING", header.title(), "Section header exists but content is empty."))

        return results
