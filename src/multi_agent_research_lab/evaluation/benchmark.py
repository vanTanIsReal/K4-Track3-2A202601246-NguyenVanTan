"""Benchmark runner and evaluation metrics for single-agent vs multi-agent."""

from collections.abc import Callable
from time import perf_counter

from multi_agent_research_lab.core.schemas import BenchmarkMetrics
from multi_agent_research_lab.core.state import ResearchState

Runner = Callable[[str], ResearchState]


def compute_citation_coverage(state: ResearchState) -> float:
    """Calculate the ratio of retrieved sources referenced in the final answer."""
    if not state.sources or not state.final_answer:
        return 0.0

    answer_lower = state.final_answer.lower()
    cited_count = 0

    for idx, doc in enumerate(state.sources, start=1):
        idx_marker = f"[{idx}]"
        title_words = [w for w in doc.title.lower().split() if len(w) > 4]
        has_title_match = (
            any(word in answer_lower for word in title_words) if title_words else False
        )
        has_url_match = doc.url is not None and doc.url.lower() in answer_lower

        if idx_marker in state.final_answer or has_title_match or has_url_match:
            cited_count += 1

    return min(1.0, cited_count / len(state.sources))


def estimate_total_cost(state: ResearchState) -> float:
    """Sum up total estimated USD cost across all agent invocations."""
    total_cost = 0.0
    for res in state.agent_results:
        cost = res.metadata.get("cost_usd")
        if cost is not None and isinstance(cost, (int, float)):
            total_cost += cost
    return total_cost


def evaluate_quality_score(state: ResearchState) -> float:
    """Score output quality on a 0-10 scale based on depth, structure, and citations."""
    if not state.final_answer:
        return 0.0

    score = 5.0
    answer = state.final_answer

    # Structural bonus (markdown headers)
    if "#" in answer and "##" in answer:
        score += 1.5

    # Length and depth check
    if len(answer.split()) > 150:
        score += 1.5

    # Citation grounding bonus
    coverage = compute_citation_coverage(state)
    score += coverage * 2.0

    return min(10.0, round(score, 1))


def run_benchmark(
    run_name: str, query: str, runner: Runner
) -> tuple[ResearchState, BenchmarkMetrics]:
    """Execute a runner, measure latency, quality, cost, and citation metrics."""
    started = perf_counter()
    state = runner(query)
    latency = perf_counter() - started

    coverage = compute_citation_coverage(state)
    cost = estimate_total_cost(state)
    quality = evaluate_quality_score(state)
    failure_rate = 1.0 if (len(state.errors) > 0 or not state.final_answer) else 0.0

    notes = (
        f"Iterations: {state.iteration}, "
        f"Sources: {len(state.sources)}, "
        f"Agents: {len(state.agent_results)}"
    )

    metrics = BenchmarkMetrics(
        run_name=run_name,
        latency_seconds=latency,
        estimated_cost_usd=cost if cost > 0 else 0.0005,
        quality_score=quality,
        citation_coverage=coverage,
        failure_rate=failure_rate,
        notes=notes,
    )
    return state, metrics
