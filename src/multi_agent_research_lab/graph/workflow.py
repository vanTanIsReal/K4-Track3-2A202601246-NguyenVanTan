"""LangGraph workflow implementation."""

import logging
from typing import Any

from langgraph.graph import END, StateGraph

from multi_agent_research_lab.agents import (
    AnalystAgent,
    CriticAgent,
    ResearcherAgent,
    SupervisorAgent,
    WriterAgent,
)
from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.state import ResearchState

logger = logging.getLogger(__name__)


class MultiAgentWorkflow:
    """Builds and runs the multi-agent graph with LangGraph."""

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()
        self.supervisor = SupervisorAgent(settings=self.settings)
        self.researcher = ResearcherAgent()
        self.analyst = AnalystAgent()
        self.writer = WriterAgent()
        self.critic = CriticAgent()
        self._compiled_graph: Any = None

    def build(self) -> Any:
        """Create and compile a LangGraph StateGraph."""
        builder = StateGraph(ResearchState)

        # 1. Define nodes
        def supervisor_node(state: ResearchState) -> ResearchState:
            return self.supervisor.run(state)

        def researcher_node(state: ResearchState) -> ResearchState:
            return self.researcher.run(state)

        def analyst_node(state: ResearchState) -> ResearchState:
            return self.analyst.run(state)

        def writer_node(state: ResearchState) -> ResearchState:
            return self.writer.run(state)

        def critic_node(state: ResearchState) -> ResearchState:
            return self.critic.run(state)

        builder.add_node("supervisor", supervisor_node)
        builder.add_node("researcher", researcher_node)
        builder.add_node("analyst", analyst_node)
        builder.add_node("writer", writer_node)
        builder.add_node("critic", critic_node)

        # 2. Define routing edge from supervisor
        def route_decision(state: ResearchState) -> str:
            if not state.route_history:
                return "done"
            decision = state.route_history[-1]
            if decision in ["researcher", "analyst", "writer", "critic"]:
                return decision
            return "done"

        builder.add_conditional_edges(
            "supervisor",
            route_decision,
            {
                "researcher": "researcher",
                "analyst": "analyst",
                "writer": "writer",
                "critic": "critic",
                "done": END,
            },
        )

        # 3. Connect worker nodes back to supervisor
        builder.add_edge("researcher", "supervisor")
        builder.add_edge("analyst", "supervisor")
        builder.add_edge("writer", "supervisor")
        builder.add_edge("critic", "supervisor")

        # 4. Set entry point
        builder.set_entry_point("supervisor")

        self._compiled_graph = builder.compile()
        return self._compiled_graph

    def run(self, state: ResearchState) -> ResearchState:
        """Execute the graph and return final state."""
        if self._compiled_graph is None:
            self.build()

        try:
            result = self._compiled_graph.invoke(state)
            if isinstance(result, ResearchState):
                return result
            if isinstance(result, dict):
                return ResearchState.model_validate(result)
        except Exception as exc:
            logger.warning(
                f"LangGraph execution exception: {exc}. Executing direct coordinator loop."
            )
            return self._run_direct_loop(state)

        return state

    def _run_direct_loop(self, state: ResearchState) -> ResearchState:
        """Direct coordination loop fallback ensuring 100% resilience."""
        workers = {
            "researcher": self.researcher,
            "analyst": self.analyst,
            "writer": self.writer,
            "critic": self.critic,
        }

        while True:
            state = self.supervisor.run(state)
            next_route = state.route_history[-1] if state.route_history else "done"
            if next_route == "done" or next_route not in workers:
                break
            state = workers[next_route].run(state)

        return state
