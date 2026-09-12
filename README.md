# Model Tester Tool

A PyQt6 desktop application for testing and comparing TTS, STT, and LLM API models before integrating them into your production system. Optimised for macOS with full support for Khmer and multilingual datasets.

---

## Features

### 🔊 TTS Testing
- **OpenAI TTS** — alloy, echo, fable, onyx, nova, shimmer
- **Google Cloud TTS** — Neural2 voices
- **Azure TTS** — Neural voices
- **Local pyttsx3** — offline, no key needed
- **Microsoft Edge TTS** — 50+ free voices including Khmer (`km-KH-PisethNeural`, `km-KH-SreymomNeural`)
- **Meta MMS TTS** (`facebook/mms-tts-khm`) — offline Khmer & multilingual TTS, no key needed
- **Deepgram Aura TTS** — `aura-asteria-en` and more
- **Any custom endpoint** — add via API tab

### 🎤 STT Testing
- **OpenAI Whisper** — `whisper-1`
- **Google Cloud STT** — `latest_long`, `latest_short`
- **Azure STT** — conversation, dictation
- **Local Vosk** — fully offline
- **Meta MMS STT** (`facebook/mms-300m`) — offline 1000+ language STT with per-language adapters, including Khmer
- **Deepgram STT** — `nova-2`, `base`
- **Any custom endpoint** — add via API tab
- Record from microphone or upload audio files
- CER / WER accuracy scoring (NeMo or fallback)
- **Batch testing** — test entire folders of audio files with TSV/CSV/JSON reference text

### 🤖 LLM API Testing
- **OpenAI GPT** — gpt-4o, gpt-4o-mini, gpt-3.5-turbo
- **Anthropic Claude** — claude-3-5-sonnet, claude-3-haiku
- **Any OpenAI-compatible endpoint** — Groq, OpenRouter, Together AI, etc.
- Send the same prompt to all providers simultaneously
- Configurable temperature and max tokens

### 📊 Compare & Rank
- Live results table — updates automatically as tests complete
- Filter by TTS / STT / LLM
- Manual 1–5 star ratings with notes
- Automatic ranking by average accuracy / score
- **Refresh button** to reload results at any time
- Export to JSON, CSV, or summary report

---

## Quick Start

### 1. Clone & set up virtual environment

```bash
git clone https://github.com/sassdahRAK/TTS-STT-testing-tool.git
cd TTS-STT-testing-tool
python3 -m venv .venv
source .venv/bin/activate
```

### 2. Install dependencies

```bash
pip install -r requirements.txt
```

> **Meta MMS models** (TTS + STT) download automatically from HuggingFace on first use:
> - MMS TTS Khmer: ~130 MB (`facebook/mms-tts-khm`)
> - MMS STT 300M: ~1.2 GB (`facebook/mms-300m`)
>
> After first download everything runs fully offline.

### 3. Configure API keys (optional)

```bash
cp .env.example .env
```

Edit `.env` — only fill in the providers you want to test:

```env
# OpenAI (Whisper STT + TTS)
OPENAI_API_KEY=sk-your-key-here

# Google Cloud (STT + TTS)
GOOGLE_APPLICATION_CREDENTIALS=path/to/google-credentials.json

# Azure Cognitive Services
AZURE_SPEECH_KEY=your-azure-key
AZURE_SPEECH_REGION=eastus

# Anthropic Claude
ANTHROPIC_API_KEY=sk-ant-your-key-here
```

> You don't need to fill in all keys. Providers with missing keys are automatically disabled.  
> **Edge TTS and Meta MMS work with zero configuration.**

### 4. Run

```bash
source .venv/bin/activate   # always activate .venv, not enev
python main.py
```

---

## Adding Custom Providers (Deepgram, ElevenLabs, Groq, etc.)

Go to the **API tab** → click **+ Add New Provider** → paste your endpoint URL.  
The app auto-detects the provider type and correct request format.

| Provider | Type | Endpoint |
|---|---|---|
| Deepgram TTS | TTS | `https://api.deepgram.com/v1/speak` |
| Deepgram STT | STT | `https://api.deepgram.com/v1/listen` |
| ElevenLabs | TTS | `https://api.elevenlabs.io/v1/text-to-speech/{voice_id}` |
| Groq | LLM | `https://api.groq.com/openai/v1/chat/completions` |
| OpenRouter | LLM | `https://openrouter.ai/api/v1/chat/completions` |
| Together AI | LLM | `https://api.together.xyz/v1/chat/completions` |

> **Deepgram auth:** uses `Token <key>` not `Bearer <key>` — the app handles this automatically.

---

## Batch STT Testing with Khmer Dataset

The STT tab includes a **Batch Testing** section designed for large dataset evaluation.

### Workflow

