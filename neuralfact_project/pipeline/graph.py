from langgraph.graph import StateGraph, END
import os
from pipeline.state import FactCheckState
from pipeline.nodes import (
    decompose_node, checkworthy_node, retrieve_node, verify_node
    decompose_node, checkworthy_node, retrieve_node, verify_node
)


def should_retry(state: FactCheckState):
    """Logic tự sửa lỗi (Self-Correction)"""
    retry_enabled = os.getenv("RETRIEVE_RETRY_ENABLED", "false").strip().lower() in {"1", "true", "yes"}
    if not retry_enabled:
        return "continue"

    all_empty = all(not ev for ev in state["evidence"].values())
    if all_empty and state["retry_count"] < 1:
        state["retry_count"] += 1
        return "retry"
    return "continue"

# Khởi tạo Graph
workflow = StateGraph(FactCheckState)

# Add Nodes
workflow.add_node("decompose", decompose_node)
workflow.add_node("checkworthy", checkworthy_node)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("verify", verify_node)

# Add Edges (Luồng xử lý chính)
workflow.set_entry_point("decompose")
workflow.add_edge("decompose", "checkworthy")
workflow.add_edge("checkworthy", "retrieve")
workflow.add_edge("checkworthy", "retrieve")

workflow.add_conditional_edges(
    "retrieve",
    should_retry,
    {
        "retry": "retrieve",
        "retry": "retrieve",
        "continue": "verify"
    }
)

workflow.add_edge("verify", END)

# show the graph structure (optional)
# workflow.visualize()

# Đóng gói Agent
factcheck_app = workflow.compile()
