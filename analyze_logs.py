"""
Analyze and visualize Guardian logs from Opik.

This script fetches logs from Opik and provides analysis and visualization.
"""
import os
from collections import Counter
from datetime import datetime, timedelta
from typing import Optional

try:
    from rich.console import Console
    from rich.table import Table
    from rich.panel import Panel
    from rich import box
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False


console = Console() if RICH_AVAILABLE else None


def get_opik_traces(limit: int = 100, days_back: int = 7):
    """
    Fetch recent traces from Opik.

    Args:
        limit: Maximum number of traces to fetch
        days_back: How many days back to fetch

    Returns:
        List of trace objects
    """
    try:
        from opik import Opik
        import opik

        api_key = os.getenv("OPIK_API_KEY")
        project_name = os.getenv("OPIK_PROJECT_NAME", "coaching-guardian")
        workspace_name = os.getenv("OPIK_WORKSPACE_NAME")

        if not api_key:
            print("❌ OPIK_API_KEY not set. Cannot fetch traces.")
            return []

        # Configure and initialize
        opik.configure(api_key=api_key, workspace=workspace_name)
        client = Opik(project_name=project_name)

        print(f"📊 Fetching traces from project: {project_name}")
        print(f"   Looking back {days_back} days, limit {limit} traces\n")

        # This is a placeholder - actual API depends on Opik's Python SDK
        # You may need to adjust based on the actual Opik API
        # For now, we'll show what the analysis would look like

        print("⚠️  Note: This is a demo of analysis capabilities.")
        print("   The actual Opik SDK integration may vary.\n")
        print("   For full visualization, use the Opik web dashboard at:")
        print("   https://www.comet.com\n")

        return []

    except ImportError:
        print("❌ opik package not installed. Run: pip install opik")
        return []
    except Exception as e:
        print(f"❌ Error fetching from Opik: {e}")
        return []


def analyze_traces(traces: list):
    """
    Analyze traces and display statistics.

    Args:
        traces: List of trace objects from Opik
    """
    if not traces:
        display_demo_analysis()
        return

    # Count severities
    severities = Counter()
    toxicity_count = 0
    sensitivity_count = 0
    off_topic_count = 0
    categories = Counter()

    for trace in traces:
        metadata = trace.get("metadata", {})
        classification = metadata.get("classification", {})

        severity = classification.get("severity", "none")
        severities[severity] += 1

        if classification.get("is_toxic"):
            toxicity_count += 1
        if classification.get("is_sensitive"):
            sensitivity_count += 1
        if classification.get("is_off_topic"):
            off_topic_count += 1

        for cat in classification.get("categories", []):
            categories[cat] += 1

    # Display results
    display_analysis_results(
        total=len(traces),
        severities=severities,
        toxicity_count=toxicity_count,
        sensitivity_count=sensitivity_count,
        off_topic_count=off_topic_count,
        categories=categories,
    )


