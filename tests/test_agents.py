"""Comprehensive unit tests for agents and multi-agent workflow."""

from multi_agent_research_lab.agents import (
    AnalystAgent,
    CriticAgent,
    ResearcherAgent,
    SupervisorAgent,
    WriterAgent,
)
from multi_agent_research_lab.core.schemas import AgentName, ResearchQuery, SourceDocument
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow


def test_supervisor_routing_cycle() -> None:
    supervisor = SupervisorAgent()
    state = ResearchState(request=ResearchQuery(query="Test multi-agent systems"))

    # Initial state -> Researcher
    assert supervisor.get_next_route(state) == "researcher"
    state = supervisor.run(state)
    assert state.route_history[-1] == "researcher"

    # Has sources -> Analyst
    state.sources = [SourceDocument(title="Doc 1", snippet="Snippet 1")]
    assert supervisor.get_next_route(state) == "analyst"
    state = supervisor.run(state)
    assert state.route_history[-1] == "analyst"

    # Has analysis -> Writer
    state.analysis_notes = "Analysis notes ready"
    assert supervisor.get_next_route(state) == "writer"
    state = supervisor.run(state)
    assert state.route_history[-1] == "writer"

    # Has final answer -> Critic
    state.final_answer = "Draft final answer with citations [1]"
    assert supervisor.get_next_route(state) == "critic"

    # Has critic done -> Done
    state = CriticAgent().run(state)
    assert supervisor.get_next_route(state) == "done"


def test_researcher_agent() -> None:
    agent = ResearcherAgent()
    state = ResearchState(request=ResearchQuery(query="GraphRAG architectures", max_sources=2))
    state = agent.run(state)

    assert len(state.sources) > 0
    assert state.research_notes is not None
    assert any(res.agent == AgentName.RESEARCHER for res in state.agent_results)


def test_analyst_agent() -> None:
    agent = AnalystAgent()
    state = ResearchState(request=ResearchQuery(query="GraphRAG architectures"))
    state.sources = [
        SourceDocument(
            title="GraphRAG Paper",
            snippet="GraphRAG combines knowledge graphs and vector search.",
        )
    ]
    state = agent.run(state)

    assert state.analysis_notes is not None
    assert any(res.agent == AgentName.ANALYST for res in state.agent_results)


def test_writer_agent() -> None:
    agent = WriterAgent()
    state = ResearchState(request=ResearchQuery(query="GraphRAG architectures"))
    state.sources = [
        SourceDocument(
            title="GraphRAG Paper",
            url="https://example.com/graphrag",
            snippet="Knowledge graphs.",
        )
    ]
    state.analysis_notes = "GraphRAG is scalable and provides structural reasoning."
    state = agent.run(state)

    assert state.final_answer is not None
    assert any(res.agent == AgentName.WRITER for res in state.agent_results)


def test_critic_agent() -> None:
    agent = CriticAgent()
    state = ResearchState(request=ResearchQuery(query="GraphRAG architectures"))
    state.final_answer = "Summary report with references."
    state = agent.run(state)

    assert any(res.agent == AgentName.CRITIC for res in state.agent_results)


def test_multi_agent_workflow_end_to_end() -> None:
    workflow = MultiAgentWorkflow()
    state = ResearchState(
        request=ResearchQuery(query="Explain GraphRAG architectures", max_sources=3)
    )
    result = workflow.run(state)

    assert result.final_answer is not None
    assert len(result.sources) > 0
    assert result.analysis_notes is not None
    assert len(result.route_history) >= 4
