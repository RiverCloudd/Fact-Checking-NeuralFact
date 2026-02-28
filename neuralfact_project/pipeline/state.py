from typing import Dict, List, TypedDict

class FactCheckState(TypedDict):
    input_text: str
    claims: List[str]
    checkworthy_claims: List[str]
    queries: Dict[str, str]
    evidence: Dict[str, str]
    verdicts: Dict[str, Dict]
    retry_count: int
    prompt_tokens: int      
    completion_tokens: int  