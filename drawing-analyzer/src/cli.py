#!/usr/bin/env python3
"""
Drawing Analyzer CLI

Command-line interface for analyzing technical drawings.
"""
import json
import sys
from pathlib import Path
from typing import Optional

import click
from rich.console import Console
from rich.table import Table
from rich.progress import Progress, SpinnerColumn, TextColumn
from rich.panel import Panel

console = Console()


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """Drawing Analyzer - AI-powered technical drawing analysis"""
    pass


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--provider",
    "-p",
    type=click.Choice(["openai", "anthropic"]),
    default="openai",
    help="API provider to use",
)
@click.option("--api-key", "-k", envvar="API_KEY", help="API key (or use env var)")
@click.option("--model", "-m", help="Model to use")
@click.option("--page", type=int, help="Specific page to analyze")
@click.option(
    "--output",
    "-o",
    type=click.Path(path_type=Path),
    help="Output file path",
)
@click.option(
    "--format",
    "-f",
    "output_format",
    type=click.Choice(["json", "table", "csv"]),
    default="json",
    help="Output format",
)
@click.option("--verbose", "-v", is_flag=True, help="Verbose output")
def analyze(
    pdf_path: Path,
    provider: str,
    api_key: Optional[str],
    model: Optional[str],
    page: Optional[int],
    output: Optional[Path],
    output_format: str,
    verbose: bool,
):
    """Analyze a technical drawing PDF"""
    from .analyzer import create_analyzer

    console.print(Panel.fit(
        f"[bold blue]Drawing Analyzer[/bold blue]\n"
        f"File: {pdf_path.name}\n"
        f"Provider: {provider}",
        title="Starting Analysis",
    ))

    try:
        # Create analyzer
        with Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            console=console,
        ) as progress:
            task = progress.add_task("Initializing analyzer...", total=None)

            analyzer = create_analyzer(
                provider=provider,
                api_key=api_key,
                model=model,
            )

            progress.update(task, description="Analyzing drawing...")

            # Run analysis
            result = analyzer.analyze(pdf_path, page_number=page)

            progress.update(task, description="Processing results...")

        # Display summary
        _display_summary(result, verbose)

        # Output results
        if output_format == "json":
            output_data = result.model_dump_json(indent=2)
        elif output_format == "table":
            output_data = json.dumps(result.to_table_format(), indent=2)
        elif output_format == "csv":
            import csv
            import io
            buffer = io.StringIO()
            rows = result.to_table_format()
            if rows:
                writer = csv.DictWriter(buffer, fieldnames=rows[0].keys())
                writer.writeheader()
                writer.writerows(rows)
            output_data = buffer.getvalue()

        if output:
            output.write_text(output_data)
            console.print(f"\n[green]Results saved to:[/green] {output}")
        else:
            console.print("\n[bold]Results:[/bold]")
            if output_format == "csv":
                console.print(output_data)
            else:
                console.print_json(output_data)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        if verbose:
            console.print_exception()
        sys.exit(1)


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
@click.option(
    "--provider",
    "-p",
    type=click.Choice(["openai", "anthropic"]),
    default="openai",
    help="API provider to use",
)
@click.option("--api-key", "-k", envvar="API_KEY", help="API key")
def classify(pdf_path: Path, provider: str, api_key: Optional[str]):
    """Classify a drawing's type and discipline"""
    from .core.models import APIConfig, APIProvider
    from .extraction import PDFExtractor
    from .classification import DrawingClassifier

    console.print(f"[bold]Classifying:[/bold] {pdf_path.name}")

    try:
        # Extract first page
        extractor = PDFExtractor()
        pages = list(extractor.extract(pdf_path))
        if not pages:
            console.print("[red]No pages found in PDF[/red]")
            sys.exit(1)

        thumbnail = pages[0].thumbnail

        # Create classifier
        import os
        api_provider = APIProvider.OPENAI if provider == "openai" else APIProvider.ANTHROPIC
        env_key = "OPENAI_API_KEY" if provider == "openai" else "ANTHROPIC_API_KEY"
        key = api_key or os.environ.get(env_key)

        if not key:
            console.print(f"[red]No API key. Set {env_key} or use --api-key[/red]")
            sys.exit(1)

        config = APIConfig(
            provider=api_provider,
            api_key=key,
            model="gpt-4o" if provider == "openai" else "claude-sonnet-4-20250514",
        )

        classifier = DrawingClassifier(config)
        result = classifier.classify(thumbnail)

        # Display results
        table = Table(title="Classification Results")
        table.add_column("Property", style="cyan")
        table.add_column("Value", style="green")

        table.add_row("Drawing Type", result.drawing_type)
        table.add_row("Discipline", result.discipline)
        table.add_row("Sub-type", result.sub_type or "N/A")
        table.add_row("Confidence", f"{result.confidence:.1%}")

        console.print(table)

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command()
@click.argument("pdf_path", type=click.Path(exists=True, path_type=Path))
@click.option("--page", type=int, default=1, help="Page number to extract")
@click.option("--output", "-o", type=click.Path(path_type=Path), help="Output file")
def extract(pdf_path: Path, page: int, output: Optional[Path]):
    """Extract elements from a drawing (text, annotations, vectors)"""
    from .extraction import PDFExtractor, ElementExtractor

    console.print(f"[bold]Extracting from:[/bold] {pdf_path.name}, page {page}")

    try:
        pdf_extractor = PDFExtractor()
        element_extractor = ElementExtractor()

        pages = list(pdf_extractor.extract(pdf_path))
        if page > len(pages):
            console.print(f"[red]Page {page} not found (PDF has {len(pages)} pages)[/red]")
            sys.exit(1)

        target_page = pages[page - 1]
        elements = element_extractor.extract_elements(target_page)

        # Convert to list format
        element_list = element_extractor.elements_to_list_format(elements)

        # Display summary
        console.print(f"\n[bold]Found {len(elements)} elements:[/bold]")

        type_counts = {}
        for elem in elements:
            t = elem.type.value
            type_counts[t] = type_counts.get(t, 0) + 1

        table = Table(title="Element Summary")
        table.add_column("Type", style="cyan")
        table.add_column("Count", style="green")

        for t, count in sorted(type_counts.items()):
            table.add_row(t, str(count))

        console.print(table)

        # Output
        output_data = json.dumps(element_list, indent=2)
        if output:
            output.write_text(output_data)
            console.print(f"\n[green]Elements saved to:[/green] {output}")
        else:
            console.print("\n[bold]Elements:[/bold]")
            # Show first 10 elements
            for elem in element_list[:10]:
                console.print(f"  [{elem['type']}] {elem['content'][:50]}...")
            if len(element_list) > 10:
                console.print(f"  ... and {len(element_list) - 10} more")

    except Exception as e:
        console.print(f"[red]Error:[/red] {e}")
        sys.exit(1)