def display_analysis_results(
    total: int,
    severities: Counter,
    toxicity_count: int,
    sensitivity_count: int,
    off_topic_count: int,
    categories: Counter,
):
    """Display analysis results in a nice format."""

    if RICH_AVAILABLE:
        console.print("\n[bold cyan]📊 Guardian Analysis Results[/bold cyan]\n")

        # Summary table
        table = Table(title="Summary", box=box.ROUNDED)
        table.add_column("Metric", style="cyan", width=30)
        table.add_column("Count", justify="right", style="yellow", width=15)
        table.add_column("Percentage", justify="right", style="green", width=15)

        table.add_row("Total Interactions", str(total), "100%")
        table.add_row("Toxic", str(toxicity_count), f"{toxicity_count/total*100:.1f}%" if total else "0%")
        table.add_row("Sensitive", str(sensitivity_count), f"{sensitivity_count/total*100:.1f}%" if total else "0%")
        table.add_row("Off-topic", str(off_topic_count), f"{off_topic_count/total*100:.1f}%" if total else "0%")

        console.print(table)
        console.print()

        # Severity breakdown
        sev_table = Table(title="Severity Breakdown", box=box.ROUNDED)
        sev_table.add_column("Severity", style="cyan")
        sev_table.add_column("Count", justify="right", style="yellow")

        severity_colors = {
            "none": "green",
            "low": "yellow",
            "medium": "orange1",
            "high": "red"
        }

        for sev in ["none", "low", "medium", "high"]:
            count = severities.get(sev, 0)
            color = severity_colors.get(sev, "white")
            sev_table.add_row(f"[{color}]{sev.upper()}[/{color}]", str(count))

        console.print(sev_table)
        console.print()

        # Categories
        if categories:
            cat_table = Table(title="Top Categories", box=box.ROUNDED)
            cat_table.add_column("Category", style="cyan")
            cat_table.add_column("Count", justify="right", style="yellow")

            for cat, count in categories.most_common(10):
                cat_table.add_row(cat, str(count))

            console.print(cat_table)
            console.print()

    else:
        # Plain text output
        print("\n" + "=" * 60)
        print("GUARDIAN ANALYSIS RESULTS")
        print("=" * 60)
        print(f"\nTotal Interactions: {total}")
        print(f"Toxic: {toxicity_count} ({toxicity_count/total*100:.1f}%)" if total else "0%")
        print(f"Sensitive: {sensitivity_count} ({sensitivity_count/total*100:.1f}%)" if total else "0%")
        print(f"Off-topic: {off_topic_count} ({off_topic_count/total*100:.1f}%)" if total else "0%")

        print("\nSeverity Breakdown:")
        for sev in ["none", "low", "medium", "high"]:
            count = severities.get(sev, 0)
            print(f"  {sev.upper()}: {count}")

        if categories:
            print("\nTop Categories:")
            for cat, count in categories.most_common(10):
                print(f"  {cat}: {count}")

        print("\n" + "=" * 60 + "\n")


def display_demo_analysis():
    """Display a demo analysis with sample data."""

    if RICH_AVAILABLE:
        console.print("\n[yellow]📋 Demo Analysis (Sample Data)[/yellow]\n")
        console.print("[dim]This is what the analysis would look like with real data from Opik.[/dim]\n")

    # Sample data
    total = 50
    severities = Counter({"none": 35, "low": 10, "medium": 4, "high": 1})
    toxicity_count = 2
    sensitivity_count = 1
    off_topic_count = 8
    categories = Counter({
        "off_topic_chatter": 8,
        "harassment": 2,
        "self_harm": 1,
        "inappropriate_request": 3,
    })

    display_analysis_results(
        total=total,
        severities=severities,
        toxicity_count=toxicity_count,
        sensitivity_count=sensitivity_count,
        off_topic_count=off_topic_count,
        categories=categories,
    )

    if RICH_AVAILABLE:
        console.print("[cyan]💡 Tips:[/cyan]")
        console.print("  • Set OPIK_API_KEY to fetch real data")
        console.print("  • View full details at https://www.comet.com")
        console.print("  • Use Opik dashboard for advanced filtering and visualization\n")


def main():
    """Main analysis function."""

    if RICH_AVAILABLE:
        console.print("\n[bold cyan]" + "=" * 60 + "[/bold cyan]")
        console.print("[bold cyan]Guardian Log Analysis[/bold cyan]")
        console.print("[bold cyan]" + "=" * 60 + "[/bold cyan]\n")
    else:
        print("\n" + "=" * 60)
        print("GUARDIAN LOG ANALYSIS")
        print("=" * 60 + "\n")
        print("💡 Tip: Install 'rich' for better visualization: pip install rich\n")

    # Fetch traces
    traces = get_opik_traces(limit=100, days_back=7)

    # Analyze
    analyze_traces(traces)


if __name__ == "__main__":
    # Load environment variables
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        pass

    main()
