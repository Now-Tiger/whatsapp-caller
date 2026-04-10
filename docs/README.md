# WhatsApp AI Voice Agent — Complete Setup Guide

**Repository:** [github.com/Now-Tiger/whatsapp-caller](https://github.com/Now-Tiger/whatsapp-caller)  
**Version:** 0.1.0  
**Stack:** Pipecat · OpenRouter · Deepgram · WhatsApp Business API

---

## Table of Contents

1. [What This Project Does](#1-what-this-project-does)
2. [How a Call Works — User Perspective](#2-how-a-call-works--user-perspective)
3. [Architecture Overview](#3-architecture-overview)
4. [Prerequisites — Accounts & Tools](#4-prerequisites--accounts--tools)
5. [Step 1: Clone the Repository](#5-step-1-clone-the-repository)
6. [Step 2: Install Dependencies](#6-step-2-install-dependencies)
7. [Step 3: Collect Your API Keys](#7-step-3-collect-your-api-keys)
8. [Step 4: Configure Meta Developer Console](#8-step-4-configure-meta-developer-console)
9. [Step 5: Set Up Your Environment File](#9-step-5-set-up-your-environment-file)
10. [Step 6: Run Locally](#10-step-6-run-locally)
11. [Step 7: Expose to the Internet with ngrok](#11-step-7-expose-to-the-internet-with-ngrok)
12. [Step 8: Connect Meta Webhook](#12-step-8-connect-meta-webhook)
13. [Step 9: Make Your First Test Call](#13-step-9-make-your-first-test-call)
14. [Step 10: Deploy to Production (Pipecat Cloud)](#14-step-10-deploy-to-production-pipecat-cloud)
15. [Customising the Agent](#15-customising-the-agent)
16. [Environment Variable Reference](#16-environment-variable-reference)
17. [Project File Reference](#17-project-file-reference)
18. [Troubleshooting](#18-troubleshooting)

---

## 1. What This Project Does

This project turns your **WhatsApp Business phone number** into an AI voice agent. When someone calls your WhatsApp number, the call is automatically answered by an AI that:

- **Listens** to what the caller says (speech-to-text via Deepgram)
- **Thinks** about a response (LLM via OpenRouter — any model you choose)
- **Replies** in a natural voice (text-to-speech via Deepgram Aura)

The caller hears a real-time AI voice, exactly like a phone call. No apps to install on the caller's side — they just call your WhatsApp number.

---

## 2. How a Call Works — User Perspective

```
Caller opens WhatsApp → Dials your Business number
         ↓
WhatsApp rings → AI answers automatically (no hold music, no menus)
         ↓
Caller speaks  → AI listens and understands
         ↓
AI speaks back → Caller hears a natural voice response
         ↓
Conversation continues until caller hangs up
```

**From the caller's point of view:** They dial a WhatsApp number and an AI answers within 1–2 seconds, speaks in a natural voice, understands what they say, and responds conversationally.

**From the system's point of view:** WhatsApp sends the call to your server via a webhook. Your server negotiates a WebRTC audio connection, pipes the audio through Deepgram (speech-to-text) → OpenRouter LLM → Deepgram (text-to-speech), and streams the AI voice back to the caller in real time.

---

## 3. Architecture Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      WhatsApp Caller                         │
│              (any WhatsApp user, any device)                  │
└──────────────────────────┬──────────────────────────────────┘
                           │  Makes a WhatsApp call
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                   Meta's WhatsApp Cloud                      │
│    Sends SDP offer (WebRTC) to your webhook via HTTPS POST   │
└──────────────────────────┬──────────────────────────────────┘
                           │  POST /whatsapp
                           ▼
┌─────────────────────────────────────────────────────────────┐
│                  Your Bot Server (bot.py)                    │
│                                                              │
│  ┌─────────────────────────────────────────────────────┐    │
│  │            Pipecat AI Pipeline                       │    │
│  │                                                      │    │
│  │  Audio In ──► Silero VAD ──► Deepgram STT            │    │
│  │                                 │                    │    │
│  │                          Transcribed text            │    │
│  │                                 │                    │    │
│  │                         OpenRouter LLM               │    │
│  │                    (any model via OpenAI SDK)         │    │
│  │                                 │                    │    │
│  │                          Response text               │    │
│  │                                 │                    │    │
│  │                         Deepgram TTS                 │    │
│  │                                 │                    │    │
│  │                      Synthesised audio               │    │
│  │                                 │                    │    │
│  │                         Audio Out ──► Caller hears   │    │
│  └─────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────┘
```

**Component responsibilities:**

| Component | Role | Service Used |
|---|---|---|
| `SmallWebRTCTransport` | Manages the live audio channel with WhatsApp | Pipecat (built-in) |
| `SileroVADAnalyzer` | Detects when the caller starts/stops speaking | ONNX Runtime (local) |
| `DeepgramSTTService` | Converts caller speech to text | Deepgram API |
| `OpenAILLMService` | Generates the agent's response | OpenRouter API |
| `DeepgramTTSService` | Converts the response text to voice | Deepgram API |

---

## 4. Prerequisites — Accounts & Tools

Before you start, make sure you have the following. Each item links to where to sign up.

### Required Accounts

| Account | Free Tier? | Purpose |
|---|---|---|
| [Meta Developer Account](https://developers.facebook.com) | Yes | WhatsApp Business API access |
| [OpenRouter](https://openrouter.ai) | Yes (free models) | LLM inference |
| [Deepgram](https://console.deepgram.com) | Yes ($200 credit) | Speech-to-text and text-to-speech |
| [ngrok](https://ngrok.com) | Yes | Expose localhost for testing |
| [Pipecat Cloud](https://pipecat.daily.co) | Required for production | Host the deployed bot |

### Required Tools (install on your machine)

| Tool | Install Command | Purpose |
|---|---|---|
| Python 3.10–3.12 | [python.org](https://python.org) | Runtime |
| `uv` | `curl -LsSf https://astral.sh/uv/install.sh \| sh` | Dependency management |
| `ngrok` | [ngrok.com/download](https://ngrok.com/download) | Local tunnel for testing |
| Git | Pre-installed on most systems | Clone the repository |

> **macOS users:** After installing Python from python.org, run this once to fix SSL certificates:
> ```bash
> open "/Applications/Python 3.12/Install Certificates.command"
> ```

---

## 5. Step 1: Clone the Repository

```bash
git clone https://github.com/Now-Tiger/whatsapp-caller.git
cd whatsapp-caller
```

Your project directory will contain:

```
whatsapp-caller/
├── bot.py            ← Main AI voice agent (the core of the system)
├── bot_prompt.py     ← The AI's personality and instructions
├── Dockerfile        ← For production Docker deployment
├── pcc-deploy.toml   ← Pipecat Cloud deployment configuration
├── pyproject.toml    ← Python dependencies
├── env.example       ← Template for your environment variables
└── docs/             ← This documentation
```

---

## 6. Step 2: Install Dependencies

```bash
uv sync
```

This installs all Python dependencies including Pipecat, Deepgram SDK, OpenAI SDK, FastAPI, and supporting libraries. It creates a `.venv` folder in the project directory.

**Expected output (first run):**
```
Resolved 119 packages in 2.1s
Installed 119 packages in 8.3s
```

---

## 7. Step 3: Collect Your API Keys

You need four sets of credentials before proceeding. Collect them now — you will put them all into a `.env` file in Step 5.

### 7a. OpenRouter API Key (for the LLM)

1. Go to [openrouter.ai](https://openrouter.ai) and sign in
2. Navigate to **Keys** → **Create Key**
3. Copy the key — it starts with `sk-or-v1-`
4. Choose a model from [openrouter.ai/models](https://openrouter.ai/models). The default in this project is `arcee-ai/trinity-large-preview:free` (a free model). You can use any model listed there.

### 7b. Deepgram API Key (for speech-to-text and text-to-speech)

1. Go to [console.deepgram.com](https://console.deepgram.com) and sign in
2. Navigate to **API Keys** → **Create a New API Key**
3. Give it a name (e.g., "whatsapp-bot") and click **Create Key**
4. Copy the key immediately — it is only shown once

### 7c. WhatsApp / Meta Credentials (see Step 4 for full details)

You need three values from Meta's Developer Console. **Step 4 below walks you through getting all three.**

| Variable | Where to find it |
|---|---|
| `WHATSAPP_TOKEN` | Meta Developer Console → WhatsApp → API Setup → Access Token |
| `WHATSAPP_PHONE_NUMBER_ID` | Meta Developer Console → WhatsApp → API Setup → Phone Number ID |
| `WHATSAPP_APP_SECRET` | Meta Developer Console → App Settings → Basic → App Secret |

### 7d. Webhook Verification Token (you choose this)

This is a string **you make up yourself** — it can be any word or phrase. You will enter the same string in both your `.env` file and the Meta webhook settings. Example: `my-secret-token-123`

---

## 8. Step 4: Configure Meta Developer Console

> **This is the most important configuration step.** Follow it exactly. Mistakes here are the most common cause of the bot not working.

### 8a. Create a Meta App (if you don't have one)

1. Go to [developers.facebook.com](https://developers.facebook.com)
2. Click **My Apps** → **Create App**
3. Select **Other** as the use case → click **Next**
4. Select **Business** as the app type → click **Next**
5. Enter an app name (e.g., "My AI Voice Bot") and click **Create App**

### 8b. Add WhatsApp to Your App

1. In your app dashboard, find the **Add Products to Your App** section
2. Find **WhatsApp** and click **Set Up**
3. You are now on the WhatsApp setup page

### 8c. Get Your Access Token and Phone Number ID

1. In the left sidebar, click **WhatsApp** → **API Setup**
2. You will see a **Send and receive messages** section
3. Under **Step 1**, note your **Phone Number ID** — copy this value
4. Under **Step 2**, click **Generate access token** — copy this token

> **Important:** This access token expires in approximately 2 hours. For production use, create a permanent System User token by following [this guide](https://developers.facebook.com/blog/post/2022/12/05/auth-tokens/).

### 8d. Get Your App Secret

1. In the left sidebar, click **Settings** → **Basic**
2. Find the **App Secret** field — click **Show**
3. Enter your Facebook password when prompted
4. Copy the App Secret

### 8e. Enable Voice Calls on Your Phone Number

> WhatsApp voice calling for businesses is a separate feature that must be enabled.

1. In the left sidebar, click **WhatsApp** → **Configuration**
2. Find the **Phone Numbers** section and click **Manage Phone Numbers**
3. Select your phone number from the list
4. Click the **Calls** tab
5. Toggle **Allow voice calls** to **ON**
6. Click **Save**

### 8f. Set Up the Webhook

The webhook tells WhatsApp where to send call events (i.e., your bot server's address).

1. In the left sidebar, click **WhatsApp** → **Configuration**
2. Scroll down to the **Webhook** section
3. Click **Edit**
4. You will see two fields:

   **Callback URL** — Enter your server address + `/whatsapp`. During local testing this will be your ngrok URL. For now, you can leave it blank and return after Step 7:
   ```
   https://YOUR_NGROK_DOMAIN/whatsapp
   ```

   **Verify Token** — Enter the same string you chose in Step 7d (e.g., `my-secret-token-123`)

5. Click **Verify and Save**

### 8g. Subscribe to the `calls` Webhook Field

> **This step is critical. Without it, WhatsApp will not send call events to your bot.**

1. Still on the **Configuration** page, scroll to **Webhook Fields**
2. Find **calls** in the list
3. Click the toggle next to `calls` to enable it — it should turn blue/green
4. The change saves automatically

**Checkpoint:** At this point you should have:
- [x] WhatsApp added to your Meta app
- [x] Access token copied
- [x] Phone Number ID copied
- [x] App Secret copied
- [x] Voice calls enabled on your number
- [x] Webhook fields: `calls` subscribed

---

## 9. Step 5: Set Up Your Environment File

Copy the template and fill in your credentials:

```bash
cp env.example .env
```

Open `.env` in a text editor and fill in every value:

```bash
# ── LLM via OpenRouter ────────────────────────────────────────────
OPENROUTER_API_KEY=sk-or-v1-YOUR_KEY_HERE
OPENROUTER_BASE_URL=https://openrouter.ai/api/v1
OPENROUTER_LLM_MODEL=arcee-ai/trinity-large-preview:free

# ── Speech (Deepgram) ─────────────────────────────────────────────
DEEPGRAM_API_KEY=YOUR_DEEPGRAM_KEY_HERE

# ── WhatsApp / Meta ───────────────────────────────────────────────
WHATSAPP_TOKEN=YOUR_ACCESS_TOKEN_FROM_META
WHATSAPP_PHONE_NUMBER_ID=YOUR_PHONE_NUMBER_ID_FROM_META
WHATSAPP_APP_SECRET=YOUR_APP_SECRET_FROM_META

# ── Local development only ────────────────────────────────────────
WHATSAPP_WEBHOOK_VERIFICATION_TOKEN=my-secret-token-123
```

> **Security:** Never commit `.env` to version control. It is already listed in `.gitignore`.

---

## 10. Step 6: Run Locally

Start the bot server:

```bash
uv run bot.py
```

You will see output like this:

```
INFO   Pipecat 0.0.108 ...
INFO   Bot ready! (WhatsApp)
INFO   → Open http://localhost:7860/client in your browser
```

The server is now running on **port 7860**. It is listening for webhook events from WhatsApp.

> **Keep this terminal window open.** You need the server running for the next steps.

---

## 11. Step 7: Expose to the Internet with ngrok

WhatsApp needs to reach your server from the internet. ngrok creates a secure tunnel from a public URL to your localhost.

Open a **new terminal window** (keep the bot running in the first one) and run:

```bash
ngrok http 7860
```

ngrok will display output like this:

```
Forwarding   https://abc123.ngrok-free.app -> http://localhost:7860
```

Copy the `https://` URL shown (e.g., `https://abc123.ngrok-free.app`).

Your webhook URL is this URL with `/whatsapp` appended:
```
https://abc123.ngrok-free.app/whatsapp
```

> **If you have a paid ngrok plan**, you can use a static domain:
> ```bash
> ngrok http --domain=your-static-domain.ngrok.io 7860
> ```

---

## 12. Step 8: Connect Meta Webhook

Now update the Meta Developer Console with your ngrok URL.

1. Go to [developers.facebook.com](https://developers.facebook.com) → Your App → **WhatsApp** → **Configuration**
2. In the **Webhook** section, click **Edit**
3. Set **Callback URL** to:
   ```
   https://YOUR-NGROK-URL.ngrok-free.app/whatsapp
   ```
4. Set **Verify Token** to the same value as `WHATSAPP_WEBHOOK_VERIFICATION_TOKEN` in your `.env`
5. Click **Verify and Save**

**What happens during verification:** Meta sends a GET request to your `/whatsapp` endpoint with a challenge string. Your bot responds with the challenge, proving the server is under your control. You should see in your bot terminal:
```
INFO   Webhook verification successful
```

If verification fails, double-check that:
- Your ngrok tunnel is running
- The Verify Token matches exactly (case-sensitive)
- The URL ends with `/whatsapp` (not `/whatsapp/`)

---

## 13. Step 9: Make Your First Test Call

1. Open WhatsApp on your phone
2. Find your WhatsApp Business number (the one registered in Meta Developer Console)
3. Make a **voice call** to that number

**Expected experience:**
- The call connects within 1–3 seconds
- The AI greets you immediately
- You can speak and the AI responds naturally
- The AI understands context across the conversation

**Expected logs in your terminal:**
```
DEBUG  Processing WhatsApp webhook: {...}
DEBUG  Webhook signature verified!
DEBUG  Processing connect event for call wacid...
DEBUG  SDP answer generated
DEBUG  Pre-accept successful
DEBUG  Accept successful
INFO   bot() invoked — starting run_bot
INFO   Starting bot | LLM model=arcee-ai/...
INFO   Pipeline ready — waiting for WebRTC connection
INFO   WhatsApp call connected
INFO   Greeting context frame queued for call
```

---

## 14. Step 10: Deploy to Production (Pipecat Cloud)

Local development uses ngrok which is temporary. For a permanent, always-on deployment use Pipecat Cloud.

### Prerequisites for Production Deployment

- A [Docker Hub](https://hub.docker.com) account (free)
- Docker installed on your machine
- A [Pipecat Cloud](https://pipecat.daily.co) account

### 14a. Update pcc-deploy.toml

Open `pcc-deploy.toml` and replace `YOUR_DOCKERHUB_USERNAME` with your actual Docker Hub username:

```toml
agent_name = "whatsapp-voice-agent"
image = "yourdockerhubusername/whatsapp-voice-agent:0.1"
secret_set = "whatsapp-secrets"

[scaling]
min_agents = 1
```

### 14b. Deploy

Run these four commands in order:

```bash
# 1. Log in to Pipecat Cloud
uv run pcc auth login

# 2. Upload your secrets securely
uv run pcc secrets set whatsapp-secrets --file .env

# 3. Build and push Docker image to Docker Hub
uv run pcc docker build-push

# 4. Deploy the agent
uv run pcc deploy
```

### 14c. Update Meta Webhook for Production

After deployment, Pipecat Cloud gives you a permanent webhook URL. Find it in your Pipecat Cloud dashboard, or it follows this pattern:

```
https://api.pipecat.daily.co/v1/public/webhooks/YOUR_ORG_NAME/whatsapp-voice-agent/whatsapp
```

1. Go to Meta Developer Console → WhatsApp → Configuration → Webhook
2. Update **Callback URL** to the Pipecat Cloud URL above
3. Update **Verify Token** to your **Pipecat Cloud public API key** (found in your Pipecat Cloud dashboard — this is different from the local `WHATSAPP_WEBHOOK_VERIFICATION_TOKEN`)
4. Click **Verify and Save**

> **Important:** The production Verify Token must be your Pipecat Cloud public API key, not the string you used for local testing.

---

## 15. Customising the Agent

### Change the AI's Personality

Edit `bot_prompt.py`:

```python
BOT_SYSTEM_PROMPT = """
You are a helpful customer service agent for Acme Corp.
You assist customers with order tracking and product questions.
Keep responses to 1-2 sentences. Always be professional and polite.
"""
```

### Change the LLM Model

Update `OPENROUTER_LLM_MODEL` in your `.env` file. Browse available models at [openrouter.ai/models](https://openrouter.ai/models).

```bash
# Examples:
OPENROUTER_LLM_MODEL=openai/gpt-4o-mini
OPENROUTER_LLM_MODEL=anthropic/claude-3-haiku
OPENROUTER_LLM_MODEL=meta-llama/llama-3.1-8b-instruct:free
```

### Change the Voice

Edit the `voice` setting in `bot.py`:

```python
tts = DeepgramTTSService(
    api_key=os.environ["DEEPGRAM_API_KEY"],
    settings=DeepgramTTSService.Settings(voice="aura-2-zeus-en"),  # male voice
)
```

Available voices: `aura-2-helena-en` (female), `aura-2-zeus-en` (male), `aura-2-luna-en` (female), and more at [deepgram.com/docs](https://developers.deepgram.com/docs/tts-models).

---

## 16. Environment Variable Reference

| Variable | Required | Description |
|---|---|---|
| `OPENROUTER_API_KEY` | Yes | Your OpenRouter API key |
| `OPENROUTER_BASE_URL` | Yes | Always `https://openrouter.ai/api/v1` |
| `OPENROUTER_LLM_MODEL` | Yes | Model identifier from OpenRouter |
| `DEEPGRAM_API_KEY` | Yes | Your Deepgram API key (used for both STT and TTS) |
| `WHATSAPP_TOKEN` | Yes | Access token from Meta Developer Console |
| `WHATSAPP_PHONE_NUMBER_ID` | Yes | Phone Number ID from Meta Developer Console |
| `WHATSAPP_APP_SECRET` | Yes | App Secret from Meta Developer Console |
| `WHATSAPP_WEBHOOK_VERIFICATION_TOKEN` | Local dev only | Any string you choose; must match Meta webhook config |

---

## 17. Project File Reference

| File | Purpose |
|---|---|
| `bot.py` | Core application. Builds the Pipecat AI pipeline, handles WebRTC, manages call lifecycle |
| `bot_prompt.py` | System prompt defining the AI agent's personality and behaviour |
| `pyproject.toml` | Python dependency manifest. Run `uv sync` after any changes |
| `Dockerfile` | Container image for production deployment |
| `pcc-deploy.toml` | Pipecat Cloud deployment configuration (agent name, Docker image, scaling) |
| `env.example` | Template showing required environment variables. Copy to `.env` and fill in |
| `.env` | Your actual secrets. Never commit this file |
| `docs/README.md` | This document |

---

## 18. Troubleshooting

### Webhook verification fails (GET /whatsapp returns 403)

**Cause:** The Verify Token in Meta does not match `WHATSAPP_WEBHOOK_VERIFICATION_TOKEN` in `.env`.

**Fix:** Make sure both values are identical, including capitalisation and spaces. Restart the bot after changing `.env`.

---

### Bot does not answer calls (no logs appear when calling)

**Cause:** The `calls` webhook field is not subscribed.

**Fix:** Meta Developer Console → WhatsApp → Configuration → Webhook Fields → find **calls** → toggle it on.

---

### `Error validating access token` in logs

**Cause:** The `WHATSAPP_TOKEN` expires after approximately 2 hours.

**Fix:** Go to Meta Developer Console → WhatsApp → API Setup → generate a new token → update `.env` → restart the bot. For production, use a permanent System User token.

---

### Call connects but no audio (silent call)

**Cause:** Usually a missing or invalid `DEEPGRAM_API_KEY`.

**Fix:** Verify the key is correct in `.env`. Test it at [console.deepgram.com](https://console.deepgram.com).

---

### `SSLCertVerificationError` connecting to graph.facebook.com

**Cause:** macOS Python does not use system certificates by default.

**Fix:** Run this once:
```bash
open "/Applications/Python 3.12/Install Certificates.command"
```

---

### POST /whatsapp returns 404

**Cause:** The bot was started without the `--whatsapp` flag.

**Fix:** Always use `uv run bot.py` — the required flags are now injected automatically. Do not pass conflicting transport flags.

---

### Call connects but bot crashes immediately

**Cause:** A missing or mistyped environment variable.

**Fix:** Check your `.env` file contains all 7 required variables with no empty values. Look at the bot logs for a line like `Starting bot | LLM model=NOT SET` to identify which variable is missing.

---

## Additional Resources

- [Pipecat Documentation](https://docs.pipecat.ai)
- [WhatsApp Business API Docs](https://developers.facebook.com/docs/whatsapp)
- [OpenRouter Models](https://openrouter.ai/models)
- [Deepgram TTS Voice Models](https://developers.deepgram.com/docs/tts-models)
- [Meta Permanent System User Token Guide](https://developers.facebook.com/blog/post/2022/12/05/auth-tokens/)
