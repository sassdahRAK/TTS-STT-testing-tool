# API Key Guide - How to Get API Keys for Each Provider

This guide shows you where to get API keys for each supported provider.

---

## Quick Reference Table

| Provider | Link | Free Tier |
|----------|------|-----------|
| OpenAI | https://platform.openai.com/api-keys | $5 free credit for new accounts |
| Google Cloud | https://console.cloud.google.com/apis/credentials | $300 free credit (90 days) |
| Azure Speech | https://portal.azure.com (create a Speech resource) | 5 hours free/month |
| Anthropic | https://console.anthropic.com/account/keys | No free tier (pay-as-you-go) |
| Vosk (Local) | https://alphacephei.com/vosk/models | Completely free & offline |

---

## Detailed Steps

### OpenAI (TTS + Whisper STT + Chat LLM)

1. Go to https://platform.openai.com/api-keys
2. Sign up or log in
3. Click **"Create new secret key"**
4. Copy the key (starts with `sk-...`)
5. Paste it in the API tab when adding a provider

**Covers:** TTS, STT (Whisper), and LLM in one key!

---

### Google Cloud (STT + TTS)

1. Go to https://console.cloud.google.com/apis/credentials
2. Create a new project (or select existing)
3. Enable **Speech-to-Text API** and **Text-to-Speech API**
4. Go to **Credentials** → **Create Credentials** → **Service Account**
5. Download the JSON key file
6. Set `GOOGLE_APPLICATION_CREDENTIALS` in `.env` to the file path

---

### Azure Speech (STT + TTS)

1. Go to https://portal.azure.com
2. Create a **Speech** resource
3. Go to the resource → **Keys and Endpoint**
4. Copy **Key 1**
5. Note your region (e.g., `eastus`)
6. Paste key and region in the API tab when adding a provider

---

### Anthropic Claude (LLM)

1. Go to https://console.anthropic.com/account/keys
2. Sign up or log in
3. Click **"Create Key"**
4. Copy the key (starts with `sk-ant-...`)
5. Paste it in the API tab when adding a provider

---

### Vosk (Local Offline STT)

1. Go to https://alphacephei.com/vosk/models
2. Download a model (e.g., `vosk-model-small-en-us-0.15.zip`)
3. Extract to a `models/` folder in the project
4. No API key needed - works completely offline!

---

## Tips

- You don't need all providers - start with just **OpenAI** (covers TTS + STT + LLM in one key) and **Local Vosk** (free, offline)
- Use the **Quick Templates** button in the API tab to auto-fill known providers
- The app auto-detects provider type when you paste a URL
- Custom providers are saved to `custom_providers.json` and persist between launches
