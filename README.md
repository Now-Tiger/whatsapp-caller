# WhatsApp Voice Agent (Pipecat)

A real-time AI voice agent that automatically answers incoming WhatsApp Business calls. Built with [Pipecat](https://pipecat.ai), OpenRouter (LLM), and Deepgram (STT + TTS).

## Stack

- **Transport**: SmallWebRTC (Pipecat) — WebRTC SDP handshake with Meta's WhatsApp Calling API
- **VAD**: Silero — detects when the user starts and stops speaking
- **STT**: Deepgram — speech to text
- **LLM**: OpenRouter via OpenAI SDK — any model available on OpenRouter
- **TTS**: Deepgram Aura — text to speech
- **Deploy**: Pipecat Cloud

## Project Structure

```
├── bot.py               # Pipecat pipeline — the AI voice agent
├── bot_prompt.py        # System prompt for the AI agent
├── Dockerfile           # Container build
├── pcc-deploy.toml      # Pipecat Cloud deployment config
├── pyproject.toml       # Python dependencies (uv)
├── env.example          # Template of required environment variables
└── .env                 # Local secrets — never commit this
```

## Setup

### 1. Copy and fill environment variables

```bash
cp env.example .env
# Edit .env and fill in all values
```

### 2. Install dependencies

```bash
uv sync
```

### 3. Meta Developer Console (one-time)

- Enable voice calls: WhatsApp → Configuration → Phone Numbers → select number → Calls tab → Enable
- Subscribe webhook to `calls` field: WhatsApp → Configuration → Webhooks → enable `calls`

## Local Development

```bash
# Start the bot
uv run bot.py
# Opens at http://localhost:7860

# Expose to the internet (requires ngrok)
ngrok http --domain=YOUR_NGROK_DOMAIN http://localhost:7860

# Set webhook in Meta Developer Console:
# https://YOUR_NGROK_DOMAIN/whatsapp
```

## Production Deployment (Pipecat Cloud)

```bash
# 1. Authenticate
uv run pcc auth login

# 2. Upload secrets
uv run pcc secrets set whatsapp-secrets --file .env

# 3. Build and push Docker image
#    First update pcc-deploy.toml with your Docker Hub username
uv run pcc docker build-push

# 4. Deploy
uv run pcc deploy
```

After deploy, update the Meta webhook URL to:
```
https://api.pipecat.daily.co/v1/public/webhooks/YOUR_ORGANIZATION_NAME/whatsapp-voice-agent/whatsapp
```

Use your **Pipecat Cloud public API key** as the Verify Token in Meta (not the local `WHATSAPP_WEBHOOK_VERIFICATION_TOKEN`).

## Troubleshooting

| Symptom | Fix |
|---|---|
| Webhook verification fails | Local: check `WHATSAPP_WEBHOOK_VERIFICATION_TOKEN` matches Meta. Production: use Pipecat Cloud public API key |
| Bot doesn't answer calls | Enable `calls` webhook field in Meta Console |
| `Error validating access token` | Regenerate token in WhatsApp → API Setup, update `.env` |
| Call connects but no audio | Check `audio_in_enabled` and `audio_out_enabled` are both `True` in `TransportParams` |
| Bot answers but crashes | Check all env vars are set in Pipecat Cloud secrets |

> **Note:** The `WHATSAPP_TOKEN` from Meta expires in ~2 hours. For production, create a permanent System User token.
