"""LangGraph agent: planner → (analyst → retriever → checker → responder) | conversational.

MemorySaver keeps each thread's last report, so a conversational turn ("what does the
second question mean?") is answered from it without a new assessment.
"""

from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, StateGraph

from app.agents.nodes.analyst import analyst_node
from app.agents.nodes.checker import checker_node
from app.agents.nodes.planner import planner_node
from app.agents.nodes.responder import conversational_node, responder_node
from app.agents.nodes.retriever import retriever_node
from app.agents.state import AgentState

workflow = StateGraph(AgentState)
workflow.add_node("planner", planner_node)
workflow.add_node("analyst", analyst_node)
workflow.add_node("retriever", retriever_node)
workflow.add_node("checker", checker_node)
workflow.add_node("responder", responder_node)
workflow.add_node("conversational", conversational_node)

workflow.set_entry_point("planner")
workflow.add_conditional_edges(
    "planner",
    lambda s: "conversational" if s.get("intent") == "conversational" and s.get("report") else "analyst",
    {"conversational": "conversational", "analyst": "analyst"},
)
workflow.add_edge("analyst", "retriever")
workflow.add_edge("retriever", "checker")
workflow.add_edge("checker", "responder")
workflow.add_edge("responder", END)
workflow.add_edge("conversational", END)

checkpointer = MemorySaver()
agent = workflow.compile(checkpointer=checkpointer)
