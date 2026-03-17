from typing import Dict, List, TypedDict


class EvidenceItem(TypedDict, total=False):
    title: str
    snippet: str
    url: str
    text: str
    source_type: str
    source_name: str
    tier: str

class FactCheckState(TypedDict):
    input_text: str
    claims: List[str]
    checkworthy_claims: List[str]
    queries: Dict[str, List[str]]
    evidence: Dict[str, List[EvidenceItem]]
    verdicts: Dict[str, Dict]
    overall_verdict: Dict[str, object]
    retry_count: int
    prompt_tokens: int      
    completion_tokens: int  