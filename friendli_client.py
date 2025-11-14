"""
Friendli client wrapper for toxicity and off-topic classification.
"""
import os
import json
import logging
import re
from typing import Optional
import requests

from models import ConversationMessage, ClassificationVerdict


logger = logging.getLogger(__name__)


# System prompt for the Friendli classifier
CLASSIFIER_SYSTEM_PROMPT = """You are a safety and relevance classifier for an AI coaching assistant.

Your job is to analyze conversations between a user and a coaching agent, and classify the interaction based on:

1. **Toxicity**: Is there abusive, harassing, hateful, aggressive language, or requests for dangerous/violent activities (weapons, explosives, harm to others)?
2. **Sensitivity**: Does the content involve self-harm, crisis situations, explicit medical advice, or other highly sensitive topics that a coaching agent should not handle?
3. **Off-topic**: Is the conversation drifting away from coaching goals into casual chat, unrelated topics, or inappropriate requests?

**Severity levels**:
- "none": No issues detected
- "low": Minor concerns, worth noting but not problematic
- "medium": Moderate concerns, potentially problematic
- "high": Serious concerns, should likely be blocked or escalated

**Categories** (you can use multiple):
- "harassment": Abusive or harassing language
- "hate_speech": Hateful content
- "self_harm": Content about self-harm or suicide
- "medical_advice": Requests for medical diagnosis or treatment
- "off_topic_chatter": Casual conversation unrelated to coaching
- "inappropriate_request": Requests outside coaching scope
- "crisis": User appears to be in crisis
- "other": Other concerns (explain in notes)

Return ONLY valid JSON with this exact structure:
{
  "is_toxic": false,
  "is_sensitive": false,
  "is_off_topic": false,
  "severity": "none",
  "categories": [],
  "notes": "Brief explanation of your classification."
}
"""


def _local_fallback_classifier(
    user_message: str,
    coach_response: str,
) -> ClassificationVerdict:
    """
    Fallback local classifier for when Friendli API is unavailable.
    Uses pattern matching to detect obvious toxic, dangerous, or sensitive content.
    
    Args:
        user_message: The latest message from the user
        coach_response: The candidate response from the coaching agent
        
    Returns:
        ClassificationVerdict with classification results
    """
    text_lower = (user_message + " " + coach_response).lower()
    
    # Dangerous/violent content patterns
    dangerous_patterns = [
        r'\b(bomb|explosive|weapon|gun|shoot|kill|murder|assassinate|violence|attack|harm)\b',
        r'\b(how to (make|build|create|construct).*(bomb|explosive|weapon|poison))\b',
        r'\b(threat|threaten|hurt|injure|violence)\b',
    ]
    
    # Toxic/hateful content patterns
    toxic_patterns = [
        r'\b(fuck you|damn you|hate you|kill yourself|die)\b',
        r'\b(racist|sexist|homophobic|slur)\b',
    ]
    
    # Self-harm/crisis patterns
    self_harm_patterns = [
        r'\b(suicide|kill myself|end my life|self harm|cutting|overdose)\b',
        r'\b(want to die|better off dead|no reason to live)\b',
    ]
    
    # Medical advice requests
    medical_patterns = [
        r'\b(diagnose|diagnosis|prescription|medication|treatment for|symptom|disease|illness)\b',
        r'\b(should i take|what medicine|medical advice|doctor|physician)\b',
    ]
    
    # Check for dangerous content
    is_dangerous = any(re.search(pattern, text_lower) for pattern in dangerous_patterns)
    is_toxic = any(re.search(pattern, text_lower) for pattern in toxic_patterns)
    is_self_harm = any(re.search(pattern, text_lower) for pattern in self_harm_patterns)
    is_medical = any(re.search(pattern, text_lower) for pattern in medical_patterns)
    
    # Determine severity and categories
    categories = []
    severity = "none"
    notes = "Local fallback classification"
    
    if is_dangerous:
        is_toxic = True
        severity = "high"
        categories.append("inappropriate_request")
        notes = "Detected dangerous or violent content"
    
    if is_toxic:
        if severity == "none":
            severity = "high"
        if "harassment" not in categories:
            categories.append("harassment")
        notes = "Detected toxic or harmful language"
    
    if is_self_harm:
        severity = "high"
        categories.append("self_harm")
        categories.append("crisis")
        notes = "Detected potential self-harm or crisis content"
    
    if is_medical:
        severity = "medium"
        categories.append("medical_advice")
        notes = "Detected medical advice request"
    
    return ClassificationVerdict(
        is_toxic=is_toxic,
        is_sensitive=is_self_harm or is_medical,
        is_off_topic=False,  # Local classifier doesn't detect off-topic well
        severity=severity,
        categories=categories,
        notes=notes,
    )