@cli.command()
def skills():
    """List available analysis skills"""
    from .skills import list_available_skills

    skills_list = list_available_skills()

    table = Table(title="Available Analysis Skills")
    table.add_column("Name", style="cyan")
    table.add_column("Drawing Types", style="green")
    table.add_column("Disciplines", style="blue")
    table.add_column("Description")

    for skill in skills_list:
        table.add_row(
            skill["name"],
            ", ".join(skill["drawing_types"][:3]),
            ", ".join(skill["disciplines"][:3]),
            skill["description"][:40] + "...",
        )

    console.print(table)


@cli.command()
@click.option("--host", default="127.0.0.1", help="Host to bind to")
@click.option("--port", default=5000, help="Port to bind to")
@click.option("--debug", is_flag=True, help="Enable debug mode")
def serve(host: str, port: int, debug: bool):
    """Start the web API server"""
    from .api import create_app

    console.print(f"[bold blue]Starting Drawing Analyzer API[/bold blue]")
    console.print(f"Server: http://{host}:{port}")
    console.print(f"Web UI: http://{host}:{port}/")

    app = create_app()
    app.run(host=host, port=port, debug=debug)


def _display_summary(result, verbose: bool):
    """Display analysis summary"""
    # Classification
    console.print("\n[bold]Classification:[/bold]")
    console.print(f"  Type: {result.classification.drawing_type}")
    console.print(f"  Discipline: {result.classification.discipline}")
    console.print(f"  Confidence: {result.classification.confidence:.1%}")

    # Metadata
    if result.metadata.drawing_number:
        console.print(f"\n[bold]Metadata:[/bold]")
        console.print(f"  Drawing #: {result.metadata.drawing_number}")
        if result.metadata.revision:
            console.print(f"  Revision: {result.metadata.revision}")
        if result.metadata.scale:
            console.print(f"  Scale: {result.metadata.scale}")

    # Statistics
    console.print(f"\n[bold]Analysis Summary:[/bold]")
    console.print(f"  Elements found: {result.total_elements}")
    console.print(f"  Quantities extracted: {result.total_quantities}")
    console.print(f"  Average confidence: {result.average_confidence:.1%}")
    console.print(f"  Items needing review: {result.requires_review_count}")
    console.print(f"  Kernels analyzed: {len(result.kernels_analyzed)}")

    # Quantities table
    if result.quantities and verbose:
        table = Table(title=f"Quantities (showing first 10 of {len(result.quantities)})")
        table.add_column("Description", style="cyan")
        table.add_column("Qty", style="green")
        table.add_column("Unit")
        table.add_column("Category")
        table.add_column("Confidence")

        for q in result.quantities[:10]:
            table.add_row(
                q.description[:30] + ("..." if len(q.description) > 30 else ""),
                str(q.quantity),
                q.unit.value,
                q.category.level1,
                f"{q.confidence:.0%}",
            )

        console.print(table)


def main():
    """Main entry point"""
    cli()


if __name__ == "__main__":
    main()
