"""
Demo script for testing the Guardian system.

This script provides an interactive CLI to test the Guardian with a simple
mock coaching agent.
"""
import os
import logging
from typing import Optional

from models import ConversationMessage, GuardianConfig
from guardian import Guardian


# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def simple_coach_response(conversation_history: list[ConversationMessage]) -> str:
    """
    A more natural mock coaching agent that provides supportive, contextual responses.

    In a real application, this would be replaced with your actual
    coaching agent (e.g., an LLM-based agent).

    Args:
        conversation_history: List of conversation messages

    Returns:
        A coaching response string
    """
    if not conversation_history:
        return "Hello! I'm here to support you on your journey. What would you like to work on today?"

    # Get conversation context
    last_message = conversation_history[-1].content.lower() if conversation_history else ""
    user_messages = [msg.content for msg in conversation_history if msg.role == "user"]
    coach_messages = [msg.content for msg in conversation_history if msg.role == "assistant"]
    
    # Check if this is early in conversation (first 2 exchanges)
    is_early = len(user_messages) <= 2

    # Handle greetings and acknowledgments
    if any(word in last_message for word in ["hi", "hello", "hey"]):
        if len(user_messages) == 1:
            return "Hi there! I'm glad you're here. What's on your mind today?"
        else:
            return "Hey! Good to hear from you again. How are things going?"

    # Handle gratitude
    if any(word in last_message for word in ["thank", "thanks", "appreciate"]):
        responses = [
            "You're welcome! I'm here whenever you need support.",
            "Of course! That's what I'm here for. What else is on your mind?",
            "Happy to help! Remember, small steps lead to big changes. What would you like to explore next?",
        ]
        return responses[len(coach_messages) % len(responses)]

    # Handle goals and career topics
    if any(word in last_message for word in ["goal", "career", "job", "work", "professional"]):
        if is_early:
            responses = [
                "That's a meaningful area to explore. What draws you to focus on this right now?",
                "I'd love to understand more about what you're hoping to achieve. Can you tell me what success looks like for you?",
                "Goals are powerful motivators. What specific aspect feels most important to you at this moment?",
            ]
        else:
            # Reference previous conversation
            responses = [
                "Building on what we've discussed, what feels like the next step forward?",
                "Given what you've shared, what would make the biggest difference right now?",
                "I'm curious - what's changed since we last talked about this?",
            ]
        return responses[len(coach_messages) % len(responses)]

    # Handle feeling stuck or overwhelmed
    if any(word in last_message for word in ["stuck", "overwhelm", "overwhelmed", "frustrated", "frustrating"]):
        responses = [
            "It sounds like you're going through a challenging time. Can you tell me more about what's making you feel this way?",
            "Those feelings are completely valid. What do you think might be contributing to this?",
            "I hear you. When you say you feel stuck, what does that look like day-to-day?",
            "That must be really difficult. What would feel like a small step forward, even if it's tiny?",
        ]
        return responses[len(coach_messages) % len(responses)]

    # Handle procrastination
    if any(word in last_message for word in ["procrastinat", "delay", "putting off", "avoid"]):
        responses = [
            "Procrastination often has deeper roots. What do you think might be underneath this?",
            "I'm curious - when you think about starting, what comes up for you?",
            "Sometimes we delay things because we're afraid of what might happen. Does that resonate with you?",
            "What would need to be different for you to take that first step?",
        ]
        return responses[len(coach_messages) % len(responses)]

    # Handle questions directed at the coach
    if "?" in conversation_history[-1].content and any(word in last_message for word in ["you", "your", "what do you"]):
        responses = [
            "I'm here to support you, so I'd love to hear more about what you're thinking.",
            "That's a great question. What's your gut feeling about it?",
            "I'm curious what your perspective is on that. What comes to mind for you?",
        ]
        return responses[len(coach_messages) % len(responses)]

    # Handle short responses (yes, no, okay, etc.)
    if last_message.strip() in ["yes", "no", "ok", "okay", "yeah", "yep", "nope", "maybe"]:
        if len(coach_messages) > 0:
            # Try to reference the last coach question
            last_coach = coach_messages[-1] if coach_messages else ""
            if "?" in last_coach:
                return "Tell me more about that. What's behind your answer?"
            else:
                return "I'd love to understand more. Can you elaborate?"
        else:
            return "I'd like to understand better. Can you share a bit more?"

    # Handle emotional language
    if any(word in last_message for word in ["feel", "feeling", "emotion", "anxious", "worried", "excited", "happy", "sad"]):
        responses = [
            "I appreciate you sharing that with me. What's it like to feel that way?",
            "Thank you for being open about that. How long have you been noticing this feeling?",
            "That's important. What do you think might be contributing to this feeling?",
        ]
        return responses[len(coach_messages) % len(responses)]

    # Default - more natural follow-up
    # Vary responses based on conversation length
    if is_early:
        responses = [
            "I hear you. What feels most important to explore right now?",
            "Thanks for sharing that. Can you tell me more about what's on your mind?",
            "I'd like to understand better. What's the heart of what you're dealing with?",
        ]
    else:
        # Reference that we've been talking
        responses = [
            "Building on our conversation, what feels like the next piece to explore?",
            "I'm noticing some patterns in what you're sharing. What stands out to you?",
            "Given what we've discussed, what would be most helpful to dive into now?",
            "I'm curious - what's shifted for you since we started talking?",
        ]
    
    return responses[len(coach_messages) % len(responses)]


