"""
Dynamic Provider Management System
Allows users to add custom API providers at runtime.
Supports TTS, STT, and LLM provider types with auto-detection.
"""

import json
import os
import time
import tempfile
from pathlib import Path
from typing import Optional
from dataclasses import dataclass, field, asdict
from enum import Enum

import httpx

from config import APIConfig

# Storage file for custom providers
CUSTOM_PROVIDERS_FILE = Path(__file__).parent / "custom_providers.json"


class ProviderType(Enum):
    TTS = "tts"
    STT = "stt"
    LLM = "llm"


@dataclass
class CustomProvider:
    """A user-defined API provider."""
    id: str
    name: str
    provider_type: str  # "tts", "stt", "llm"
    api_key: str
    endpoint: str
    models: list = field(default_factory=list)
    headers: dict = field(default_factory=dict)
    config: dict = field(default_factory=dict)  # extra config like region, voice, etc.
    created_at: str = ""

    def __post_init__(self):
        if not self.created_at:
            from datetime import datetime
            self.created_at = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, data: dict) -> "CustomProvider":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# --- Auto-detection patterns for known services ---
DETECTION_PATTERNS = {
    # TTS patterns
    "openai_tts": {
        "patterns": ["api.openai.com/v1/audio/speech"],
        "type": "tts",
        "models": ["tts-1", "tts-1-hd"],
        "endpoint_template": "https://api.openai.com/v1/audio/speech",
    },
    "elevenlabs": {
        "patterns": ["api.elevenlabs.io"],
        "type": "tts",
        "models": ["eleven_monolingual_v1", "eleven_multilingual_v1"],
        "endpoint_template": "https://api.elevenlabs.io/v1/text-to-speech/{voice_id}",
    },
    "camb_ai_stt": {
        "patterns": ["client.camb.ai/apis/transcribe"],
        "type": "stt",
        "models": ["fast", "slow"],
        "endpoint_template": "https://client.camb.ai/apis/transcribe",
    },
    "camb_ai": {
        "patterns": ["client.camb.ai/apis/tts", "client.camb.ai", "camb.ai/apis"],
        "type": "tts",
        "models": ["mars-8.1-flash-beta", "mars-8.1-pro-beta", "mars-flash", "mars-pro"],
        "endpoint_template": "https://client.camb.ai/apis/tts-stream",
    },
    "google_tts": {
        "patterns": ["texttospeech.googleapis.com"],
        "type": "tts",
        "models": ["en-US-Neural2-A"],
        "endpoint_template": "https://texttospeech.googleapis.com/v1/text:synthesize",
    },
    # STT patterns
    "openai_whisper": {
        "patterns": ["api.openai.com/v1/audio/transcriptions"],
        "type": "stt",
        "models": ["whisper-1"],
        "endpoint_template": "https://api.openai.com/v1/audio/transcriptions",
    },
    "deepgram": {
        "patterns": ["api.deepgram.com"],
        "type": "stt",
        "models": ["nova-2", "base"],
        "endpoint_template": "https://api.deepgram.com/v1/listen",
    },
    "assemblyai": {
        "patterns": ["api.assemblyai.com"],
        "type": "stt",
        "models": ["best"],
        "endpoint_template": "https://api.assemblyai.com/v2/transcript",
    },
    # LLM patterns
    "openai_chat": {
        "patterns": ["api.openai.com/v1/chat/completions"],
        "type": "llm",
        "models": ["gpt-4o", "gpt-4o-mini", "gpt-3.5-turbo"],
        "endpoint_template": "https://api.openai.com/v1/chat/completions",
    },
    "anthropic_chat": {
        "patterns": ["api.anthropic.com"],
        "type": "llm",
        "models": ["claude-sonnet-4-6", "claude-haiku-4-5-20251001"],
        "endpoint_template": "https://api.anthropic.com/v1/messages",
    },
    "together": {
        "patterns": ["api.together.xyz"],
        "type": "llm",
        "models": ["meta-llama/Llama-3.1-8B-Instruct-Turbo"],
        "endpoint_template": "https://api.together.xyz/v1/chat/completions",
    },
    "groq": {
        "patterns": ["api.groq.com"],
        "type": "llm",
        "models": ["llama-3.1-8b-instant", "mixtral-8x7b-32768"],
        "endpoint_template": "https://api.groq.com/openai/v1/chat/completions",
    },
    "openrouter": {
        "patterns": ["openrouter.ai/api"],
        "type": "llm",
        "models": ["auto", "google/gemini-2.0-flash-001"],
        "endpoint_template": "https://openrouter.ai/api/v1/chat/completions",
    },
}


