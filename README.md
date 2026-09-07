# Model Tester Tool

A PyQt6 desktop application for testing and comparing TTS, STT, and LLM API models before integrating them into your production system.

## Features

### TTS Testing
- Test text-to-speech across **OpenAI TTS**, **Google Cloud TTS**, **Azure TTS**, and **Local pyttsx3**
- Compare synthesis speed and output quality
- Play audio directly in the app
- Multiple voice options per provider

### STT Testing
- Test speech-to-text across **OpenAI Whisper**, **Google Cloud STT**, **Azure STT**, and **Local Vosk**
- Record from microphone or upload audio files
- Compare transcription accuracy and speed
- Multi-language support

### LLM API Testing
- Test **OpenAI GPT**, **Anthropic Claude**, and **custom/self-hosted** models
- Send the same prompt to all providers simultaneously
- Compare response quality, speed, and token usage
- Configurable temperature and max tokens

### Comparison & Ranking
- Side-by-side result comparison
- Rate each model 1-5 stars with notes
- Automatic ranking by average score
- Export results to JSON for analysis

## Quick Start

### 1. Install Dependencies

```bash
pip install -r requirements.txt
```

### 2. Configure API Keys

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# OpenAI (Whisper STT + OpenAI TTS)
OPENAI_API_KEY=sk-your-key-here

# Google Cloud (STT + TTS)
GOOGLE_APPLICATION_CREDENTIALS=path/to/google-credentials.json

# Azure Cognitive Services (Speech)
AZURE_SPEECH_KEY=your-azure-key
AZURE_SPEECH_REGION=eastus

# Anthropic (Claude)
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Custom API (OpenAI-compatible endpoint)
CUSTOM_API_URL=https://your-api.com/v1/chat
CUSTOM_API_KEY=your-custom-key
```

### 3. Run

```bash
python main.py
```

## Project Structure

```
model_tester_tool/
├── main.py              # Application entry point
├── config.py            # Configuration management
├── tts_providers.py     # TTS provider implementations
├── stt_providers.py     # STT provider implementations
├── llm_providers.py     # LLM provider implementations
├── tts_tab.py           # TTS testing UI tab
├── stt_tab.py           # STT testing UI tab
├── llm_tab.py           # LLM testing UI tab
├── comparison_tab.py    # Results comparison tab
├── audio_recorder.py    # Microphone recording utility
├── requirements.txt     # Python dependencies
├── .env.example         # Example configuration
└── output/             # Generated audio files
```

## Provider Setup

| Provider | What You Need |
|----------|--------------|
| OpenAI | API key from [platform.openai.com](https://platform.openai.com) |
| Google Cloud | Service account JSON from [console.cloud.google.com](https://console.cloud.google.com) |
| Azure | Speech resource key from [portal.azure.com](https://portal.azure.com) |
| Anthropic | API key from [console.anthropic.com](https://console.anthropic.com) |
| Local Vosk | Download model from [alphacephei.com/vosk/models](https://alphacephei.com/vosk/models) |

## Tips

- You don't configure all providers — only fill in the ones you want to test
- Local providers (pyttsx3, Vosk) work without API keys
- Use the "Compare & Rank" tab to score models and track your evaluations
- Export results to JSON for sharing with your team
