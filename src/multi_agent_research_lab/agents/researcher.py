"""Researcher agent implementation."""

from multi_agent_research_lab.agents.base import BaseAgent
from multi_agent_research_lab.core.schemas import AgentName, AgentResult
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.services.search_client import SearchClient


class ResearcherAgent(BaseAgent):
    """Collects sources and creates concise research notes."""

    name = "researcher"

    def __init__(self, search_client: SearchClient | None = None) -> None:
        self.search_client = search_client or SearchClient()

    def run(self, state: ResearchState) -> ResearchState:
        """Populate `state.sources` and `state.research_notes`."""
        docs = self.search_client.search(
            query=state.request.query,
            max_results=state.request.max_sources,
        )
        state.sources = docs

        notes_lines: list[str] = [
            f"# Research Notes for Query: {state.request.query}",
            f"Total Sources Retrieved: {len(docs)}\n",
        ]
        for i, doc in enumerate(docs, start=1):
            notes_lines.append(f"[{i}] **{doc.title}**")
            if doc.url:
                notes_lines.append(f"    URL: {doc.url}")
            notes_lines.append(f"    Summary: {doc.snippet}\n")

        state.research_notes = "\n".join(notes_lines)

        state.agent_results.append(
            AgentResult(
                agent=AgentName.RESEARCHER,
                content=state.research_notes,
                metadata={"num_sources": len(docs)},
            )
        )
        state.add_trace_event("researcher.done", {"num_sources": len(docs)})
        return state
