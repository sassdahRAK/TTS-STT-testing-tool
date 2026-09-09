# Model Tester Tool — Complete System Documentation

> A PyQt6 desktop application for testing and comparing TTS, STT, and LLM API models before integrating them into production systems.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [System Architecture](#2-system-architecture)
3. [Project Structure](#3-project-structure)
4. [Data Flow & Process](#4-data-flow--process)
5. [Installation & Setup](#5-installation--setup)
6. [Usage Guide](#6-usage-guide)
7. [Provider Types](#7-provider-types)
8. [Scoring System](#8-scoring-system)
9. [Custom Providers](#9-custom-providers)
10. [Output & Export](#10-output--export)

---

## 1. System Overview

The **Model Tester Tool** is a desktop application that allows developers and AI teams to:

- **Test TTS (Text-to-Speech)** — Compare voice synthesis quality and speed across providers
- **Test STT (Speech-to-Text)** — Measure transcription accuracy with CER/WER metrics
- **Test LLM APIs** — Send the same prompt to multiple models and compare responses
- **Compare & Rank** — Side-by-side result comparison with star ratings and export

### Key Features

| Feature | Description |
|---------|-------------|
| Multi-Provider | Test OpenAI, Google Cloud, Azure, Anthropic, and local models |
| Auto-Scoring | NVIDIA NeMo-powered CER/WER metrics for STT accuracy |
| Batch Testing | Test multiple audio files across all STT providers at once |
| Custom Providers | Add any API endpoint (Deepgram, Groq, OpenRouter, etc.) |
| Free TTS | Edge TTS (Microsoft) requires no API key |
| Export | JSON, CSV, and summary report export |
| Modern UI | Dashboard-style PyQt6 interface with full-page scrolling |

---

## 2. System Architecture

### High-Level Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│                     Model Tester Tool (PyQt6)                   │
├─────────────────────────────────────────────────────────────────┤
│                                                                 │
│  ┌──────────┐  ┌──────────┐  ┌──────────┐  ┌──────────────┐   │
│  │  API Tab │  │  TTS Tab │  │  STT Tab │  │ Compare Tab  │   │
│  │          │  │          │  │          │  │              │   │
│  │ Provider │  │  Test    │  │  Audio   │  │  Results     │   │
│  │ Manager  │  │  Cases   │  │  Input   │  │  Table       │   │
│  └────┬─────┘  └────┬─────┘  └────┬─────┘  │  Rankings    │   │
│       │              │              │        │  Ratings     │   │
│       ▼              ▼              ▼        └──────▲───────┘   │
│  ┌─────────────────────────────────────────┐     │           │
│  │         Provider Manager Layer          │     │           │
│  ├─────────────────────────────────────────┤     │           │
│  │  Built-in Providers  │  Custom/Dynamic  │     │           │
│  │  ─────────────────   │  Providers       │     │           │
│  │  • OpenAI (TTS/STT/LLM)               │     │           │
│  │  • Google Cloud (TTS/STT)              │     │           │
│  │  • Azure (TTS/STT)                     │     │           │
│  │  • Anthropic (LLM)                     │     │           │
│  │  • Local: pyttsx3 (TTS) / Vosk (STT)  │     │           │
│  │  • Edge TTS (Free, no key)             │     │           │
│  └────────────────────┬────────────────────┘     │           │
│                       │                          │           │
│                       ▼                          │           │
│  ┌─────────────────────────────────────────┐     │           │
│  │           External APIs                 │     │           │
│  │  ┌─────────┐ ┌───────┐ ┌──────────┐   │     │           │
│  │  │ OpenAI  │ │Google │ │ Azure    │   │     │           │
│  │  │ API     │ │Cloud  │ │ Speech   │   │     │           │
│  │  └─────────┘ └───────┘ └──────────┘   │     │           │
│  │  ┌─────────┐ ┌───────┐ ┌──────────┐   │     │           │
│  │  │Anthropic│ │Custom │ │ Edge TTS │   │     │           │
│  │  │ Claude  │ │ APIs  │ │ (Free)   │   │     │           │
│  │  └─────────┘ └───────┘ └──────────┘   │     │           │
│  └─────────────────────────────────────────┘     │           │
│                                                  │           │
│  ┌─────────────────────────────────────────┐     │           │
│  │         Scoring Layer (NeMo)            │─────┘           │
│  │  • Character Error Rate (CER)           │                 │
│  │  • Word Error Rate (WER)                │                 │
│  │  • Substitution/Deletion/Insertion      │                 │
│  │  • Accuracy %                           │                 │
│  └─────────────────────────────────────────┘                 │
│                                                              │
│  ┌─────────────────────────────────────────┐                 │
│  │         Persistence Layer               │                 │
│  │  • .env (API keys)                      │                 │
│  │  • custom_providers.json                │                 │
│  │  • tts_test_cases.json                  │                 │
│  │  • output/ (generated audio files)      │                 │
│  └─────────────────────────────────────────┘                 │
│                                                              │
└──────────────────────────────────────────────────────────────┘
```

### Component Interaction Diagram

```
User Interface (Tabs)
       │
       ├── API Tab ──────────► DynamicProviderManager ──► custom_providers.json
       │
       ├── TTS Tab ──────────► TTSProviderManager
       │                           ├── OpenAITTSProvider ──────► OpenAI API
       │                           ├── GoogleTTSProvider ─────► Google Cloud API
       │                           ├── AzureTTSProvider ──────► Azure API
       │                           ├── LocalTTSProvider ──────► pyttsx3 (local)
       │                           ├── EdgeTTSProvider ───────► Edge TTS (free)
       │                           └── DynamicTTSCaller ──────► Custom Endpoints
       │
       ├── STT Tab ──────────► STTProviderManager
       │                           ├── OpenAISTTProvider ─────► Whisper API
       │                           ├── GoogleSTTProvider ────► Google Cloud API
       │                           ├── AzureSTTProvider ─────► Azure API
       │                           ├── VoskSTTProvider ──────► Vosk (local)
       │                           └── DynamicSTTCaller ─────► Custom Endpoints
       │
       ├── LLM Tab ──────────► LLMProviderManager
       │                           ├── OpenAILLMProvider ─────► OpenAI Chat API
       │                           ├── AnthropicLLMProvider ─► Claude API
       │                           ├── CustomLLMProvider ────► Custom Endpoints
       │                           └── DynamicLLMCaller ─────► Custom Endpoints
       │
       └── Compare Tab ◄────── Results from all tabs
              │
              ├── Scoring: NeMoScorer / FallbackScorer
              │
              └── Export: JSON, CSV, Summary Report
```

### Layered Architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Presentation Layer                     │
│  ┌─────────┐ ┌─────────┐ ┌─────────┐ ┌───────────────┐ │
│  │main.py  │ │ TTS Tab │ │ STT Tab │ │ Compare Tab   │ │
│  │(Window) │ │         │ │         │ │               │ │
│  └─────────┘ └─────────┘ └─────────┘ └───────────────┘ │
├─────────────────────────────────────────────────────────┤
│                   Business Logic Layer                   │
│  ┌──────────────────┐  ┌──────────────────────────────┐ │
│  │ ProviderManagers │  │ Workers (QThread)            │ │
│  │ (TTS/STT/LLM)    │  │ • TTSWorker                  │ │
│  │                  │  │ • STTWorker                  │ │
│  │ DynamicProvider  │  │ • LLMWorker                  │ │
│  │ Manager          │  │ • BatchSTTWorker             │ │
│  └──────────────────┘  └──────────────────────────────┘ │
├─────────────────────────────────────────────────────────┤
│                    Provider Layer                        │
│  ┌────────────────────────────────────────────────────┐  │
│  │  Built-in Providers    │    Custom/Dynamic Callers │  │
│  │  • OpenAI (TTS/STT/LLM)│    • DynamicTTSCaller     │  │
│  │  • Google (TTS/STT)    │    • DynamicSTTCaller     │  │
│  │  • Azure (TTS/STT)     │    • DynamicLLMCaller     │  │
│  │  • Anthropic (LLM)     │                           │  │
│  │  • Local (pyttsx3/Vosk)│                           │  │
│  │  • Edge TTS (free)     │                           │  │
│  └────────────────────────────────────────────────────┘  │
├─────────────────────────────────────────────────────────┤
│                   Scoring Layer                          │
│  ┌─────────────────┐  ┌──────────────────────────────┐  │
│  │  NeMoScorer     │  │  FallbackScorer (pure Python)│  │
│  │  (NVIDIA NeMo)  │  │  • Levenshtein distance      │  │
│  │  • CER/WER      │  │  • Error backtrace           │  │
│  │  • Error breakdn│  │                              │  │
│  └─────────────────┘  └──────────────────────────────┘  │
├─────────────────────────────────────────────────────────┤
│                  Persistence Layer                       │
│  ┌──────────┐ ┌────────────────┐ ┌───────────────────┐  │
│  │ .env     │ │ custom_providers│ │ tts_test_cases    │  │
│  │ (keys)   │ │ .json          │ │ .json             │  │
│  └──────────┘ └────────────────┘ └───────────────────┘  │
└─────────────────────────────────────────────────────────┘
```

---

## 3. Project Structure

```
model_tester_tool/
├── main.py                    # Application entry point (QMainWindow + tabs)
├── config.py                  # Configuration loader (.env), voice/model lists
├── api_tab.py                 # API Provider management tab
├── tts_tab.py                 # TTS testing tab with test case management
├── stt_tab.py                 # STT testing tab with recording + batch
├── llm_tab.py                 # LLM API testing tab
├── comparison_tab.py          # Results comparison, ranking, export
├── tts_providers.py           # TTS provider implementations (4 built-in)
├── stt_providers.py           # STT provider implementations (4 built-in)
├── llm_providers.py           # LLM provider implementations (3 built-in)
├── edge_tts_provider.py       # Free Microsoft Edge TTS (no key needed)
├── audio_recorder.py          # Microphone recording utility
├── nemo_scoring.py            # NVIDIA NeMo CER/WER scoring + fallback
├── dynamic_providers.py       # Custom provider management + API callers
├── add_provider_dialog.py     # UI dialogs for adding/managing providers
├── batch_testing.py           # Batch STT testing (multiple audio files)
├── requirements.txt           # Python dependencies
├── .env.example               # Example API key configuration
├── custom_providers.json      # Storage for custom providers (auto-created)
├── tts_test_cases.json        # Storage for TTS test cases (auto-created)
└── output/                    # Generated audio files directory
```

### File Responsibilities

| File | Purpose |
|------|---------|
| `main.py` | Main window, tab initialization, global stylesheet, menu bar |
| `config.py` | Loads `.env`, defines `APIConfig` dataclass, voice/model constants |
| `tts_providers.py` | `TTSProviderManager` + 4 providers (OpenAI, Google, Azure, Local) |
| `stt_providers.py` | `STTProviderManager` + 4 providers (Whisper, Google, Azure, Vosk) |
| `llm_providers.py` | `LLMProviderManager` + 3 providers (OpenAI, Anthropic, Custom) |
| `edge_tts_provider.py` | Free Edge TTS with 40+ voices, no API key required |
| `nemo_scoring.py` | `NeMoScorer` (NVIDIA NeMo) + `FallbackScorer` (pure Python) |
| `dynamic_providers.py` | `DynamicProviderManager`, auto-detection, generic API callers |
| `add_provider_dialog.py` | `AddProviderDialog`, `ManageProvidersDialog`, `EditProviderDialog` |
| `audio_recorder.py` | `AudioRecorder` — microphone capture to WAV |
| `batch_testing.py` | `BatchTestingWidget` — test multiple audio files across providers |
| `comparison_tab.py` | Results table, manual ratings, rankings, JSON/CSV export |

---

## 4. Data Flow & Process

### 4.1 TTS Testing Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      TTS Testing Process                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. USER INPUT                                              │
│     ├── Select providers (checkboxes)                       │
│     ├── Choose voice (dropdown)                             │
│     └── Create test cases (text inputs)                     │
│                          │                                  │
│                          ▼                                  │
│  2. TEST CASE MANAGEMENT                                    │
│     ├── Add/Edit/Delete test cases                          │
│     ├── Load presets (greeting, weather, news, etc.)        │
│     ├── Upload TSV/CSV dataset                              │
│     └── Persist to tts_test_cases.json                      │
│                          │                                  │
│                          ▼                                  │
│  3. SYNTHESIS (Background Thread)                           │
│     ├── TTSWorker runs per test case                        │
│     ├── For each provider:                                  │
│     │   ├── Generate output path: tts_{provider}_{id}.wav   │
│     │   ├── Call provider.synthesize(text, voice, path)     │
│     │   └── Return {success, duration_ms, output_path}      │
│     └── Progress signals update UI                          │
│                          │                                  │
│                          ▼                                  │
│  4. RESULTS                                                 │
│     ├── Results table with:                                 │
│     │   ├── Test case name, provider, status, duration      │
│     │   ├── Output file path                                │
│     │   └── Play button (QMediaPlayer)                      │
│     └── Audio saved to output/ directory                    │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.2 STT Testing Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      STT Testing Process                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. AUDIO INPUT                                             │
│     ├── Option A: Microphone Recording                      │
│     │   ├── Select input device                             │
│     │   ├── Set duration (3-60 seconds)                     │
│     │   ├── Click Record → Stop                             │
│     │   └── Saved as temp WAV (16kHz, mono)                 │
│     │                                                       │
│     └── Option B: Upload Audio File                         │
│         ├── Browse for WAV/MP3/FLAC/OGG/M4A/WMA            │
│         └── Path stored for transcription                   │
│                          │                                  │
│                          ▼                                  │
│  2. REFERENCE TEXT (Ground Truth)                           │
│     ├── Enter correct transcript                            │
│     ├── Used for auto-scoring (CER/WER)                     │
│     └── Leave empty to skip scoring                         │
│                          │                                  │
│                          ▼                                  │
│  3. PROVIDER SELECTION & TRANSCRIPTION                      │
│     ├── Select providers (checkboxes)                       │
│     ├── Choose language (en-US, fr-FR, km-KH, etc.)         │
│     ├── Click "Transcribe"                                  │
│     ├── STTWorker runs in background                        │
│     └── Each provider transcribes the audio                 │
│                          │                                  │
│                          ▼                                  │
│  4. SCORING (if reference provided)                         │
│     ├── NeMoScorer.score(reference, hypothesis)             │
│     ├── Calculate:                                          │
│     │   ├── CER (Character Error Rate)                      │
│     │   ├── WER (Word Error Rate)                           │
│     │   ├── Substitutions/Deletions/Insertions              │
│     │   └── Accuracy % = 1.0 - CER                          │
│     └── Color-coded results (green/yellow/red)              │
│                          │                                  │
│                          ▼                                  │
│  5. RESULTS & COMPARISON                                    │
│     ├── Results table with all metrics                      │
│     ├── Results auto-sent to Compare Tab                    │
│     └── Can run batch tests on multiple files               │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.3 LLM Testing Flow

```
┌─────────────────────────────────────────────────────────────┐
│                      LLM Testing Process                     │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. PROMPT INPUT                                            │
│     ├── System prompt (optional)                            │
│     ├── User prompt (required)                              │
│     ├── Temperature (0.0 - 2.0)                             │
│     └── Max tokens (50 - 8192)                              │
│                          │                                  │
│                          ▼                                  │
│  2. PROVIDER & MODEL SELECTION                              │
│     ├── Built-in:                                           │
│     │   ├── OpenAI (gpt-4o, gpt-4o-mini, gpt-3.5-turbo)    │
│     │   ├── Anthropic (claude-opus-4-6, claude-sonnet-4-6) │
│     │   └── Custom API (OpenAI-compatible)                  │
│     └── Dynamic:                                            │
│         └── User-added providers (Groq, OpenRouter, etc.)   │
│                          │                                  │
│                          ▼                                  │
│  3. API CALLS (Background Thread)                           │
│     ├── LLMWorker runs in background                        │
│     ├── For each selected provider:                          │
│     │   ├── Build messages array                            │
│     │   ├── Call provider.chat(prompt, model, ...)          │
│     │   └── Return {success, text, duration_ms, tokens}     │
│     └── Progress signals update UI                          │
│                          │                                  │
│                          ▼                                  │
│  4. RESULTS                                                 │
│     ├── Tabbed view (one tab per provider)                  │
│     ├── Each tab shows:                                     │
│     │   ├── Response text                                   │
│     │   └── Duration + token count                          │
│     └── Errors shown in red                                 │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

### 4.4 Comparison & Ranking Flow

```
┌─────────────────────────────────────────────────────────────┐
│                   Comparison Process                         │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  1. DATA COLLECTION                                         │
│     ├── STT results auto-emitted via signals                │
│     │   └── results_ready signal → add_stt_scored_result()  │
│     ├── Manual rating entry (TTS/LLM)                       │
│     │   └── _on_add_score() → add to test_history           │
│     └── All stored in self.test_history list                │
│                          │                                  │
│                          ▼                                  │
│  2. RESULTS TABLE                                           │
│     ├── Filter by type (All/TTS/STT/LLM)                    │
│     ├── Show: timestamp, type, provider, model, status      │
│     ├── Show: duration, CER, accuracy, score, notes         │
│     └── Color-coded CER (green ≤10%, yellow ≤25%, red)      │
│                          │                                  │
│                          ▼                                  │
│  3. RANKINGS                                                │
│     ├── Group by provider+type                              │
│     ├── Calculate averages:                                 │
│     │   ├── Avg CER, Avg Accuracy, Avg Score                │
│     │   └── Sort by accuracy (descending)                   │
│     └── Display ranked table                                │
│                          │                                  │
│                          ▼                                  │
│  4. EXPORT                                                  │
│     ├── Export JSON (full data + summary)                   │
│     ├── Export CSV (spreadsheet format)                     │
│     └── Export Summary (ranked providers)                   │
│                                                             │
└─────────────────────────────────────────────────────────────┘
```

---

## 5. Installation & Setup

### Prerequisites

- Python 3.10+
- pip package manager
- Internet connection (for cloud providers)

### Step 1: Install Dependencies

```bash
cd model_tester_tool
pip install -r requirements.txt
```

### Step 2: Configure API Keys

```bash
cp .env.example .env
```

Edit `.env` with your credentials:

```env
# OpenAI (Whisper STT + OpenAI TTS + Chat LLM)
OPENAI_API_KEY=sk-your-key-here

# Google Cloud (STT + TTS)
GOOGLE_APPLICATION_CREDENTIALS=path/to/google-credentials.json

# Azure Cognitive Services (Speech)
AZURE_SPEECH_KEY=your-azure-key
AZURE_SPEECH_REGION=eastus

# Anthropic (Claude)
ANTHROPIC_API_KEY=sk-ant-your-key-here

# Custom API (OpenAI-compatible endpoint)
CUSTOM_API_URL=https://your-api.com/v1/chat/completions
CUSTOM_API_KEY=your-custom-key
```

### Step 3: Run

```bash
python main.py
```

### Optional: Install NeMo for Enhanced Scoring

```bash
pip install nemo-toolkit[asr]
```

> Without NeMo, the system uses a built-in `FallbackScorer` with the same CER/WER algorithm.

---

## 6. Usage Guide

### 6.1 API Tab — Provider Management

The API tab is your central hub for adding custom providers.

**Adding a Provider:**
1. Click **"+ Add New Provider"**
2. Enter a name (e.g., "My Groq API")
3. Paste the endpoint URL
4. Click **"Auto-Detect Type"** — the system will detect:
   - Provider type (TTS/STT/LLM)
   - Known models for that service
5. Enter your API key
6. Click **"Add Provider"**

**Quick Templates:**
Click any template button to auto-fill:
- OpenAI TTS, Whisper, Chat
- Anthropic, Deepgram, Groq, OpenRouter, ElevenLabs, Together

**Managing Providers:**
- Use the filter dropdown to view by type
- Click **"Edit"** on any card to modify
- Click **"Remove"** to delete a provider

### 6.2 TTS Tab — Text-to-Speech Testing

**Step 1: Select Providers**
- Check the providers you want to test
- Select a voice from the dropdown
- Edge TTS is enabled by default (free, no key needed)

**Step 2: Create Test Cases**
- Click **"+ Add Test Case"** for custom text
- Click **"+ Load Presets"** for pre-built examples:
  - Greeting, Weather, Navigation, News
  - Technical, Emotion, Questions, Khmer
- Click **"+ Upload TSV Dataset"** to import from file

**Step 3: Run Tests**
- Click **"Run All Test Cases"**
- Progress bar shows synthesis status
- Results appear in the table

**Step 4: Listen & Compare**
- Click **"Play"** next to any result
- Audio plays through your speakers
- Compare duration and quality across providers

**Test Case Management:**
- **Rename**: Change the test case name
- **Upload**: Import text from a file
- **Clear**: Remove text content
- **Delete**: Remove the test case entirely

### 6.3 STT Tab — Speech-to-Text Testing

**Single File Testing:**

1. **Audio Input** (choose one):
   - **Microphone**: Select device, set duration, click Record
   - **Audio File**: Browse for WAV/MP3/FLAC/OGG/M4A/WMA

2. **Reference Text** (optional):
   - Enter the correct transcript
   - Used for auto-scoring accuracy (CER/WER)

3. **Provider Selection**:
   - Check providers to test
   - Select language (en-US, fr-FR, km-KH, etc.)

4. **Transcribe**:
   - Click **"Transcribe"**
   - Results appear with:
     - Transcription text
     - Duration
     - CER (color-coded)
     - Accuracy %
     - Error breakdown (S/D/I)

**Batch Testing:**

1. Click **"Add Audio Files"** or **"Add Folder"**
2. Optionally **"Load References"** (CSV/JSON)
3. Click **"Run Batch Test"**
4. Progress shows per-file status
5. Results table shows all transcriptions with scoring

### 6.4 LLM Tab — LLM API Testing

1. **Enter Prompts**:
   - System prompt (optional)
   - User prompt (required)
   - Adjust temperature and max tokens

2. **Select Models**:
   - Check built-in providers
   - Select specific model per provider
   - Custom providers appear automatically

3. **Send**:
   - Click **"Send to All Selected"**
   - Each provider responds in its own tab
   - View response text, duration, and token count

### 6.5 Compare & Rank Tab

**Viewing Results:**
- All STT results appear automatically
- Filter by type: All, TTS, STT, LLM
- Stats show total tests per type

**Manual Rating:**
1. Select provider and test type
2. Enter score (1.0 - 5.0)
3. Add notes
4. Click **"+ Add Rating"**

**Rankings:**
- Auto-calculated from all results
- Sorted by accuracy (descending)
- Shows: rank, provider, avg CER, avg accuracy, avg score, test count

**Export:**
- **Export JSON**: Full data with summary
- **Export CSV**: Spreadsheet-compatible format
- **Summary**: Ranked providers report

---

## 7. Provider Types

### TTS Providers

| Provider | Key Required | Voices | Notes |
|----------|--------------|--------|-------|
| OpenAI TTS | Yes (OPENAI_API_KEY) | alloy, echo, fable, onyx, nova, shimmer | High quality neural voices |
| Google Cloud TTS | Yes (credentials JSON) | Neural2 voices | Requires service account |
| Azure TTS | Yes (AZURE_SPEECH_KEY) | Jenny, Guy, Aria Neural | Enterprise-grade |
| Local (pyttsx3) | No | System default | Offline, lower quality |
| Edge TTS | **No** | 40+ voices | Free, no key needed! |

### STT Providers

| Provider | Key Required | Models | Notes |
|----------|--------------|--------|-------|
| OpenAI Whisper | Yes (OPENAI_API_KEY) | whisper-1 | Industry-leading accuracy |
| Google Cloud STT | Yes (credentials JSON) | latest_long, latest_short | Real-time capable |
| Azure STT | Yes (AZURE_SPEECH_KEY) | conversation, dictation | Enterprise-grade |
| Local (Vosk) | No | vosk-model-small-en-us-0.15 | Offline, needs model download |

### LLM Providers

| Provider | Key Required | Models | Notes |
|----------|--------------|--------|-------|
| OpenAI | Yes (OPENAI_API_KEY) | gpt-4o, gpt-4o-mini, gpt-3.5-turbo | Chat completions API |
| Anthropic | Yes (ANTHROPIC_API_KEY) | claude-opus-4-6, claude-sonnet-4-6, claude-haiku-4-5 | Messages API |
| Custom API | Optional | Any | OpenAI-compatible endpoint |

### Auto-Detected Custom Providers

When you add a custom endpoint, the system auto-detects:

| Service | Type | Models |
|---------|------|--------|
| OpenAI | TTS/STT/LLM | tts-1, whisper-1, gpt-4o |
| ElevenLabs | TTS | eleven_monolingual_v1 |
| Deepgram | STT | nova-2, base |
| AssemblyAI | STT | best |
| Anthropic | LLM | claude-sonnet-4-6 |
| Together | LLM | Llama-3.1-8B-Instruct |
| Groq | LLM | llama-3.1-8b-instant |
| OpenRouter | LLM | auto, gemini-2.0-flash |

---

## 8. Scoring System

### CER (Character Error Rate)

CER measures transcription accuracy at the character level. Ideal for languages without word boundaries (e.g., Khmer).

```
CER = (Substitutions + Deletions + Insertions) / Reference_Length
```

| CER Range | Color | Meaning |
|-----------|-------|---------|
| 0% - 10% | Green | Excellent |
| 10% - 25% | Yellow | Acceptable |
| > 25% | Red | Poor |

### WER (Word Error Rate)

WER measures accuracy at the word level. Better for space-separated languages.

```
WER = (S + D + I) / Number_of_Words_in_Reference
```

### Accuracy

```
Accuracy = 1.0 - CER
```

### Error Types

| Type | Description | Example |
|------|-------------|---------|
| Substitution | Wrong character/word | "cat" → "bat" |
| Deletion | Missing character/word | "cat" → "ct" |
| Insertion | Extra character/word | "cat" → "cats" |

### Scoring Implementation

- **NeMoScorer**: Uses NVIDIA NeMo's `word_error_rate` function (if installed)
- **FallbackScorer**: Pure Python Levenshtein distance implementation (always available)

Both produce identical metrics. The factory function `get_scorer()` returns the best available.

---

## 9. Custom Providers

### Adding a Custom Provider

1. **Via API Tab** (recommended):
   - Click **"+ Add New Provider"**
   - Fill in name, endpoint, API key
   - Auto-detect fills in type and models
   - Click **"Add Provider"**

2. **Via TTS/STT/LLM Tab**:
   - Click **"+ Add Provider"** in any test tab
   - Same dialog appears

### Provider Persistence

Custom providers are saved to `custom_providers.json`:

```json
[
  {
    "id": "a1b2c3d4",
    "name": "My Groq API",
    "provider_type": "llm",
    "api_key": "gsk_...",
    "endpoint": "https://api.groq.com/openai/v1/chat/completions",
    "models": ["llama-3.1-8b-instant", "mixtral-8x7b-32768"],
    "headers": {},
    "config": {},
    "created_at": "2025-01-15 10:30:00"
  }
]
```

### Dynamic API Callers

The system includes generic API callers for custom providers:

| Caller | Purpose | Response Handling |
|--------|---------|-------------------|
| `DynamicTTSCaller` | Custom TTS | Direct audio, base64, or URL |
| `DynamicSTTCaller` | Custom STT | Multipart upload, JSON response |
| `DynamicLLMCaller` | Custom LLM | OpenAI/Anthropic/generic formats |

### Payload Templates

For non-standard APIs, you can define custom payload templates:

```python
# In provider config:
config = {
    "payload_template": {
        "model": "{{model}}",
        "prompt": "{{prompt}}",
        "temperature": "{{temperature}}"
    }
}
```

Placeholders: `{{text}}`, `{{voice}}`, `{{model}}`, `{{prompt}}`, `{{system}}`, `{{temperature}}`, `{{max_tokens}}`, `{{messages}}`

---

## 10. Output & Export

### Generated Files

| File | Location | Description |
|------|----------|-------------|
| TTS audio | `output/tts_{provider}_{id}.wav` | Synthesized speech |
| STT recording | Temp directory | Microphone recordings |
| Custom providers | `custom_providers.json` | Saved provider configs |
| Test cases | `tts_test_cases.json` | Saved TTS test cases |

### Export Formats

**JSON Export:**
```json
{
  "export_timestamp": "2025-01-15 10:30:00",
  "total_results": 42,
  "results": [...],
  "summary": {
    "providers_ranked": [...]
  }
}
```

**CSV Export:**
```csv
timestamp,test_type,provider,model,success,duration_ms,cer,accuracy,score,notes
2025-01-15 10:30:00,STT,OpenAI,whisper-1,True,1234,0.05,0.95,4.75,CER: 5.0%
```

**Summary Export:**
```json
{
  "export_timestamp": "2025-01-15 10:30:00",
  "total_results": 42,
  "providers_ranked": [
    {
      "provider": "OpenAI (STT)",
      "total_tests": 10,
      "avg_cer": "3.5%",
      "avg_accuracy": "96.5%",
      "avg_score_1to5": "4.8"
    }
  ]
}
```

---

## Quick Reference

### Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| Ctrl+S | Export Results (JSON) |
| Ctrl+Q | Quit Application |

### Common Workflows

**Quick TTS Test:**
1. Open TTS Tab → Edge TTS is pre-enabled
2. Edit default test case text
3. Click "Run All Test Cases"
4. Click "Play" to listen

**Quick STT Test:**
1. Open STT Tab → Select microphone
2. Click "Record" → speak → click "Stop"
3. Enter reference text
4. Click "Transcribe"
5. View CER/Accuracy scores

**Quick LLM Test:**
1. Open LLM Tab → Enter prompt
2. Select models to compare
3. Click "Send to All Selected"
4. Compare responses in tabs

**Full Comparison:**
1. Run tests across TTS, STT, and LLM tabs
2. Open Compare Tab
3. View rankings and add manual ratings
4. Export results to JSON/CSV

---

## Troubleshooting

| Issue | Solution |
|-------|----------|
| "Provider not configured" | Add API key in .env or add custom provider |
| "sounddevice not installed" | `pip install sounddevice soundfile` |
| "edge-tts not installed" | `pip install edge-tts` |
| "vosk not installed" | `pip install vosk` + download model |
| "NeMo not available" | `pip install nemo-toolkit[asr]` (optional) |
| Recording not working | Check microphone permissions and device selection |
| API call fails | Verify API key and endpoint URL |

---

*Generated: 2026-09-07 | Model Tester Tool v1.0*
