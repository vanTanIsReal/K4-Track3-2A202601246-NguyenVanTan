"""Critic agent implementation."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.llm_client import LLMClient


class CriticAgent(BaseAgent):
    """Fact-checking, citation verification, and quality review agent."""

    name = "critic"

    def __init__(self, llm_client: LLMClient | None = None) -> None:
        self.llm_client = llm_client or LLMClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Validate final answer, verify citation integrity, and score quality."""
        if not state.final_answer:
            state.errors.append("CriticAgent: No final answer found to review.")
            return state

        sources_summary = "\n".join(
            f"[{i+1}] {doc.title}: {doc.snippet}" for i, doc in enumerate(state.sources)
        )

        system_prompt = (
            "You are a Quality & Verification Critic for AI Research reports. "
            "Review the drafted report against the retrieved sources. Check for:"
            "1. Grounding and absence of hallucinations."
            "2. Citation validity (are cited claims supported by sources?)."
            "3. Completeness, technical depth, and tone."
        )

        user_prompt = (
            f"Original Query: {state.request.query}\n\n"
            f"Draft Report:\n{state.final_answer}\n\n"
            f"Ground Truth Sources:\n{sources_summary}\n\n"
            "Provide a concise quality critique and validation score."
        )

        response = self.llm_client.complete(system_prompt, user_prompt)

        state.agent_results.append(
            AgentResult(
                agent=AgentName.CRITIC,
                content=response.content,
                metadata={
                    "input_tokens": response.input_tokens,
                    "output_tokens": response.output_tokens,
                    "cost_usd": response.cost_usd,
                },
            )
        )
        state.add_trace_event("critic.done", {"content_len": len(response.content)})
        return state
