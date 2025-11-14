# Guardian: Toxicity + Off-topic Monitoring for Coaching Agents

A lightweight, composable wrapper that adds safety monitoring and observability to AI coaching agents. Guardian detects toxic content, sensitive topics, and off-topic drift, logging everything to Comet Opik for analysis.

## Overview

Guardian provides:

1. **Classification**: Uses Friendli AI to detect:
   - Toxic or abusive content
   - Self-harm or crisis situations
   - Highly sensitive topics
   - Off-topic drift from coaching goals

2. **Observability**: Logs all interactions to Comet Opik for:
   - Identifying when coaches go off-track
   - Understanding problematic patterns
   - Iterating on prompts and safety policies

3. **Safety**: Optional blocking of problematic responses (configurable)

## Quick Start

### 1. Installation

```bash
# Clone or download this repository
cd coach-guardian

# Install dependencies
pip install -r requirements.txt
```

### 2. Configuration

Copy the example environment file and add your API keys:

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# Friendli AI (https://friendli.ai)
FRIENDLI_API_KEY=your_friendli_api_key_here
# Or use FRIENDLI_TOKEN for dedicated endpoints
# FRIENDLI_TOKEN=your_friendli_token_here

# For dedicated endpoints, use your endpoint ID as the model
FRIENDLI_ENDPOINT_ID=your_endpoint_id_here
# Or specify model name for standard endpoints
# FRIENDLI_MODEL_NAME=meta-llama-3.1-8b-instruct

# Optional: Custom endpoint URL (if different from standard dedicated endpoint)
# FRIENDLI_ENDPOINT_URL=https://api.friendli.ai/dedicated/v1/chat/completions

# Comet Opik (https://www.comet.com/site/products/opik/)
OPIK_API_KEY=your_opik_api_key_here
OPIK_PROJECT_NAME=coaching-guardian
OPIK_WORKSPACE_NAME=your_workspace_name

# Guardian Configuration
# Optional: Enable/disable response blocking (default: true - blocking enabled)
# Set to "false", "0", "no", or "off" to disable blocking
GUARDIAN_ENFORCE_BLOCKING=true
```

### 3. Run the Demo

```bash
python demo_guardian_verbose.py
```

The demo provides an interactive CLI where you can:
- Chat with a mock coaching agent
- See Guardian classifications in real-time
- Toggle response blocking on/off
- View logs in Comet Opik

## Usage in Your Application

### Basic Integration

```python
from guardian import Guardian
from models import ConversationMessage, GuardianConfig

# Your existing coaching function
def my_coaching_agent(conversation_history: list[ConversationMessage]) -> str:
    # Your LLM call or coaching logic here
    return "Your coaching response"

# Wrap with Guardian
guardian = Guardian(
    coach_fn=my_coaching_agent,
    config=GuardianConfig(
        enforce_blocking=False,  # Monitor only (v0)
        log_to_opik=True,
        log_unflagged=True,
    )
)

# Use in your app
conversation = [
    ConversationMessage(role="user", content="I feel stuck in my career"),
]

response = guardian.generate_guarded_response(conversation)
```

### With Dictionary Format

If you're working with dictionaries instead of `ConversationMessage` objects:

```python
conversation = [
    {"role": "user", "content": "I feel stuck in my career"},
    {"role": "assistant", "content": "Tell me more about that."},
]

response = guardian.generate_guarded_response_dict(conversation)
```

## Configuration Options

### GuardianConfig

```python
from models import GuardianConfig

