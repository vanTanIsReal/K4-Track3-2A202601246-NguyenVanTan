"""Supervisor / router implementation."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.config import Settings, get_settings
from multi_agent_research_lab.core.schemas import AgentName
from multi_agent_research_lab.core.state import ResearchState


class SupervisorAgent(BaseAgent):
    """Decides which worker should run next and when to stop."""

    name = "supervisor"

    def __init__(self, settings: Settings | None = None) -> None:
        self.settings = settings or get_settings()

    def get_next_route(self, state: ResearchState) -> str:
        """Evaluate the current state and return the next agent name or 'done'."""
        # 1. Guardrail against infinite loops
        if state.iteration >= self.settings.max_iterations:
            return "done"

        # 2. Check for missing stages in order:
        # Step A: Collect sources
        if not state.sources:
            return "researcher"

        # Step B: Synthesize analytical insights from sources
        if not state.analysis_notes:
            return "analyst"

        # Step C: Draft the final answer with citations
        if not state.final_answer:
            return "writer"

        # Step D: Critic review (optional safety check / verification)
        has_critic = any(res.agent == AgentName.CRITIC for res in state.agent_results)
        if not has_critic:
            return "critic"

        # Step E: All phases complete
        return "done"

    def run(self, state: ResearchState) -> ResearchState:
        """Update `state.route_history` with the next route and record trace."""
        next_route = self.get_next_route(state)
        state.record_route(next_route)
        state.add_trace_event(
            "supervisor.decision",
            {
                "next_route": next_route,
                "iteration": state.iteration,
                "has_sources": bool(state.sources),
                "has_analysis": bool(state.analysis_notes),
                "has_final_answer": bool(state.final_answer),
            },
        )
        return state
