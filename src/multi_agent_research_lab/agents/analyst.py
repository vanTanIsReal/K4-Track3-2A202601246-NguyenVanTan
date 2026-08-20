"""Analyst agent implementation."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient


class AnalystAgent(BaseAgent):
    """Turns research notes into structured insights."""

    name = "analyst"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.analysis_notes` from raw sources and notes."""
        if not state.sources and not state.research_notes:
            state.errors.append("AnalystAgent: No sources or research notes available.")
            state.analysis_notes = "Insufficient evidence provided for detailed analysis."
            return state

        system_prompt = (
            "You are a Senior Technical Analyst. Your goal is to synthesize research materials "
            "into structured, comparative insights. Identify key claims, trade-offs, conflicting "
            "viewpoints, and evaluate the reliability of evidence."
        )

        sources_summary = state.research_notes or "\n".join(
            f"[{i+1}] {doc.title}: {doc.snippet}" for i, doc in enumerate(state.sources)
        )

        user_prompt = (
            f"Research Question: {state.request.query}\n\n"
            f"Retrieved Evidence:\n{sources_summary}\n\n"
            "Please provide a structured analysis outlining:\n"
            "1. Core findings and agreements among sources.\n"
            "2. Trade-offs, contrasts, and critical comparison.\n"
            "3. Evidence assessment and potential limitations."
        )

        response = self.llm_client.complete(system_prompt, user_prompt)
        state.analysis_notes = response.content

        state.agent_results.append(
            AgentResult(
                agent=AgentName.ANALYST,
                content=response.content,
                metadata={
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "cost_usd": response.cost_usd,
                },
            )
        )
        state.add_trace_event(
            "analyst.done",
            {
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "cost_usd": response.cost_usd,
            },
        )
        return state
