"""
TTS Provider implementations for each supported service.
Each provider has a synthesize(text, voice, output_path) method.
"""

import os
import tempfile
import time
from abc import ABC, abstractmethod
from pathlib import Path
from typing import Optional

from config import APIConfig


class TTSProvider(ABC):
    """Base class for all TTS providers."""

    name: str = "base"
    display_name: str = "Base Provider"

    def __init__(self, config: APIConfig):
        self.config = config

    @abstractmethod
    def synthesize(self, text: str, voice: str, output_path: str) -> dict:
        """
        Synthesize speech from text.
        Returns: {"success": bool, "duration_ms": float, "error": str}
        """
        pass

    def is_available(self) -> bool:
        return True


class OpenAITTSProvider(TTSProvider):
    """OpenAI Text-to-Speech API."""

    name = "openai"
    display_name = "OpenAI TTS"

    def is_available(self) -> bool:
        return bool(self.config.openai_api_key)

    def synthesize(self, text: str, voice: str, output_path: str) -> dict:
        try:
            import openai
        except ImportError:
            return {"success": False, "duration_ms": 0, "error": "openai package not installed"}

        if not self.config.openai_api_key:
            return {"success": False, "duration_ms": 0, "error": "OpenAI API key not configured"}

        start = time.time()
        try:
            client = openai.OpenAI(api_key=self.config.openai_api_key)
            response = client.audio.speech.create(
                model="tts-1",
                voice=voice or "alloy",
                input=text,
                response_format="wav"
            )
            response.stream_to_file(output_path)
            duration = (time.time() - start) * 1000
            return {"success": True, "duration_ms": duration, "error": ""}
        except Exception as e:
            return {"success": False, "duration_ms": 0, "error": str(e)}


class GoogleTTSProvider(TTSProvider):
    """Google Cloud Text-to-Speech API."""

    name = "google"
    display_name = "Google Cloud TTS"

    def is_available(self) -> bool:
        return bool(self.config.google_credentials_path)

    def synthesize(self, text: str, voice: str, output_path: str) -> dict:
        try:
            from google.cloud import texttospeech
        except ImportError:
            return {"success": False, "duration_ms": 0, "error": "google-cloud-texttospeech not installed"}

        if not self.config.google_credentials_path:
            return {"success": False, "duration_ms": 0, "error": "Google credentials not configured"}

        start = time.time()
        try:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.config.google_credentials_path
            client = texttospeech.TextToSpeechClient()

            synthesis_input = texttospeech.SynthesisInput(text=text)
            voice_params = texttospeech.VoiceSelectionParams(
                language_code="en-US",
                name=voice or "en-US-Neural2-A",
            )
            audio_config = texttospeech.AudioConfig(
                audio_encoding=texttospeech.AudioEncoding.LINEAR16
            )

            response = client.synthesize_speech(
                input=synthesis_input,
                voice=voice_params,
                audio_config=audio_config,
            )

            with open(output_path, "wb") as f:
                f.write(response.audio_content)

            duration = (time.time() - start) * 1000
            return {"success": True, "duration_ms": duration, "error": ""}
        except Exception as e:
            return {"success": False, "duration_ms": 0, "error": str(e)}


class AzureTTSProvider(TTSProvider):
    """Azure Cognitive Services Speech (TTS)."""

    name = "azure"
    display_name = "Azure TTS"

    def is_available(self) -> bool:
        return bool(self.config.azure_speech_key)

    def synthesize(self, text: str, voice: str, output_path: str) -> dict:
        try:
            import azure.cognitiveservices.speech as speechsdk
        except ImportError:
            return {"success": False, "duration_ms": 0, "error": "azure-cognitiveservices-speech not installed"}

        if not self.config.azure_speech_key:
            return {"success": False, "duration_ms": 0, "error": "Azure Speech key not configured"}

        start = time.time()
        try:
            speech_config = speechsdk.SpeechConfig(
                subscription=self.config.azure_speech_key,
                region=self.config.azure_speech_region,
            )
            speech_config.set_speech_synthesis_output_format(
                speechsdk.SpeechSynthesisOutputFormat.Riff16Khz16BitMonoPcm
            )
            speech_config.speech_synthesis_voice_name = voice or "en-US-JennyNeural"

            audio_config = speechsdk.audio.AudioOutputConfig(filename=output_path)
            synthesizer = speechsdk.SpeechSynthesizer(
                speech_config=speech_config,
                audio_config=audio_config,
            )

            result = synthesizer.speak_text_async(text).get()

            if result.reason == speechsdk.ResultReason.SynthesizingAudioCompleted:
                duration = (time.time() - start) * 1000
                return {"success": True, "duration_ms": duration, "error": ""}
            else:
                return {"success": False, "duration_ms": 0, "error": f"Synthesis failed: {result.reason}"}
        except Exception as e:
            return {"success": False, "duration_ms": 0, "error": str(e)}


class LocalTTSProvider(TTSProvider):
    """Local offline TTS using pyttsx3."""

    name = "local"
    display_name = "Local (pyttsx3)"

    def synthesize(self, text: str, voice: str, output_path: str) -> dict:
        try:
            import pyttsx3
        except ImportError:
            return {"success": False, "duration_ms": 0, "error": "pyttsx3 not installed"}

        start = time.time()
        try:
            engine = pyttsx3.init()
            engine.save_to_file(text, output_path)
            engine.runAndWait()
            duration = (time.time() - start) * 1000
            return {"success": True, "duration_ms": duration, "error": ""}
        except Exception as e:
            return {"success": False, "duration_ms": 0, "error": str(e)}


class TTSProviderManager:
    """Manages all TTS providers and provides a unified interface."""

    def __init__(self, config: APIConfig):
        self.config = config
        self.providers: dict[str, TTSProvider] = {
            "openai": OpenAITTSProvider(config),
            "google": GoogleTTSProvider(config),
            "azure": AzureTTSProvider(config),
            "local": LocalTTSProvider(config),
        }

    def get_available_providers(self) -> list[str]:
        """Return list of provider names that are configured and available."""
        return [name for name, provider in self.providers.items() if provider.is_available()]

    def synthesize(self, provider_name: str, text: str, voice: str, output_path: str) -> dict:
        """Synthesize using the specified provider."""
        provider = self.providers.get(provider_name)
        if not provider:
            return {"success": False, "duration_ms": 0, "error": f"Unknown provider: {provider_name}"}
        return provider.synthesize(text, voice, output_path)

    def synthesize_all(self, text: str, voice: str, output_dir: str) -> dict:
        """Synthesize with all available providers. Returns results per provider."""
        results = {}
        for name, provider in self.providers.items():
            if provider.is_available():
                path = os.path.join(output_dir, f"tts_{name}.wav")
                results[name] = provider.synthesize(text, voice, path)
                if results[name]["success"]:
                    results[name]["output_path"] = path
        return results
