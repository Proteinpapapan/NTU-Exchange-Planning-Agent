"""Assemble the LangGraph StateGraph."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from agents.au_agent import au_agent
from agents.currency_agent import currency_agent
from agents.decompose_agent import decompose_agent
from agents.intake_agent import intake_agent
from agents.mapping_agent import mapping_agent
from agents.reflect_agent import reflect_agent, route_after_reflect
from agents.render_agent import render_agent
from agents.research_agent import research_agent
from graph.orchestrator import build_profile_node, clarify_node, route_after_intake
from graph.state import ExchangeState


def build_graph():
    g = StateGraph(ExchangeState)
    g.add_node("intake", intake_agent)
    g.add_node("clarify", clarify_node)
    g.add_node("build_profile", build_profile_node)
    g.add_node("decompose", decompose_agent)
    g.add_node("mapping", mapping_agent)
    g.add_node("au", au_agent)
    g.add_node("currency", currency_agent)
    g.add_node("research", research_agent)
    g.add_node("reflect", reflect_agent)
    g.add_node("render", render_agent)

    g.add_edge(START, "intake")
    g.add_conditional_edges(
        "intake",
        route_after_intake,
        {"clarify": "clarify", "discover": "build_profile"},
    )
    g.add_edge("clarify", END)
    g.add_edge("build_profile", "decompose")
    g.add_edge("decompose", "mapping")
    g.add_edge("mapping", "au")
    g.add_edge("au", "currency")
    g.add_edge("currency", "research")
    g.add_edge("research", "reflect")
    g.add_conditional_edges(
        "reflect",
        route_after_reflect,
        {"mapping": "mapping", "render": "render"},
    )
    g.add_edge("render", END)
    return g.compile()


graph = build_graph()