1. Click **Add Folder** → select your `wavs/` folder (supports `.wav .mp3 .flac .ogg .m4a .wma`)
2. Click **Load References (CSV/JSON)** → select your `line_index.tsv`
3. The app matches audio files to reference text **by filename stem** automatically
4. Select providers (e.g. Meta MMS STT, Deepgram) → click **▶ Run Batch Test**

### TSV format (compatible with `line_index.tsv`)

```
khm_0308_0011865648	ស្ពាន កំពង់ ចម្លង អ្នកលឿង នៅ ព្រៃវែង
khm_0308_0032157149	ភ្លើង កំពុង ឆាប ឆេះ ផ្ទះ ប្រជា ពលរដ្ឋ
```

Format: `filename<TAB>(optional)<TAB>reference_text` — no header row needed.

---

## Project Structure

```
TTS-STT-testing-tool/
├── main.py               # App entry point, global stylesheet, MainWindow
├── config.py             # API credentials loaded from .env
├── ui_components.py      # Shared Card widget, responsive margin constants
│
├── tts_tab.py            # TTS testing UI — test cases, run, results, play
├── stt_tab.py            # STT testing UI — mic/file input, scoring, batch
├── llm_tab.py            # LLM testing UI — prompt, responses per model
├── comparison_tab.py     # Compare & Rank — table, ratings, export
├── api_tab.py            # Custom provider manager — add/edit/remove
│
├── tts_providers.py      # Built-in TTS: OpenAI, Google, Azure, Local, MMS
├── stt_providers.py      # Built-in STT: Whisper, Google, Azure, Vosk, MMS
├── llm_providers.py      # Built-in LLM: OpenAI, Anthropic, Custom
├── mms_providers.py      # Meta MMS TTS + STT (offline, HuggingFace)
├── dynamic_providers.py  # Custom provider runtime management + API callers
├── edge_tts_provider.py  # Microsoft Edge TTS (free, no key)
│
├── audio_recorder.py     # Microphone recording via sounddevice
├── batch_testing.py      # Batch STT widget — folder/TSV import, progress
├── nemo_scoring.py       # CER/WER scoring (NeMo or fallback)
├── add_provider_dialog.py # Add/Edit provider dialogs
│
├── requirements.txt      # Python dependencies
├── custom_providers.json # Saved custom providers (auto-managed)
├── tts_test_cases.json   # Saved TTS test cases (auto-managed)
├── dataset/              # Audio dataset + line_index.tsv
└── output/               # Generated TTS audio files
```

---

## Provider Reference

| Provider | Type | Key Required | Offline | Notes |
|---|---|---|---|---|
| OpenAI TTS | TTS | ✅ | ❌ | `tts-1` model |
| Google Cloud TTS | TTS | ✅ | ❌ | Neural2 voices |
| Azure TTS | TTS | ✅ | ❌ | Neural voices |
| Local pyttsx3 | TTS | ❌ | ✅ | System voices |
| Edge TTS | TTS | ❌ | ❌ | Free, 50+ voices incl. Khmer |
| **Meta MMS TTS** | TTS | ❌ | ✅ | Khmer + 1000 langs, downloads once |
| Deepgram Aura | TTS | ✅ | ❌ | Fast neural TTS |
| OpenAI Whisper | STT | ✅ | ❌ | `whisper-1` |
| Google Cloud STT | STT | ✅ | ❌ | |
| Azure STT | STT | ✅ | ❌ | |
| Local Vosk | STT | ❌ | ✅ | Needs model download |
| **Meta MMS STT** | STT | ❌ | ✅ | 1000+ langs incl. Khmer, downloads once |
| Deepgram STT | STT | ✅ | ❌ | `nova-2`, fast + accurate |
| OpenAI GPT | LLM | ✅ | ❌ | gpt-4o, gpt-4o-mini |
| Anthropic Claude | LLM | ✅ | ❌ | claude-3-5-sonnet |
| Groq / OpenRouter | LLM | ✅ | ❌ | Add via API tab |

---

## Requirements

- Python 3.12+
- macOS (primary), Windows, Linux
- ~2 GB disk space if using Meta MMS STT

### Key packages

```
PyQt6>=6.6.0          # GUI framework
transformers>=4.40.0  # Meta MMS models
torch>=2.1.0          # Model inference
edge-tts>=6.1.0       # Microsoft Edge TTS
httpx>=0.27.0         # Custom API calls
sounddevice>=0.4.6    # Microphone recording
scipy>=1.11.0         # Audio processing for MMS
```

---

## Known Issues & Notes

- **Always use `.venv`** to run the app — not `enev` or system Python:
  ```bash
  source .venv/bin/activate
  python main.py
  ```
- **OneDrive audio files** — if files show a ☁️ icon, right-click → "Download Now" before importing
- **Meta MMS first run** is slow (model download) — subsequent runs load from cache instantly
- **Deepgram** requires `Token <key>` auth (not `Bearer`) — handled automatically
- NeMo scoring falls back to a built-in CER/WER calculator if `nemo-toolkit` is not installed