def detect_provider_type(endpoint: str) -> Optional[dict]:
    """
    Auto-detect provider type and models from endpoint URL.
    Returns dict with type, models, and detected_service or None.
    """
    endpoint_lower = endpoint.lower()
    for service, info in DETECTION_PATTERNS.items():
        for pattern in info["patterns"]:
            if pattern.lower() in endpoint_lower:
                return {
                    "service": service,
                    "type": info["type"],
                    "models": info["models"],
                    "endpoint_template": info["endpoint_template"],
                }
    return None


class DynamicProviderManager:
    """Manages dynamically added providers with persistence."""

    def __init__(self):
        self.providers: dict[str, CustomProvider] = {}
        self._load()

    def _load(self):
        """Load custom providers from disk."""
        if CUSTOM_PROVIDERS_FILE.exists():
            try:
                with open(CUSTOM_PROVIDERS_FILE, "r") as f:
                    data = json.load(f)
                for item in data:
                    provider = CustomProvider.from_dict(item)
                    self.providers[provider.id] = provider
            except (json.JSONDecodeError, KeyError):
                pass

    def _save(self):
        """Save custom providers to disk."""
        data = [p.to_dict() for p in self.providers.values()]
        with open(CUSTOM_PROVIDERS_FILE, "w") as f:
            json.dump(data, f, indent=2)

    def add_provider(self, provider: CustomProvider) -> None:
        """Add a new custom provider."""
        self.providers[provider.id] = provider
        self._save()

    def remove_provider(self, provider_id: str) -> None:
        """Remove a custom provider."""
        if provider_id in self.providers:
            del self.providers[provider_id]
            self._save()

    def get_by_type(self, provider_type: str) -> list[CustomProvider]:
        """Get all custom providers of a specific type."""
        return [p for p in self.providers.values() if p.provider_type == provider_type]

    def get_all(self) -> list[CustomProvider]:
        """Get all custom providers."""
        return list(self.providers.values())


# --- Generic API callers for dynamic providers ---

