"""Writer agent implementation."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient


class WriterAgent(BaseAgent):
    """Produces final answer from research and analysis notes."""

    name = "writer"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.final_answer` with citations and references."""
        system_prompt = (
            f"You are a Principal Technical Writer. Your audience is: {state.request.audience}. "
            "Write an authoritative, crystal-clear, and well-structured research synthesis. "
            "Every major statement and claim must include an inline numbered citation like "
            "[1], [2] referencing the provided sources, and conclude with References."
        )

        sources_block = "\n".join(
            f"[{i+1}] {doc.title} ({doc.url or 'internal source'}): {doc.snippet}"
            for i, doc in enumerate(state.sources)
        )

        analysis_context = (
            state.analysis_notes or state.research_notes or "No prior analysis notes available."
        )

        user_prompt = (
            f"Original Query: {state.request.query}\n\n"
            f"Analysis Notes:\n{analysis_context}\n\n"
            f"Available Sources for Citation:\n{sources_block}\n\n"
            "Format your response as follows:\n"
            "- # Executive Summary & Title\n"
            "- ## Key Technical Findings (with inline citations [1], [2])\n"
            "- ## Architectural Trade-offs & Analysis\n"
            "- ## Actionable Recommendations\n"
            "- ## References (numbered matching inline citations)"
        )

        response = self.llm_client.complete(system_prompt, user_prompt)
        state.final_answer = response.content

        state.agent_results.append(
            AgentResult(
                agent=AgentName.WRITER,
                content=response.content,
                metadata={
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "cost_usd": response.cost_usd,
                },
            )
        )
        state.add_trace_event(
            "writer.done",
            {
                "input_tokens": response.input_tokens,
                "output_tokens": response.output_tokens,
                "cost_usd": response.cost_usd,
            },
        )
        return state
