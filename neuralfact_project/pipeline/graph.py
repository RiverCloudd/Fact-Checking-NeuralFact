from langgraph.graph import StateGraph, END
from pipeline.state import FactCheckState
from pipeline.nodes import (
    decompose_node, checkworthy_node, query_gen_node, retrieve_node, verify_node
)

def should_retry(state: FactCheckState):
    """Logic tự sửa lỗi (Self-Correction)"""
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
workflow.add_node("query_gen", query_gen_node)
workflow.add_node("retrieve", retrieve_node)
workflow.add_node("verify", verify_node)

# Add Edges (Luồng xử lý chính)
workflow.set_entry_point("decompose")
workflow.add_edge("decompose", "checkworthy")
workflow.add_edge("checkworthy", "query_gen")
workflow.add_edge("query_gen", "retrieve")

# Điều hướng có điều kiện
workflow.add_conditional_edges(
    "retrieve",
    should_retry,
    {
        "retry": "query_gen",
        "continue": "verify"
    }
)
workflow.add_edge("verify", END)

# show the graph structure (optional)
# workflow.visualize()

# Đóng gói Agent
factcheck_app = workflow.compile()
