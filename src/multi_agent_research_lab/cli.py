"""Command-line entrypoint for the lab."""

import sys
from typing import Annotated

import typer
from pydantic import ValidationError
from rich.console import Console
from rich.markdown import Markdown
from rich.panel import Panel
from rich.table import Table

from multi_agent_research_lab.core.config import get_settings
from multi_agent_research_lab.core.schemas import ResearchQuery
from multi_agent_research_lab.core.state import ResearchState
from multi_agent_research_lab.evaluation.benchmark import run_benchmark
from multi_agent_research_lab.evaluation.report import render_markdown_report
from multi_agent_research_lab.graph.workflow import MultiAgentWorkflow
from multi_agent_research_lab.observability.logging import configure_logging
from multi_agent_research_lab.services.llm_client import LLMClient
from multi_agent_research_lab.services.storage import LocalArtifactStore

# Configure safe UTF-8 output on Windows
if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

app = typer.Typer(help="Multi-Agent Research Lab CLI")
console = Console(highlight=False)


def _init() -> None:
    settings = get_settings()
    configure_logging(settings.log_level)


def _parse_query(query: str) -> ResearchQuery:
    try:
        return ResearchQuery(query=query)
    except ValidationError as exc:
        console.print(
            Panel.fit(
                f"Invalid query: {exc.errors()[0]['msg']}",
                title="Input Error",
                style="red",
            )
        )
        raise typer.Exit(code=1) from exc


def _run_single_agent(query_str: str) -> ResearchState:
    """Execute single-agent baseline."""
    request = _parse_query(query_str)
    state = ResearchState(request=request)
    llm = LLMClient()
    response = llm.complete(
        system_prompt=(
            "You are a helpful research assistant. "
            "Answer the user query comprehensively in clear markdown."
        ),
        user_prompt=request.query,
    )
    state.final_answer = response.content
    state.iteration = 1
    state.record_route("single_agent")
    return state


def _run_multi_agent(query_str: str) -> ResearchState:
    """Execute multi-agent workflow."""
    request = _parse_query(query_str)
    state = ResearchState(request=request)
    workflow = MultiAgentWorkflow()
    return workflow.run(state)


@app.command()
def baseline(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run a single-agent baseline completion."""
    _init()
    with console.status("[bold green]Executing single-agent baseline..."):
        state = _run_single_agent(query)

    console.print(
        Panel(
            Markdown(state.final_answer or "No answer generated."),
            title="Single-Agent Baseline Response",
            border_style="green",
        )
    )


@app.command("multi-agent")
def multi_agent(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run the complete multi-agent LangGraph workflow."""
    _init()
    console.print(f"[bold cyan]Starting Multi-Agent Research System for:[/bold cyan] {query}\n")

    with console.status("[bold blue]Executing multi-agent workflow..."):
        result = _run_multi_agent(query)

    # 1. Execution trace table
    table = Table(title="Workflow Execution Summary", border_style="cyan")
    table.add_column("Step", justify="center")
    table.add_column("Agent Route", style="magenta")
    table.add_column("Key Output", style="green")

    for idx, route in enumerate(result.route_history, start=1):
        summary = "Completed"
        if route == "researcher":
            summary = f"Retrieved {len(result.sources)} sources"
        elif route == "analyst":
            summary = "Generated analytical insights"
        elif route == "writer":
            summary = "Composed final synthesis"
        elif route == "critic":
            summary = "Verified claims and citation coverage"
        table.add_row(str(idx), route, summary)

    console.print(table)
    console.print("\n")

    # 2. Final Answer Panel
    console.print(
        Panel(
            Markdown(result.final_answer or "No final answer generated."),
            title="Final Multi-Agent Research Synthesis",
            border_style="blue",
        )
    )


@app.command("benchmark")
def benchmark(
    query: Annotated[str, typer.Option("--query", "-q", help="Research query")],
) -> None:
    """Run benchmark comparing Single-Agent vs Multi-Agent and export report."""
    _init()
    console.print(f"[bold yellow]Running Benchmark Suite for query:[/bold yellow] {query}\n")

    metrics_list = []

    # Run Baseline
    with console.status("[bold green]Benchmarking Single-Agent Baseline..."):
        _, base_metrics = run_benchmark("Single-Agent Baseline", query, _run_single_agent)
        metrics_list.append(base_metrics)

    # Run Multi-Agent
    with console.status("[bold blue]Benchmarking Multi-Agent System..."):
        _, multi_metrics = run_benchmark("Multi-Agent Workflow", query, _run_multi_agent)
        metrics_list.append(multi_metrics)

    # Render report
    report_md = render_markdown_report(metrics_list)
    store = LocalArtifactStore()
    report_path = store.write_text("benchmark_report.md", report_md)

    console.print(Markdown(report_md))
    console.print(f"\n[bold green]Benchmark report saved to:[/bold green] {report_path}")


if __name__ == "__main__":
    app()
