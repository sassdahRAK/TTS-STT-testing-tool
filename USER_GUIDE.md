# Model Tester Tool — User Guide

A desktop tool for testing and comparing TTS, STT, and LLM API models.
STT testing is powered by **NVIDIA NeMo** for accurate CER/WER scoring.

---

## Table of Contents

1. [Getting Started](#getting-started)
2. [STT Testing — Single File](#stt-testing--single-file)
3. [STT Testing — Batch Testing](#stt-testing--batch-testing)
4. [Compare & Rank](#compare--rank)
5. [Export Results](#export-results)
6. [NeMo Scoring Explained](#nemo-scoring-explained)

---

## Getting Started

### Installation

```bash
pip install -r requirements.txt
```

### API Keys

Copy `.env.example` to `.env` and fill in your API keys:

```env
OPENAI_API_KEY=your_key_here
AZURE_SPEECH_KEY=your_key_here
AZURE_SPEECH_REGION=eastus
GOOGLE_APPLICATION_CREDENTIALS=path/to/credentials.json
```

### Run the App

```bash
python main.py
```

---

## STT Testing — Single File

Test one audio file across multiple STT providers with automatic accuracy scoring.

### Step 1: Select Audio Input

Choose between two input methods:

| Method | How |
|--------|-----|
| **Microphone** | Click "Record", speak, then click "Stop" |
| **Audio File** | Click "Browse..." and select a WAV, MP3, or FLAC file |

### Step 2: Enter Reference Text (Optional but Recommended)

In the **"Reference Text (Ground Truth)"** box, type the correct transcript of the audio.

- This enables automatic CER scoring for each provider
- Leave empty to skip scoring

### Step 3: Select Providers

Check the providers you want to test:

- **Built-in**: OpenAI Whisper, Google Cloud, Azure, Local Vosk
- **Custom**: Any providers you added via the API tab

### Step 4: Select Language

Choose the audio language from the dropdown (e.g., `km-KH` for Khmer).

### Step 5: Transcribe

Click the **"Transcribe"** button. Results appear automatically.

### Reading Results

| Column | Meaning |
|--------|---------|
| Provider | Which STT service was used |
| Transcription | The text output from the model |
| Duration | How long transcription took (ms) |
| Status | Success or Failed |
| **CER** | Character Error Rate (color-coded) |
| **Accuracy** | 100% - CER |
| **Errors (S/D/I)** | Substitutions / Deletions / Insertions |

### CER Color Codes

| Color | CER Range | Meaning |
|-------|-----------|---------|
| Green | ≤ 10% | Excellent accuracy |
| Yellow | 10% – 25% | Moderate errors |
| Red | > 25% | Poor accuracy |

---

## STT Testing — Batch Testing

Test multiple audio files across all providers in one go.

### Access Batch Testing

Go to **STT** tab → click **"Batch Testing"** sub-tab.

### Step 1: Add Audio Files

| Button | What It Does |
|--------|--------------|
| **Add Audio Files...** | Select multiple files individually |
| **Add Folder...** | Import all audio files from a directory |

Supported formats: WAV, MP3, FLAC, OGG, M4A, WMA

### Step 2: Load Reference Texts (Optional)

Click **"Load References (CSV/JSON)..."** to load ground truth for each file.

**CSV Format:**
```csv
audio_file1.wav,សូមអរគុណសម្រាប់ការទស្សនា
audio_file2.wav,ជម្រាបសួរលោកអ្នកនាង
```

**JSON Format:**
```json
[
  {"audio_filepath": "audio_file1.wav", "text": "សូមអរគុណ"},
  {"audio_filepath": "audio_file2.wav", "text": "ជម្រាបសួរ"}
]
```

The tool matches references to files by filename.

### Step 3: Select Providers

Check which providers to test (same as single file mode).

### Step 4: Run Batch Test

Click **"Run Batch Test"**. The tool processes each file with each provider.

- Progress bar shows overall progress
- Each file's status updates in the file table
- Click **"Stop"** to cancel mid-batch

### Reading Batch Results

| Column | Meaning |
|--------|---------|
| File | Audio filename |
| Provider | STT service used |
| Transcription | Model output text |
| Duration | Processing time (ms) |
| CER | Character Error Rate (color-coded) |
| Accuracy | 100% - CER |
| Errors (S/D/I) | Substitutions / Deletions / Insertions |
| Status | Success or Failed |

### Summary

After completion, a summary line shows average CER per provider:

```
Average CER — OpenAI Whisper: 8.2% (5 files) | Azure STT: 15.3% (5 files)
```

---

## Compare & Rank

The **Compare & Rank** tab collects all test results and ranks providers by accuracy.

### What It Shows

1. **Summary Statistics** — Total tests by type (TTS/STT/LLM)
2. **Results Table** — All test results with CER, Accuracy, and Scores
3. **Model Rankings** — Providers ranked by average accuracy

### Filtering

Use the **Test Type** dropdown to filter:
- **All** — Show everything
- **TTS** — Only TTS results
- **STT** — Only STT results
- **LLM** — Only LLM results

### Rankings Table

| Column | Meaning |
|--------|---------|
| Rank | Position (#1 is best) |
| Provider | Provider name + test type |
| Avg CER | Average Character Error Rate |
| Avg Accuracy | Average accuracy percentage |
| Avg Score (1-5) | Manual rating average |
| Test Count | Number of tests run |

### Manual Rating

For TTS and LLM (which can't be auto-scored with CER):

1. Select **Provider** and **Test Type**
2. Set a **Score** from 1.0 to 5.0
3. Add **Notes** explaining the rating
4. Click **"Add Rating"**

---

## Export Results

Three export formats are available from the Compare & Rank tab.

### Export JSON

Click **"Export JSON"** (or press `Ctrl+S`).

Contains:
- All test results with full details
- Summary statistics
- Provider rankings

```json
{
  "export_timestamp": "2026-09-06 10:30:00",
  "total_results": 25,
  "results": [...],
  "summary": {...}
}
```

### Export CSV

Click **"Export CSV"**.

Spreadsheet-friendly format. Open in Excel, Google Sheets, or any CSV reader.

| timestamp | test_type | provider | model | success | duration_ms | cer | accuracy | score | notes |
|-----------|-----------|----------|-------|---------|-------------|-----|----------|-------|-------|
| 2026-09-06 10:30:00 | STT | OpenAI Whisper | STT | True | 1250 | 8.24% | 91.76% | 4.59 | CER: 8.2% |

### Export Summary

Click **"Export Summary"**.

A focused report with provider rankings and averages:

```json
{
  "export_timestamp": "2026-09-06 10:30:00",
  "total_results": 25,
  "providers_ranked": [
    {
      "provider": "OpenAI Whisper (STT)",
      "total_tests": 10,
      "success_count": 10,
      "fail_count": 0,
      "avg_cer": "8.24%",
      "avg_accuracy": "91.76%",
      "avg_score_1to5": "4.59",
      "avg_duration_ms": 1250.5
    }
  ]
}
```

---

## NeMo Scoring Explained

### What is CER?

**Character Error Rate (CER)** measures how many characters are wrong in the transcription compared to the reference text.

```
CER = (Substitutions + Deletions + Insertions) / Reference Length
```

### Why CER for Khmer?

Khmer has no spaces between words, so Word Error Rate (WER) doesn't work. CER is the correct metric.

### How Scoring Works

1. You provide a **reference text** (ground truth)
2. The model produces a **hypothesis** (its transcription)
3. NeMo calculates the **edit distance** between them
4. The result is a CER score from 0% (perfect) to 100%+ (very wrong)

### Error Types

| Type | Example | Description |
|------|---------|-------------|
| **Substitution** | Reference: សូម → Hypothesis: សុម | Wrong character |
| **Deletion** | Reference: សូម → Hypothesis: សូ | Missing character |
| **Insertion** | Reference: សូម → Hypothesis: សូមម | Extra character |

### NeMo vs Fallback

| | NeMo Scorer | Fallback Scorer |
|---|---|---|
| Requires NeMo install | Yes | No |
| Speed | Fast (optimized) | Slightly slower |
| Accuracy | Same algorithm | Same algorithm |
| GPU support | Yes | No |

The app auto-detects NeMo and uses it if available. Otherwise, it uses the built-in fallback.

---

## Quick Reference

| Task | Where |
|------|-------|
| Test one audio file | STT tab → Single File |
| Test many files | STT tab → Batch Testing |
| Load reference texts | Batch Testing → Load References |
| View rankings | Compare & Rank tab |
| Export to JSON | Compare & Rank → Export JSON |
| Export to CSV | Compare & Rank → Export CSV |
| Export summary | Compare & Rank → Export Summary |
| Add custom provider | STT tab → + Add Provider |
| Rate TTS/LLM manually | Compare & Rank → Add Rating |