config = GuardianConfig(
    # Enable/disable response blocking (default: True - blocking enabled for safety)
    enforce_blocking=True,

    # Log to Comet Opik (default: True)
    log_to_opik=True,

    # Log even non-flagged interactions (default: True)
    log_unflagged=True,

    # Max number of messages to send as context (default: 5)
    max_context_messages=5,

    # Fallback message when blocking (customizable)
    safe_fallback_message="I'm not able to continue with this direction..."
)
```

## Architecture

### Project Structure

```
hackersquad/
├── guardian.py              # Core Guardian class
├── friendli_client.py       # Friendli AI classifier wrapper
├── opik_client.py           # Comet Opik logging wrapper
├── models.py                # Data models
├── demo_guardian.py         # Interactive demo
├── requirements.txt         # Python dependencies
├── .env.example            # Environment template
├── context.md              # Project specification
└── README.md               # This file
```

### Data Flow

1. **User message arrives** → Your app calls `guardian.generate_guarded_response()`
2. **Coach generates response** → Guardian calls your coaching function
3. **Classification** → Guardian sends to Friendli for analysis
4. **Logging** → Interaction and verdict logged to Opik
5. **Decision** → Response returned (blocked if configured and problematic)

### Classification Schema

Friendli returns a structured verdict:

```json
{
  "is_toxic": false,
  "is_sensitive": false,
  "is_off_topic": true,
  "severity": "low",
  "categories": ["off_topic_chatter"],
  "notes": "Conversation drifting into casual chat"
}
```

**Severity levels:**
- `none`: No issues detected
- `low`: Minor concerns, worth noting
- `medium`: Moderate concerns, potentially problematic
- `high`: Serious concerns, should likely be blocked

**Categories:**
- `harassment`: Abusive or harassing language
- `hate_speech`: Hateful content
- `self_harm`: Content about self-harm or suicide
- `medical_advice`: Inappropriate medical guidance
- `off_topic_chatter`: Drift from coaching goals
- `inappropriate_request`: Out-of-scope requests
- `crisis`: User appears to be in crisis
- `other`: Other concerns

## Observability with Opik

All interactions are logged to Comet Opik, allowing you to:

- **Filter** conversations by toxicity, sensitivity, or off-topic flags
- **Analyze** patterns in problematic interactions
- **Track** how often the coach drifts off-topic
- **Inspect** specific conversations with issues
- **Iterate** on prompts and safety policies

### Viewing Logs

1. Go to [Comet Opik](https://www.comet.com/site/products/opik/)
2. Navigate to your project (default: `coaching-guardian`)
3. Filter by tags:
   - `severity:high`
   - `toxic:true`
   - `off_topic:true`
   - `category:self_harm`

## Future Extensions (Post-v0)

- **Active blocking/rewriting**: Automatically replace risky responses
- **User-level risk tracking**: Monitor repeated flags for same user
- **Persona stability monitoring**: Detect tone drift from intended persona
- **Custom classification rules**: Define your own safety policies
- **Multi-language support**: Extend beyond English
- **Multimodal analysis**: Support images, audio, etc.

## Development

### Running Tests

```bash
# Install dev dependencies
pip install pytest mypy

# Run tests (when implemented)
pytest

# Type checking
mypy guardian.py friendli_client.py opik_client.py
```

### Extending the Guardian

To add custom classification logic:

1. Modify `CLASSIFIER_SYSTEM_PROMPT` in `friendli_client.py`
2. Add new fields to `ClassificationVerdict` in `models.py`
3. Update blocking logic in `guardian.py`

## Troubleshooting

### Classification always returns safe verdict

- Check that `FRIENDLI_API_KEY` is set correctly
- Verify your Friendli account has API access
- Check logs for API errors

### Nothing appears in Opik

- Verify `OPIK_API_KEY` is set correctly
- Check that `log_to_opik=True` in config
- Ensure the Opik package is installed: `pip install opik`

### Import errors

- Make sure all dependencies are installed: `pip install -r requirements.txt`
- Verify you're using Python 3.8+

## License

This project is provided as-is for demonstration and integration purposes.

## Support

For issues or questions:
1. Check the documentation in `context.md`
2. Review the code comments in each module
3. Test with `demo_guardian.py` to isolate issues

## Credits

Built with:
- [Friendli AI](https://friendli.ai) - LLM inference and classification
- [Comet Opik](https://www.comet.com/site/products/opik/) - Observability and analytics