def main():
    """Run the interactive Guardian demo."""
    print("=" * 60)
    print("Guardian Demo - Toxicity + Off-topic Monitoring")
    print("=" * 60)
    print("\nThis demo simulates a coaching conversation with Guardian monitoring.")
    print("Type your messages as a user, and see how the Guardian classifies them.")
    print("\nCommands:")
    print("  - Type 'quit' or 'exit' to end the session")
    print("  - Type 'clear' to start a new conversation")
    print("  - Type 'toggle-blocking' to enable/disable response blocking")
    print("=" * 60)
    print()

    # Check environment variables
    if not os.getenv("FRIENDLI_API_KEY"):
        print("⚠️  WARNING: FRIENDLI_API_KEY not set. Classification will fail gracefully.")
        print("   Set it in your .env file or environment to test classification.\n")

    if not os.getenv("OPIK_API_KEY"):
        print("⚠️  WARNING: OPIK_API_KEY not set. Logging to Opik will be disabled.")
        print("   Set it in your .env file or environment to test logging.\n")

    # Initialize configuration
    # Read blocking setting from environment variable, default to True
    enforce_blocking_env = os.getenv("GUARDIAN_ENFORCE_BLOCKING", "true").lower()
    enforce_blocking = enforce_blocking_env in ("true", "1", "yes", "on")
    
    config = GuardianConfig(
        enforce_blocking=enforce_blocking,
        log_to_opik=True,
        log_unflagged=True,  # Log everything for demo purposes
        max_context_messages=5,
    )

    # Initialize Guardian
    guardian = Guardian(coach_fn=simple_coach_response, config=config)

    # Conversation history
    conversation_history: list[ConversationMessage] = []

    print(f"Guardian initialized with blocking={'ENABLED' if config.enforce_blocking else 'DISABLED'}\n")

    # Main conversation loop
    while True:
        try:
            # Get user input
            user_input = input("You: ").strip()

            if not user_input:
                continue

            # Handle commands
            if user_input.lower() in ['quit', 'exit']:
                print("\nEnding session. Goodbye!")
                break

            if user_input.lower() == 'clear':
                conversation_history = []
                print("\n✓ Conversation cleared. Starting fresh.\n")
                continue

            if user_input.lower() == 'toggle-blocking':
                config.enforce_blocking = not config.enforce_blocking
                status = "ENABLED" if config.enforce_blocking else "DISABLED"
                print(f"\n✓ Response blocking is now {status}\n")
                continue

            # Add user message to history
            conversation_history.append(
                ConversationMessage(role="user", content=user_input)
            )

            # Generate guarded response
            print("\n[Guardian is analyzing...]")
            response = guardian.generate_guarded_response(conversation_history)

            # Add assistant response to history
            conversation_history.append(
                ConversationMessage(role="assistant", content=response)
            )

            # Print response
            print(f"\nCoach: {response}\n")

        except KeyboardInterrupt:
            print("\n\nInterrupted. Ending session.")
            break

        except Exception as e:
            logger.error(f"Error in demo loop: {e}")
            print(f"\n❌ Error: {e}\n")


if __name__ == "__main__":
    # Load environment variables from .env file if available
    try:
        from dotenv import load_dotenv
        load_dotenv()
    except ImportError:
        logger.warning("python-dotenv not installed. Using system environment variables only.")

    main()
