from typing import TypedDict, List, Dict, Any

class AgentState(TypedDict):
    user_id: str
    raw_preferences: str
    cleaned_preferences_json: Dict[str, Any]
    webtoon_universe_loaded: bool
    top_20_ids: List[str]  # List of Webtoon UUID strings
    feed_cycle_number: int
    all_skipped: bool
    expansion_count: int
    scrape_triggered: bool
    websocket_channel: str
    langsmith_run_id: str
