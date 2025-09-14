from .node import identify_node, check_node, publish_node, concat_node
from langgraph.graph import StateGraph, END
from typing import TypedDict, List

class GraphState(TypedDict):
    stream_url: str
    GEMINI_API_KEY: str
    analyzer_id: int                
    expected_fields: List[str]
    video_data: str
    report: dict
    accumulator: List[dict]
    minute_index: int
    
graph = StateGraph(GraphState)

graph.add_node("identify", identify_node)
graph.add_node("check", check_node)
graph.add_node("publish", publish_node)
graph.add_node("concat", concat_node)

graph.set_entry_point("identify")
graph.add_edge("identify", "check")
graph.add_edge("check", "publish")
graph.add_edge("publish", "concat")
graph.add_edge("concat", END)

langgraph = graph.compile()
