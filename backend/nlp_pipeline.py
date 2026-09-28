"""
nlp_pipeline.py
NLP Ingestion Engine for AtmoGraph.

Takes raw news text (from a feed/scraper), extracts organizations,
locations, and disruption-type events (strike, closure, shortage, delay),
then maps extracted entities onto existing graph node IDs so their
risk_score can be updated.
"""

import spacy
from dataclasses import dataclass
from typing import List, Optional

# Keywords that signal a supply-chain disruption event.
DISRUPTION_KEYWORDS = {
    "strike": 0.8,
    "closure": 0.75,
    "shutdown": 0.75,
    "shortage": 0.6,
    "delay": 0.5,
    "flood": 0.7,
    "earthquake": 0.9,
    "tariff": 0.55,
    "blockade": 0.85,
}


@dataclass
class DisruptionEvent:
    text: str
    organizations: List[str]
    locations: List[str]
    severity: float
    keyword: Optional[str]


class NLPIngestionEngine:
    def __init__(self, model_name: str = "en_core_web_sm"):
        # For production, swap in a HuggingFace NER pipeline fine-tuned on
        # logistics/news text (e.g. dslim/bert-base-NER or a custom model).
        self.nlp = spacy.load(model_name)

    def extract_entities(self, text: str) -> DisruptionEvent:
        doc = self.nlp(text)
        orgs = [ent.text for ent in doc.ents if ent.label_ in ("ORG", "FAC")]
        locs = [ent.text for ent in doc.ents if ent.label_ in ("GPE", "LOC")]

        lowered = text.lower()
        matched_keyword, severity = None, 0.0
        for kw, score in DISRUPTION_KEYWORDS.items():
            if kw in lowered:
                matched_keyword, severity = kw, score
                break

        return DisruptionEvent(
            text=text,
            organizations=orgs,
            locations=locs,
            severity=severity,
            keyword=matched_keyword,
        )

    def map_to_node_ids(self, event: DisruptionEvent, entity_lookup: dict) -> List[str]:
        """
        entity_lookup maps lowercase entity names -> graph node ids, built
        from the Neo4j node list (name -> id). Real implementation should
        use fuzzy matching (e.g. rapidfuzz) since news text rarely matches
        canonical node names exactly.
        """
        matched_ids = []
        for name in event.organizations + event.locations:
            node_id = entity_lookup.get(name.lower())
            if node_id:
                matched_ids.append(node_id)
        return matched_ids


if __name__ == "__main__":
    engine = NLPIngestionEngine()
    sample = "Dockworkers begin an indefinite strike at the Port of Rotterdam, halting shipments."
    event = engine.extract_entities(sample)
    print(event)