def classify_interaction(
    user_message: str,
    coach_response: str,
    conversation_context: Optional[list[ConversationMessage]] = None,
) -> ClassificationVerdict:
    """
    Call Friendli classifier to evaluate a coaching interaction.

    Args:
        user_message: The latest message from the user
        coach_response: The candidate response from the coaching agent
        conversation_context: Optional list of recent conversation messages for context

    Returns:
        ClassificationVerdict with the classification results
    """
    api_key = os.getenv("FRIENDLI_API_KEY") or os.getenv("FRIENDLI_TOKEN")
    # Support endpoint ID for dedicated endpoints (used as model parameter)
    endpoint_id = os.getenv("FRIENDLI_ENDPOINT_ID")
    model_name = endpoint_id or os.getenv("FRIENDLI_MODEL_NAME", "meta-llama-3.1-8b-instruct")
    # Support custom endpoint URL for dedicated endpoints
    custom_endpoint = os.getenv("FRIENDLI_ENDPOINT_URL")

    # Log configuration for debugging
    logger.info(f"Friendli config - Endpoint ID: {endpoint_id or 'NOT SET'}, Model: {model_name}, Custom URL: {custom_endpoint or 'NOT SET'}, API Key: {'SET' if api_key else 'NOT SET'}")

    if not api_key:
        logger.warning("FRIENDLI_API_KEY or FRIENDLI_TOKEN not set in environment, using local fallback classifier")
        return _local_fallback_classifier(user_message, coach_response)

    # Build the context string
    context_str = ""
    if conversation_context:
        context_str = "\n**Recent conversation context:**\n"
        for msg in conversation_context[-5:]:  # Last 5 messages max
            role_label = "User" if msg.role == "user" else "Coach"
            context_str += f"{role_label}: {msg.content}\n"

    # Build the prompt for classification
    user_prompt = f"""{context_str}
**Latest user message:**
{user_message}

**Candidate coach response:**
{coach_response}

Please classify this interaction according to the rubric provided in the system message.
Return ONLY valid JSON."""

    # Prepare API request
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }

    payload = {
        "model": model_name,
        "messages": [
            {"role": "system", "content": CLASSIFIER_SYSTEM_PROMPT},
            {"role": "user", "content": user_prompt},
        ],
        "max_tokens": 500,
        "temperature": 0.0,  # Deterministic for classification
    }

    try:
        # Build list of endpoints to try
        # If endpoint ID is provided, prioritize dedicated endpoint
        endpoints = []
        if custom_endpoint:
            # If custom endpoint doesn't end with /chat/completions, add it
            if custom_endpoint.endswith("/chat/completions"):
                endpoints.append(custom_endpoint)
            elif custom_endpoint.endswith("/v1"):
                endpoints.append(f"{custom_endpoint}/chat/completions")
            else:
                endpoints.append(f"{custom_endpoint.rstrip('/')}/v1/chat/completions")
        elif endpoint_id:
            # If endpoint ID is set, use dedicated endpoint base URL
            endpoints.append("https://api.friendli.ai/dedicated/v1/chat/completions")
        
        # Add standard endpoints as fallbacks
        endpoints.extend([
            "https://api.friendli.ai/dedicated/v1/chat/completions",  # Dedicated endpoint
            "https://api.friendli.ai/v1/chat/completions",
            "https://api.friendli.ai/v1/completions",
            "https://inference.friendli.ai/v1/chat/completions",
        ])
        
        last_error = None
        for endpoint in endpoints:
            try:
                logger.info(f"Trying Friendli endpoint: {endpoint} with model: {model_name}")
                response = requests.post(
                    endpoint,
                    headers=headers,
                    json=payload,
                    timeout=30,
                )
                response.raise_for_status()

                # Parse response
                result = response.json()
                
                # Check if response has the expected structure
                if "choices" not in result or not result["choices"]:
                    logger.warning(f"Unexpected response structure from {endpoint}: {result}")
                    continue  # Try next endpoint
                
                content = result["choices"][0]["message"]["content"].strip()

                # Extract JSON from the response (in case there's extra text)
                # Try to find JSON object in the content
                start_idx = content.find("{")
                end_idx = content.rfind("}") + 1

                if start_idx == -1 or end_idx == 0:
                    logger.error(f"No JSON found in Friendli response from {endpoint}. Full response: {content[:500]}")
                    continue  # Try next endpoint

                json_str = content[start_idx:end_idx]
                try:
                    classification_data = json.loads(json_str)
                except json.JSONDecodeError as e:
                    logger.error(f"Failed to parse JSON from {endpoint}. JSON string: {json_str[:500]}, Error: {e}")
                    continue  # Try next endpoint

                # Convert to ClassificationVerdict
                verdict = ClassificationVerdict.from_dict(classification_data)
                logger.info(f"Classification complete: {verdict.severity} severity")

                return verdict
            except requests.exceptions.RequestException as e:
                last_error = e
                # Log more details about the error
                if hasattr(e, 'response') and e.response is not None:
                    logger.warning(f"Endpoint {endpoint} failed: {e.response.status_code} - {e.response.text[:200]}")
                else:
                    logger.warning(f"Endpoint {endpoint} failed: {e}")
                continue  # Try next endpoint
            except (json.JSONDecodeError, KeyError, IndexError) as e:
                logger.warning(f"Endpoint {endpoint} response parsing failed: {e}")
                # Log the raw response for debugging
                try:
                    if 'response' in locals() and response is not None:
                        logger.debug(f"Raw response from {endpoint}: {response.text[:500]}")
                except:
                    pass
                continue  # Try next endpoint
        
        # All endpoints failed, raise the last error
        if last_error:
            raise last_error

    except requests.exceptions.RequestException as e:
        logger.error(f"Friendli API request failed after trying all endpoints: {e}")
        if endpoint_id:
            logger.error(f"Endpoint ID was set to: {endpoint_id}, but API calls failed")
            logger.error("Please verify:")
            logger.error("  1. FRIENDLI_ENDPOINT_ID is correct")
            logger.error("  2. FRIENDLI_API_KEY or FRIENDLI_TOKEN is valid")
            logger.error("  3. The endpoint is active and accessible")
        logger.warning("Falling back to local classifier")
        # Use local fallback classifier instead of safe default
        return _local_fallback_classifier(user_message, coach_response)

    except (json.JSONDecodeError, KeyError, IndexError) as e:
        logger.error(f"Failed to parse Friendli response: {e}")
        return ClassificationVerdict.safe_default(f"Response parsing failed: {str(e)}")

    except Exception as e:
        logger.error(f"Unexpected error in classification: {e}")
        return ClassificationVerdict.safe_default(f"Unexpected error: {str(e)}")
