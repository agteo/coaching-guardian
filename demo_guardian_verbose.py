"""
Verbose demo script for testing the Guardian system with detailed output.

This version shows the full classification verdict after each interaction.
"""
import os
import logging
from typing import Optional
from rich.console import Console
from rich.panel import Panel
from rich.table import Table
from rich import box

from models import ConversationMessage, GuardianConfig, ClassificationVerdict
from guardian import Guardian
from friendli_client import classify_interaction


# Configure logging
logging.basicConfig(
    level=logging.WARNING,  # Reduce noise for cleaner output
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# Rich console for pretty output
console = Console()


def simple_coach_response(conversation_history: list[ConversationMessage]) -> str:
    """
    A simple mock coaching agent that provides supportive responses.

    In a real application, this would be replaced with your actual
    coaching agent (e.g., an LLM-based agent).

    Args:
        conversation_history: List of conversation messages

    Returns:
        A coaching response string
    """
    if not conversation_history:
        return "Hello! I'm here to support you on your journey. What would you like to work on today?"

    # Get the last user message
    last_message = conversation_history[-1].content.lower() if conversation_history else ""

    # Simple pattern matching for demo purposes
    if "goal" in last_message or "career" in last_message:
        return "That's a great area to focus on! What specific aspects of your career goals would you like to explore?"

    elif "stuck" in last_message or "overwhelm" in last_message:
        return "It's completely normal to feel stuck sometimes. Can you tell me more about what's making you feel this way?"

    elif "procrastinating" in last_message or "procrastination" in last_message:
        return "Procrastination often has underlying causes. What do you think might be holding you back from taking action?"

    elif "thank" in last_message or "thanks" in last_message:
        return "You're welcome! Remember, progress happens one step at a time. What else would you like to discuss?"

    elif any(word in last_message for word in ["hate", "angry", "furious", "stupid"]):
        return "I hear that you're feeling frustrated. Let's talk about what's behind these feelings."

    elif any(word in last_message for word in ["weather", "sports", "movie", "game"]):
        return "That's interesting! But let's bring our focus back to your personal goals. What would you like to work on today?"

    else:
        return "I hear you. Tell me more about that - what feels most important to address right now?"


def display_classification_verdict(verdict: ClassificationVerdict, coach_response: str):
    """Display the classification verdict in a nice table format."""

    # Create status indicators
    toxic_status = "🔴 YES" if verdict.is_toxic else "✅ NO"
    sensitive_status = "🔴 YES" if verdict.is_sensitive else "✅ NO"
    off_topic_status = "⚠️  YES" if verdict.is_off_topic else "✅ NO"

    # Severity color
    severity_colors = {
        "none": "green",
        "low": "yellow",
        "medium": "orange1",
        "high": "red"
    }
    severity_color = severity_colors.get(verdict.severity, "white")

    # Create table
    table = Table(title="🛡️  Guardian Classification", box=box.ROUNDED, show_header=True)
    table.add_column("Category", style="cyan", width=20)
    table.add_column("Result", width=40)

    table.add_row("Toxic", toxic_status)
    table.add_row("Sensitive", sensitive_status)
    table.add_row("Off-topic", off_topic_status)
    table.add_row("Severity", f"[{severity_color}]{verdict.severity.upper()}[/{severity_color}]")

    if verdict.categories:
        table.add_row("Categories", ", ".join(verdict.categories))

    if verdict.notes:
        table.add_row("Notes", verdict.notes)

    console.print(table)
    console.print()


def main():
    """Run the verbose interactive Guardian demo."""
    console.print("\n[bold cyan]" + "=" * 60 + "[/bold cyan]")
    console.print("[bold cyan]Guardian Verbose Demo - See Classifications in Real-Time[/bold cyan]")
    console.print("[bold cyan]" + "=" * 60 + "[/bold cyan]\n")

    console.print("This demo shows detailed classification results after each interaction.\n")
    console.print("[bold]Commands:[/bold]")
    console.print("  • Type [yellow]'quit'[/yellow] or [yellow]'exit'[/yellow] to end")
    console.print("  • Type [yellow]'clear'[/yellow] to start a new conversation")
    console.print("  • Type [yellow]'toggle-blocking'[/yellow] to enable/disable response blocking")
    console.print("  • Type [yellow]'test'[/yellow] to see example test messages\n")

    console.print("[bold cyan]" + "=" * 60 + "[/bold cyan]\n")

    # Check environment variables
    if not os.getenv("FRIENDLI_API_KEY"):
        console.print("[yellow]⚠️  WARNING: FRIENDLI_API_KEY not set. Using safe default verdicts.[/yellow]")
        console.print("[dim]   Set it in your .env file to test real classification.[/dim]\n")

    if not os.getenv("OPIK_API_KEY"):
        console.print("[yellow]⚠️  WARNING: OPIK_API_KEY not set. Logging disabled.[/yellow]")
        console.print("[dim]   Set it in your .env file to enable logging.[/dim]\n")

    # Initialize configuration
    # Read blocking setting from environment variable, default to True
    enforce_blocking_env = os.getenv("GUARDIAN_ENFORCE_BLOCKING", "true").lower()
    enforce_blocking = enforce_blocking_env in ("true", "1", "yes", "on")
    
    config = GuardianConfig(
        enforce_blocking=enforce_blocking,
        log_to_opik=True,
        log_unflagged=True,
        max_context_messages=5,
    )

    # Initialize Guardian
    guardian = Guardian(coach_fn=simple_coach_response, config=config)

    # Conversation history
    conversation_history: list[ConversationMessage] = []

    blocking_status = "[red]ENABLED[/red]" if config.enforce_blocking else "[green]DISABLED[/green]"
    console.print(f"Guardian initialized | Blocking: {blocking_status}\n")

    # Test messages
    test_messages = [
        "I feel stuck in my career",
        "I keep procrastinating on applications",
        "What's the weather like today?",
        "I'm feeling really angry about everything",
    ]

    # Main conversation loop
    while True:
        try:
            # Get user input
            user_input = console.input("[bold blue]You:[/bold blue] ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.lower() in ['quit', 'exit']:
                console.print("\n[green]Ending session. Goodbye![/green]\n")
                break

            if user_input.lower() == 'clear':
                conversation_history = []
                console.print("\n[green]✓ Conversation cleared. Starting fresh.[/green]\n")
                continue

            if user_input.lower() == 'toggle-blocking':
                config.enforce_blocking = not config.enforce_blocking
                status = "[red]ENABLED[/red]" if config.enforce_blocking else "[green]DISABLED[/green]"
                console.print(f"\n[green]✓ Response blocking is now {status}[/green]\n")
                continue

            if user_input.lower() == 'test':
                console.print("\n[yellow]📋 Test Messages You Can Try:[/yellow]")
                for i, msg in enumerate(test_messages, 1):
                    console.print(f"  {i}. \"{msg}\"")
                console.print()
                continue

            # Add user message to history
            conversation_history.append(
                ConversationMessage(role="user", content=user_input)
            )

            # Generate coach response first
            coach_response = simple_coach_response(conversation_history)

            # Get classification
            console.print("\n[dim]🔍 Guardian is analyzing...[/dim]\n")

            user_message = user_input
            context_snippet = conversation_history[-config.max_context_messages:]

            verdict = classify_interaction(
                user_message=user_message,
                coach_response=coach_response,
                conversation_context=context_snippet,
            )

            # Display classification
            display_classification_verdict(verdict, coach_response)

            # Apply blocking if needed
            final_response = guardian._apply_blocking_policy(coach_response, verdict)

            if final_response != coach_response:
                console.print("[red]⚠️  Response was BLOCKED due to classification[/red]\n")

            # Add assistant response to history
            conversation_history.append(
                ConversationMessage(role="assistant", content=final_response)
            )

            # Print response
            console.print(Panel(
                final_response,
                title="[bold green]Coach Response[/bold green]",
                border_style="green"
            ))
            console.print()

        except KeyboardInterrupt:
            console.print("\n\n[yellow]Interrupted. Ending session.[/yellow]")
            break

        except Exception as e:
            logger.error(f"Error in demo loop: {e}")
            console.print(f"\n[red]❌ Error: {e}[/red]\n")


if __name__ == "__main__":
    # Load environment variables from .env file if available
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        logger.warning("python-dotenv not installed. Using system environment variables only.")

    try:
        main()
    except ImportError as e:
        if "rich" in str(e):
            console = Console()
            console.print("\n[red]❌ Error: 'rich' package not installed.[/red]")
            console.print("\nInstall it with: [yellow]pip install rich[/yellow]\n")
        else:
            raise
