"""
Data models for the Toxicity + Off-topic Guardian.
"""
from dataclasses import dataclass, field
from typing import Literal


@dataclass
class ConversationMessage:
    """Represents a single message in a conversation."""
    role: str  # "user" or "assistant"
    content: str

    def to_dict(self) -> dict:
        """Convert to dictionary format."""
        return {"role": self.role, "content": self.content}


@dataclass
class ClassificationVerdict:
    """
    The structured verdict from the Friendli classifier.
    """
    is_toxic: bool
    is_sensitive: bool
    is_off_topic: bool
    severity: Literal["none", "low", "medium", "high"]
    categories: list[str] = field(default_factory=list)
    notes: str = ""

    @classmethod
    def from_dict(cls, data: dict) -> "ClassificationVerdict":
        """
        Construct a ClassificationVerdict from a dictionary (e.g., parsed JSON).

        Args:
            data: Dictionary containing classification results

        Returns:
            ClassificationVerdict instance
        """
        return cls(
            is_toxic=data.get("is_toxic", False),
            is_sensitive=data.get("is_sensitive", False),
            is_off_topic=data.get("is_off_topic", False),
            severity=data.get("severity", "none"),
            categories=data.get("categories", []),
            notes=data.get("notes", ""),
        )

    @classmethod
    def safe_default(cls, error_msg: str = "Failed to classify") -> "ClassificationVerdict":
        """
        Returns a safe default verdict when classification fails.

        Args:
            error_msg: Optional error message to include in notes

        Returns:
            Safe default ClassificationVerdict
        """
        return cls(
            is_toxic=False,
            is_sensitive=False,
            is_off_topic=False,
            severity="none",
            categories=[],
            notes=f"{error_msg}, defaulting to safe verdict.",
        )

    def to_dict(self) -> dict:
        """Convert to dictionary format for logging."""
        return {
            "is_toxic": self.is_toxic,
            "is_sensitive": self.is_sensitive,
            "is_off_topic": self.is_off_topic,
            "severity": self.severity,
            "categories": self.categories,
            "notes": self.notes,
        }


@dataclass
class GuardianConfig:
    """Configuration for Guardian behavior."""
    enforce_blocking: bool = True  # Default to blocking enabled for safety
    log_to_opik: bool = True
    log_unflagged: bool = True
    max_context_messages: int = 5

    # Fallback message used when blocking is enforced
    safe_fallback_message: str = (
        "I'm not able to continue with this direction. Let's refocus on your goals "
        "and wellbeing. If you're in crisis, please contact local emergency services "
        "or a trusted support line."
    )
