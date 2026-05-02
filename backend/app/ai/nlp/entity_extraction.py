"""
Entity extraction: identifies the primary country mentioned in a news snippet.
This is the missing link that lets news_pipeline set country_id on events,
which in turn drives country-level risk recalculation.

Optimized to run fully locally and deterministically, using a comprehensive
keyword-matching strategy with word-boundary checks and multi-word resolution.
No OpenAI API fallback is used.
"""

import logging
from typing import Optional, Tuple

logger = logging.getLogger("geotrade.nlp.entity_extraction")


class EntityExtractor:
    """
    Extracts the primary affected country from a news headline + summary.
    Returns (country_code, country_name) or (None, None).
    """

    # Multi-word country/demonym sequences to check first via substring matching
    MULTI_WORD_MAP = {
        "united states": ("US", "United States"),
        "united kingdom": ("GB", "United Kingdom"),
        "great britain": ("GB", "United Kingdom"),
        "saudi arabia": ("SA", "Saudi Arabia"),
        "north korea": ("KP", "North Korea"),
        "south korea": ("KR", "South Korea"),
        "cote d'ivoire": ("CI", "Cote d'Ivoire"),
        "ivory coast": ("CI", "Cote d'Ivoire"),
        "south africa": ("ZA", "South Africa"),
        "new zealand": ("NZ", "New Zealand"),
        "united arab emirates": ("AE", "United Arab Emirates"),
        "czech republic": ("CZ", "Czech Republic"),
        "sri lanka": ("LK", "Sri Lanka"),
        "el salvador": ("SV", "El Salvador"),
        "costa rica": ("CR", "Costa Rica"),
        "puerto rico": ("PR", "Puerto Rico"),
        "dominican republic": ("DO", "Dominican Republic"),
        "bosnia and herzegovina": ("BA", "Bosnia and Herzegovina"),
        "west bank": ("PS", "Palestine"),
    }

    # Single-word country names, demonyms, and abbreviations to match exactly as words
    SINGLE_WORD_MAP = {
        # Seeded/Important Countries in GeoTrade
        "usa": ("US", "United States"),
        "us": ("US", "United States"),
        "america": ("US", "United States"),
        "american": ("US", "United States"),
        "americans": ("US", "United States"),
        "china": ("CN", "China"),
        "chinese": ("CN", "China"),
        "taiwan": ("TW", "Taiwan"),
        "taiwanese": ("TW", "Taiwan"),
        "russia": ("RU", "Russia"),
        "russian": ("RU", "Russia"),
        "russians": ("RU", "Russia"),
        "ukraine": ("UA", "Ukraine"),
        "ukrainian": ("UA", "Ukraine"),
        "ukrainians": ("UA", "Ukraine"),
        "saudi": ("SA", "Saudi Arabia"),
        "saudis": ("SA", "Saudi Arabia"),
        "iran": ("IR", "Iran"),
        "iranian": ("IR", "Iran"),
        "iranians": ("IR", "Iran"),
        "israel": ("IL", "Israel"),
        "israeli": ("IL", "Israel"),
        "israelis": ("IL", "Israel"),
        
        # Other Geopolitically Significant Entities
        "palestine": ("PS", "Palestine"),
        "palestinian": ("PS", "Palestine"),
        "palestinians": ("PS", "Palestine"),
        "gaza": ("PS", "Palestine"),
        "india": ("IN", "India"),
        "indian": ("IN", "India"),
        "indians": ("IN", "India"),
        "pakistan": ("PK", "Pakistan"),
        "pakistani": ("PK", "Pakistan"),
        "pakistanis": ("PK", "Pakistan"),
        "turkey": ("TR", "Turkey"),
        "turkish": ("TR", "Turkey"),
        "turkiye": ("TR", "Turkey"),
        "germany": ("DE", "Germany"),
        "german": ("DE", "Germany"),
        "germans": ("DE", "Germany"),
        "france": ("FR", "France"),
        "french": ("FR", "France"),
        "britain": ("GB", "United Kingdom"),
        "british": ("GB", "United Kingdom"),
        "uk": ("GB", "United Kingdom"),
        "brazil": ("BR", "Brazil"),
        "brazilian": ("BR", "Brazil"),
        "brazilians": ("BR", "Brazil"),
        "venezuela": ("VE", "Venezuela"),
        "venezuelan": ("VE", "Venezuela"),
        "venezuelans": ("VE", "Venezuela"),
        "myanmar": ("MM", "Myanmar"),
        "burmese": ("MM", "Myanmar"),
        "ethiopia": ("ET", "Ethiopia"),
        "ethiopian": ("ET", "Ethiopia"),
        "ethiopians": ("ET", "Ethiopia"),
        "sudan": ("SD", "Sudan"),
        "sudanese": ("SD", "Sudan"),
        "afghanistan": ("AF", "Afghanistan"),
        "afghan": ("AF", "Afghanistan"),
        "afghans": ("AF", "Afghanistan"),
        "syria": ("SY", "Syria"),
        "syrian": ("SY", "Syria"),
        "syrians": ("SY", "Syria"),
        "iraq": ("IQ", "Iraq"),
        "iraqi": ("IQ", "Iraq"),
        "iraqis": ("IQ", "Iraq"),
        "japan": ("JP", "Japan"),
        "japanese": ("JP", "Japan"),
        "indonesia": ("ID", "Indonesia"),
        "indonesian": ("ID", "Indonesia"),
        "mexico": ("MX", "Mexico"),
        "mexican": ("MX", "Mexico"),
        "mexicans": ("MX", "Mexico"),
        "yemen": ("YE", "Yemen"),
        "yemeni": ("YE", "Yemen"),
        "yemenis": ("YE", "Yemen"),
        "lebanon": ("LB", "Lebanon"),
        "lebanese": ("LB", "Lebanon"),
        "egypt": ("EG", "Egypt"),
        "egyptian": ("EG", "Egypt"),
        "egyptians": ("EG", "Egypt"),
        "canada": ("CA", "Canada"),
        "canadian": ("CA", "Canada"),
        "canadians": ("CA", "Canada"),
        "italy": ("IT", "Italy"),
        "italian": ("IT", "Italy"),
        "spain": ("ES", "Spain"),
        "spanish": ("ES", "Spain"),
        "australia": ("AU", "Australia"),
        "australian": ("AU", "Australia"),
        "greece": ("GR", "Greece"),
        "greek": ("GR", "Greece"),
        "poland": ("PL", "Poland"),
        "polish": ("PL", "Poland"),
        "korea": ("KR", "South Korea"),
        "korean": ("KR", "South Korea"),
        "uae": ("AE", "United Arab Emirates"),
    }

    def __init__(self, api_key: Optional[str] = None):
        # api_key is accepted for backward compatibility, but ignored
        self.api_key = api_key

    def extract(self, text: str) -> list:
        """
        Legacy list-style interface for backward compatibility.
        Prefer extract_country() for new code.
        """
        code, name = self.extract_country("", text)
        if code:
            return [{"entity": name, "type": "GPE", "country_code": code}]
        return []

    def extract_country(
        self, title: str, summary: str
    ) -> Tuple[Optional[str], Optional[str]]:
        """
        Identifies the primary country affected by a news event.
        Returns (country_code, country_name) e.g. ("RU", "Russia") or (None, None).
        
        Matches are ordered by their first occurrence in the text (prioritizing title first).
        """
        # Preprocess and lowercase
        title_lower = title.lower() if title else ""
        summary_lower = summary.lower() if summary else ""
        
        # Standardize dotted abbreviations to simple tokens before punctuation removal
        for src, dest in [("u.s.a.", "usa"), ("u.s.", "usa"), ("u.k.", "uk"), ("u.a.e.", "uae")]:
            title_lower = title_lower.replace(src, dest)
            summary_lower = summary_lower.replace(src, dest)

        combined = f"{title_lower} {summary_lower}".strip()
        if not combined:
            return None, None

        # We will collect all matches and record their starting position to return the earliest match
        matches = []

        # 1. Multi-word phrase matching
        for phrase, (code, name) in self.MULTI_WORD_MAP.items():
            idx = combined.find(phrase)
            if idx != -1:
                matches.append((idx, code, name))

        # 2. Tokenized word matching (to prevent false positives like "us" in "status")
        # Clean punctuation to spaces to isolate words
        cleaned_combined = "".join(c if c.isalnum() else " " for c in combined)
        words_in_text = cleaned_combined.split()
        
        # Check each word
        for word in words_in_text:
            if word in self.SINGLE_WORD_MAP:
                code, name = self.SINGLE_WORD_MAP[word]
                # Find start index of this exact word in the cleaned text to approximate position
                # Since split() loses spacing, we find the word position
                idx = cleaned_combined.find(f" {word} ")
                if idx == -1:
                    if cleaned_combined.startswith(word):
                        idx = 0
                    elif cleaned_combined.endswith(word):
                        idx = len(cleaned_combined) - len(word)
                    else:
                        # general fallback search
                        idx = cleaned_combined.find(word)
                matches.append((idx, code, name))

        if not matches:
            return None, None

        # Return the match that occurs earliest in the combined string
        matches.sort(key=lambda x: x[0])
        earliest_match = matches[0]
        return earliest_match[1], earliest_match[2]