class DynamicTTSCaller:
    """Handles TTS calls to custom providers."""

    @staticmethod
    def synthesize(provider: CustomProvider, text: str, voice: str, output_path: str) -> dict:
        """Synthesize speech from a custom TTS provider."""
        start = time.time()
        try:
            headers = {}
            if provider.api_key:
                headers["Authorization"] = f"Token {provider.api_key}"
            headers.update(provider.headers)

            endpoint = provider.endpoint
            model = provider.models[0] if provider.models else "aura-asteria-en"

            # ── Deepgram Aura TTS ──────────────────────────────────────────────
            # POST https://api.deepgram.com/v1/speak?model=aura-asteria-en
            # Body: plain text (Content-Type: text/plain)
            if "deepgram.com/v1/speak" in endpoint:
                headers["Content-Type"] = "text/plain"
                params = {"model": model}
                with httpx.Client(timeout=120.0) as client:
                    response = client.post(
                        endpoint, params=params,
                        content=text.encode("utf-8"), headers=headers
                    )
                    response.raise_for_status()
                    with open(output_path, "wb") as f:
                        f.write(response.content)

            # ── Camb.ai TTS ───────────────────────────────────────────────────
            # POST https://client.camb.ai/apis/tts-stream
            # Auth: x-api-key header (not Bearer)
            # Body: JSON with text, voice_id (int), language (BCP-47 lowercase), speech_model
            # Response: raw binary audio (audio/wav)
            elif "camb.ai" in endpoint:
                headers.pop("Authorization", None)
                headers["x-api-key"] = provider.api_key
                headers["Content-Type"] = "application/json"

                speech_model = model if model else "mars-8.1-flash-beta"

                # voice_id must be an integer — default 147320 works for all languages
                try:
                    voice_id = int(model)
                except (ValueError, TypeError):
                    voice_id = 147320

                # Map app language codes to Camb.ai BCP-47 short_name
                CAMB_LANG_MAP = {
                    "km-KH": "km-kh",
                    "en-US": "en-us",
                    "en-GB": "en-gb",
                    "fr-FR": "fr-fr",
                    "de-DE": "de-de",
                    "es-ES": "es-es",
                    "ja-JP": "ja-jp",
                    "zh-CN": "zh-cn",
                    "ko-KR": "ko-kr",
                    "vi-VN": "vi-vn",
                    "th-TH": "th-th",
                    "id-ID": "id-id",
                    "hi-IN": "hi-in",
                    "ar-SA": "ar-sa",
                    "ru-RU": "ru-ru",
                }

                # Resolve language: provider config > passed voice param > default en-us
                camb_lang = provider.config.get("language", "en-us")
                # If voice carries a language code (e.g. "km-KH") use that
                if voice and "-" in voice and len(voice) == 5:
                    camb_lang = CAMB_LANG_MAP.get(voice, voice.lower())

                payload = {
                    "text": text,
                    "voice_id": voice_id,
                    "language": camb_lang,
                    "speech_model": speech_model,
                    "output_configuration": {"format": "wav"},
                }

                with httpx.Client(timeout=120.0) as client:
                    response = client.post(endpoint, json=payload, headers=headers)
                    response.raise_for_status()
                    with open(output_path, "wb") as f:
                        f.write(response.content)

            # ── ElevenLabs TTS ────────────────────────────────────────────────
            elif "elevenlabs.io" in endpoint:
                headers["Content-Type"] = "application/json"
                headers["xi-api-key"] = provider.api_key
                headers.pop("Authorization", None)
                voice_id = model  # model field holds voice_id for ElevenLabs
                url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
                payload = {
                    "text": text,
                    "model_id": "eleven_monolingual_v1",
                    "voice_settings": {"stability": 0.5, "similarity_boost": 0.5}
                }
                with httpx.Client(timeout=120.0) as client:
                    response = client.post(url, json=payload, headers=headers)
                    response.raise_for_status()
                    with open(output_path, "wb") as f:
                        f.write(response.content)

            # ── OpenAI-compatible TTS (generic) ───────────────────────────────
            else:
                headers["Content-Type"] = "application/json"
                # Switch to Bearer for OpenAI-style
                headers["Authorization"] = f"Bearer {provider.api_key}"

                payload_template = provider.config.get("payload_template", {})
                if payload_template:
                    payload_str = json.dumps(payload_template)
                    payload_str = payload_str.replace("{{text}}", text)
                    payload_str = payload_str.replace("{{voice}}", voice)
                    payload_str = payload_str.replace("{{model}}", model)
                    payload = json.loads(payload_str)
                else:
                    payload = {
                        "model": model,
                        "input": text,
                        "voice": voice or "alloy",
                        "response_format": "wav",
                    }

                with httpx.Client(timeout=120.0) as client:
                    response = client.post(endpoint, json=payload, headers=headers)
                    response.raise_for_status()

                    content_type = response.headers.get("content-type", "")
                    if "audio" in content_type or response.content[:4] in (b"RIFF", b"ID3\x03", b"\xff\xfb"):
                        with open(output_path, "wb") as f:
                            f.write(response.content)
                    else:
                        data = response.json()
                        if "audio" in data:
                            import base64
                            with open(output_path, "wb") as f:
                                f.write(base64.b64decode(data["audio"]))
                        elif "url" in data:
                            audio_resp = client.get(data["url"])
                            with open(output_path, "wb") as f:
                                f.write(audio_resp.content)
                        else:
                            return {"success": False, "duration_ms": 0,
                                    "error": f"Unexpected response: {str(data)[:200]}"}

            duration = (time.time() - start) * 1000
            return {"success": True, "duration_ms": duration, "error": "", "output_path": output_path}

        except httpx.HTTPStatusError as e:
            return {"success": False, "duration_ms": 0,
                    "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
        except Exception as e:
            return {"success": False, "duration_ms": 0, "error": str(e)}


class DynamicSTTCaller:
    """Handles STT calls to custom providers."""

    @staticmethod
    def transcribe(provider: CustomProvider, audio_path: str, language: str = "en-US") -> dict:
        """Transcribe audio from a custom STT provider."""
        start = time.time()
        try:
            headers = {}
            if provider.api_key:
                headers["Authorization"] = f"Token {provider.api_key}"
            headers.update(provider.headers)

            model = provider.models[0] if provider.models else "nova-2"

            with httpx.Client(timeout=120.0) as client:

                # ── Camb.ai STT (async: submit → poll → fetch) ────────────────
                # POST /apis/transcribe  → task_id
                # GET  /apis/transcribe/{task_id} → {status, run_id}
                # POST /apis/transcribe/results → [{text,...}]  (requires paid tier)
                if "camb.ai" in provider.endpoint:
                    import time as _time
                    headers.pop("Authorization", None)
                    headers["x-api-key"] = provider.api_key

                    CAMB_LANG_MAP = {
                        "km-KH": "km-kh", "en-US": "en-us", "en-GB": "en-gb",
                        "fr-FR": "fr-fr", "de-DE": "de-de", "es-ES": "es-es",
                        "ja-JP": "ja-jp", "zh-CN": "zh-cn", "ko-KR": "ko-kr",
                    }
                    camb_lang = CAMB_LANG_MAP.get(language, language.lower())

                    # Step 1: Submit the audio file
                    with open(audio_path, "rb") as af:
                        submit_resp = client.post(
                            "https://client.camb.ai/apis/transcribe",
                            files={"media_file": ("audio.wav", af, "audio/wav")},
                            data={"language": camb_lang,
                                  "transcription_mode": provider.models[0] if provider.models else "fast"},
                            headers=headers,
                            timeout=60,
                        )
                    submit_resp.raise_for_status()
                    task_id = submit_resp.json().get("task_id")
                    if not task_id:
                        return {"success": False, "text": "", "duration_ms": 0,
                                "error": f"No task_id in response: {submit_resp.text[:200]}"}

                    # Step 2: Poll until complete (max 120s)
                    run_id = None
                    for _ in range(24):
                        _time.sleep(5)
                        poll_resp = client.get(
                            f"https://client.camb.ai/apis/transcribe/{task_id}",
                            headers=headers, timeout=15
                        )
                        poll_data = poll_resp.json()
                        status = poll_data.get("status")
                        if status == "SUCCESS":
                            run_id = poll_data.get("run_id")
                            break
                        elif status in ("FAILED", "ERROR"):
                            return {"success": False, "text": "", "duration_ms": 0,
                                    "error": f"Camb.ai transcription failed: {poll_data.get('exception_reason', status)}"}

                    if not run_id:
                        return {"success": False, "text": "", "duration_ms": 0,
                                "error": "Camb.ai transcription timed out after 120s"}

                    # Step 3: Fetch transcript text (requires Pro/paid tier)
                    # Submit a dummy second run_id to satisfy 2-5 minimum requirement
                    fetch_resp = client.post(
                        "https://client.camb.ai/apis/transcribe/results",
                        json={"run_ids": [run_id, run_id]},
                        headers={**headers, "Content-Type": "application/json"},
                        timeout=15,
                    )

                    if fetch_resp.status_code == 403:
                        return {"success": False, "text": "", "duration_ms": 0,
                                "error": f"Camb.ai transcript retrieval requires a paid plan. "
                                         f"The audio was transcribed (run_id: {run_id}) but the "
                                         f"results endpoint is not accessible on the free tier. "
                                         f"Upgrade at studio.camb.ai to retrieve transcripts."}

                    fetch_resp.raise_for_status()
                    result_data = fetch_resp.json()

                    # Response: {run_id_str: [{start, end, text, speaker}, ...]}
                    segments = result_data.get(str(run_id), [])
                    text = " ".join(seg.get("text", "") for seg in segments).strip()

                    duration = (_time.time() - start) * 1000
                    return {"success": True, "text": text, "duration_ms": duration, "error": ""}

                # ── Deepgram STT ───────────────────────────────────────────────
                # POST audio as raw bytes with query params
                if "deepgram.com" in provider.endpoint:
                    headers["Content-Type"] = "audio/wav"
                    params = {
                        "model": model,
                        "language": language.split("-")[0],
                        "punctuate": "true",
                    }
                    with open(audio_path, "rb") as f:
                        audio_bytes = f.read()
                    response = client.post(
                        provider.endpoint, params=params,
                        content=audio_bytes, headers=headers
                    )
                    response.raise_for_status()
                    resp_data = response.json()
                    text = (resp_data.get("results", {})
                                     .get("channels", [{}])[0]
                                     .get("alternatives", [{}])[0]
                                     .get("transcript", ""))

                # ── Generic multipart (OpenAI Whisper-compatible) ──────────────
                else:
                    with open(audio_path, "rb") as audio_file:
                        files = {"file": ("audio.wav", audio_file, "audio/wav")}
                        data = {
                            "model": model,
                            "language": language.split("-")[0],
                        }
                        response = client.post(
                            provider.endpoint, files=files,
                            data=data, headers=headers
                        )
                        response.raise_for_status()
                        resp_data = response.json()

                    # Extract text from various response formats
                    text = ""
                    if isinstance(resp_data, str):
                        text = resp_data
                    elif "text" in resp_data:
                        text = resp_data["text"]
                    elif "transcript" in resp_data:
                        text = resp_data["transcript"]
                    elif "results" in resp_data:
                        text = (resp_data["results"].get("channels", [{}])[0]
                                .get("alternatives", [{}])[0]
                                .get("transcript", ""))

            duration = (time.time() - start) * 1000
            return {"success": True, "text": text, "duration_ms": duration, "error": ""}

        except httpx.HTTPStatusError as e:
            return {"success": False, "text": "", "duration_ms": 0,
                    "error": f"HTTP {e.response.status_code}: {e.response.text[:200]}"}
        except Exception as e:
            return {"success": False, "text": "", "duration_ms": 0, "error": str(e)}


class DynamicLLMCaller:
    """Handles LLM calls to custom providers."""

    @staticmethod
    def chat(provider: CustomProvider, prompt: str, model: str = "",
             system_prompt: str = "", temperature: float = 0.7, max_tokens: int = 1024) -> dict:
        """Send chat completion to a custom LLM provider."""
        start = time.time()
        try:
            headers = {"Content-Type": "application/json"}
            if provider.api_key:
                headers["Authorization"] = f"Bearer {provider.api_key}"
            headers.update(provider.headers)

            # Build messages
            messages = []
            if system_prompt:
                messages.append({"role": "system", "content": system_prompt})
            messages.append({"role": "user", "content": prompt})

            # Use custom payload template if provided
            payload_template = provider.config.get("payload_template")
            if payload_template:
                payload_str = json.dumps(payload_template)
                payload_str = payload_str.replace("{{prompt}}", prompt.replace('"', '\\"'))
                payload_str = payload_str.replace("{{system}}", system_prompt.replace('"', '\\"'))
                payload_str = payload_str.replace("{{model}}", model or (provider.models[0] if provider.models else "default"))
                payload_str = payload_str.replace("{{temperature}}", str(temperature))
                payload_str = payload_str.replace("{{max_tokens}}", str(max_tokens))
                # Remove messages if using template
                if "{{messages}}" not in payload_str:
                    payload = json.loads(payload_str)
                else:
                    payload_str = payload_str.replace("{{messages}}", json.dumps(messages))
                    payload = json.loads(payload_str)
            else:
                # Standard OpenAI-compatible format
                payload = {
                    "model": model or (provider.models[0] if provider.models else "default"),
                    "messages": messages,
                    "temperature": temperature,
                    "max_tokens": max_tokens,
                }

            with httpx.Client(timeout=120.0) as client:
                response = client.post(provider.endpoint, json=payload, headers=headers)
                response.raise_for_status()
                data = response.json()

            duration = (time.time() - start) * 1000

            # Parse response - try multiple formats
            text = ""
            tokens = 0

            # OpenAI format
            if "choices" in data and data["choices"]:
                text = data["choices"][0].get("message", {}).get("content", "")
            # Anthropic format
            elif "content" in data and isinstance(data["content"], list):
                text = data["content"][0].get("text", "")
            # Simple text format
            elif "text" in data:
                text = data["text"]
            elif "response" in data:
                text = data["response"]
            elif "output" in data:
                text = data["output"]

            # Token counting
            if "usage" in data:
                tokens = data["usage"].get("total_tokens",
                           data["usage"].get("output_tokens", 0) + data["usage"].get("input_tokens", 0))

            return {"success": True, "text": text, "duration_ms": duration, "tokens": tokens, "error": ""}
        except Exception as e:
            return {"success": False, "text": "", "duration_ms": 0, "tokens": 0, "error": str(e)}
