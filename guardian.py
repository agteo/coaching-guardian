"""
Guardian: Toxicity + Off-topic monitoring for coaching agents.

The Guardian wraps an existing coaching agent and adds:
1. Classification of responses for toxicity, sensitivity, and off-topic drift
2. Logging to Comet Opik for observability
3. Optional blocking of problematic responses
"""
import logging
from typing import Callable, Optional

from models import ConversationMessage, GuardianConfig, ClassificationVerdict
from friendli_client import classify_interaction
from opik_client import log_interaction_to_opik


logger = logging.getLogger(__name__)


class Guardian:
    """
    Guardian wrapper for coaching agents.

    Monitors agent responses for toxicity, sensitivity, and off-topic drift.
    Logs all interactions to Comet Opik for analysis and improvement.
    """

    def __init__(
        self,
        coach_fn: Callable[[list[ConversationMessage]], str],
        config: Optional[GuardianConfig] = None,
    ):
        """
        Initialize the Guardian.

        Args:
            coach_fn: Existing coaching function that takes conversation history
                     and returns a response string
            config: Optional GuardianConfig for customizing behavior
        """
        self.coach_fn = coach_fn
        self.config = config or GuardianConfig()
        logger.info(f"Guardian initialized with enforce_blocking={self.config.enforce_blocking}")

    def generate_guarded_response(
        self,
        conversation_history: list[ConversationMessage],
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Generate a response with guardian monitoring.

        This method:
        1. Calls the coaching agent to get a candidate response
        2. Classifies the interaction using Friendli
        3. Logs to Opik if configured
        4. Returns the final response (potentially blocked if configured)

        Args:
            conversation_history: List of conversation messages
            metadata: Optional metadata to include in logs

        Returns:
            The final response string (either coach response or fallback)
        """
        # Step 1: Get candidate response from coach
        try:
            coach_response = self.coach_fn(conversation_history)
            logger.debug(f"Coach generated response: {coach_response[:100]}...")
        except Exception as e:
            logger.error(f"Coach function failed: {e}")
            return "I'm having trouble processing your request right now. Please try again."

        # Step 2: Extract context for classification
        user_message = ""
        if conversation_history and conversation_history[-1].role == "user":
            user_message = conversation_history[-1].content

        context_snippet = conversation_history[-self.config.max_context_messages:]

        # Step 3: Classify the interaction
        verdict = classify_interaction(
            user_message=user_message,
            coach_response=coach_response,
            conversation_context=context_snippet,
        )

        logger.info(
            f"Classification: toxic={verdict.is_toxic}, sensitive={verdict.is_sensitive}, "
            f"off_topic={verdict.is_off_topic}, severity={verdict.severity}"
        )

        # Step 4: Log to Opik if configured
        if self.config.log_to_opik:
            # Check if we should log (based on log_unflagged setting)
            should_log = self.config.log_unflagged or self._is_flagged(verdict)

            if should_log:
                enhanced_metadata = {
                    "enforce_blocking": self.config.enforce_blocking,
                    **(metadata or {}),
                }
                log_interaction_to_opik(
                    conversation_history=conversation_history,
                    coach_response=coach_response,
                    verdict=verdict,
                    metadata=enhanced_metadata,
                )

        # Step 5: Determine final response based on blocking policy
        final_response = self._apply_blocking_policy(coach_response, verdict)

        return final_response

    def _is_flagged(self, verdict: ClassificationVerdict) -> bool:
        """
        Check if a verdict represents a flagged interaction.

        Args:
            verdict: The classification verdict

        Returns:
            True if the interaction is flagged
        """
        return (
            verdict.is_toxic
            or verdict.is_sensitive
            or verdict.is_off_topic
            or verdict.severity in ["medium", "high"]
        )

    def _apply_blocking_policy(
        self,
        coach_response: str,
        verdict: ClassificationVerdict,
    ) -> str:
        """
        Apply the blocking policy based on the verdict.

        Args:
            coach_response: The original coach response
            verdict: The classification verdict

        Returns:
            Either the original response or a safe fallback message
        """
        # If blocking is not enforced, always return the coach response
        if not self.config.enforce_blocking:
            return coach_response

        # Check if we should block based on severity or specific flags
        # Also check for dangerous categories like inappropriate_request with high severity
        has_dangerous_category = (
            "inappropriate_request" in verdict.categories
            and verdict.severity in ["medium", "high"]
        ) or "self_harm" in verdict.categories or "crisis" in verdict.categories
        
        should_block = (
            verdict.severity in ["medium", "high"]
            or verdict.is_toxic
            or verdict.is_sensitive
            or has_dangerous_category
        )

        if should_block:
            logger.warning(
                f"Blocking response due to: severity={verdict.severity}, "
                f"toxic={verdict.is_toxic}, sensitive={verdict.is_sensitive}, "
                f"categories={verdict.categories}"
            )
            return self.config.safe_fallback_message

        # Otherwise, return the original response
        return coach_response

    def generate_guarded_response_dict(
        self,
        conversation_history: list[dict],
        metadata: Optional[dict] = None,
    ) -> str:
        """
        Convenience method that accepts conversation history as list of dicts.

        Args:
            conversation_history: List of dicts with "role" and "content" keys
            metadata: Optional metadata to include in logs

        Returns:
            The final response string
        """
        # Convert dict format to ConversationMessage objects
        messages = [
            ConversationMessage(role=msg["role"], content=msg["content"])
            for msg in conversation_history
        ]

        return self.generate_guarded_response(messages, metadata)
