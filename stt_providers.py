"""
STT Provider implementations for each supported service.
Each provider has a transcribe(audio_path, language) method.
"""

import os
import time
from abc import ABC, abstractmethod
from typing import Optional

from config import APIConfig


class STTProvider(ABC):
    """Base class for all STT providers."""

    name: str = "base"
    display_name: str = "Base Provider"

    def __init__(self, config: APIConfig):
        self.config = config

    @abstractmethod
    def transcribe(self, audio_path: str, language: str = "en-US") -> dict:
        """
        Transcribe audio file to text.
        Returns: {"success": bool, "text": str, "duration_ms": float, "error": str}
        """
        pass

    def is_available(self) -> bool:
        return True


class OpenAISTTProvider(STTProvider):
    """OpenAI Whisper API for STT."""

    name = "openai"
    display_name = "OpenAI Whisper"

    def is_available(self) -> bool:
        return bool(self.config.openai_api_key)

    def transcribe(self, audio_path: str, language: str = "en-US") -> dict:
        try:
            import openai
        except ImportError:
            return {"success": False, "text": "", "duration_ms": 0, "error": "openai package not installed"}

        if not self.config.openai_api_key:
            return {"success": False, "text": "", "duration_ms": 0, "error": "OpenAI API key not configured"}

        start = time.time()
        try:
            client = openai.OpenAI(api_key=self.config.openai_api_key)
            with open(audio_path, "rb") as audio_file:
                response = client.audio.transcriptions.create(
                    model="whisper-1",
                    file=audio_file,
                    language=language.split("-")[0],  # "en-US" -> "en"
                    response_format="text"
                )
            duration = (time.time() - start) * 1000
            return {"success": True, "text": response, "duration_ms": duration, "error": ""}
        except Exception as e:
            return {"success": False, "text": "", "duration_ms": 0, "error": str(e)}


class GoogleSTTProvider(STTProvider):
    """Google Cloud Speech-to-Text API."""

    name = "google"
    display_name = "Google Cloud STT"

    def is_available(self) -> bool:
        return bool(self.config.google_credentials_path)

    def transcribe(self, audio_path: str, language: str = "en-US") -> dict:
        try:
            from google.cloud import speech
        except ImportError:
            return {"success": False, "text": "", "duration_ms": 0, "error": "google-cloud-speech not installed"}

        if not self.config.google_credentials_path:
            return {"success": False, "text": "", "duration_ms": 0, "error": "Google credentials not configured"}

        start = time.time()
        try:
            os.environ["GOOGLE_APPLICATION_CREDENTIALS"] = self.config.google_credentials_path
            client = speech.SpeechClient()

            with open(audio_path, "rb") as f:
                content = f.read()

            audio = speech.RecognitionAudio(content=content)
            config = speech.RecognitionConfig(
                encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
                sample_rate_hertz=16000,
                language_code=language,
            )

            response = client.recognize(config=config, audio=audio)

            text = ""
            for result in response.results:
                text += result.alternatives[0].transcript + " "

            duration = (time.time() - start) * 1000
            return {"success": True, "text": text.strip(), "duration_ms": duration, "error": ""}
        except Exception as e:
            return {"success": False, "text": "", "duration_ms": 0, "error": str(e)}


class AzureSTTProvider(STTProvider):
    """Azure Cognitive Services Speech (STT)."""

    name = "azure"
    display_name = "Azure STT"

    def is_available(self) -> bool:
        return bool(self.config.azure_speech_key)

    def transcribe(self, audio_path: str, language: str = "en-US") -> dict:
        try:
            import azure.cognitiveservices.speech as speechsdk
        except ImportError:
            return {"success": False, "text": "", "duration_ms": 0, "error": "azure-cognitiveservices-speech not installed"}

        if not self.config.azure_speech_key:
            return {"success": False, "text": "", "duration_ms": 0, "error": "Azure Speech key not configured"}

        start = time.time()
        try:
            speech_config = speechsdk.SpeechConfig(
                subscription=self.config.azure_speech_key,
                region=self.config.azure_speech_region,
            )
            speech_config.speech_recognition_language = language

            audio_config = speechsdk.audio.AudioConfig(filename=audio_path)
            recognizer = speechsdk.SpeechRecognizer(
                speech_config=speech_config,
                audio_config=audio_config,
            )

            result = recognizer.recognize_once_async().get()

            if result.reason == speechsdk.ResultReason.RecognizedSpeech:
                duration = (time.time() - start) * 1000
                return {"success": True, "text": result.text, "duration_ms": duration, "error": ""}
            elif result.reason == speechsdk.ResultReason.NoMatch:
                return {"success": False, "text": "", "duration_ms": 0, "error": "No speech recognized"}
            else:
                return {"success": False, "text": "", "duration_ms": 0, "error": f"Recognition failed: {result.reason}"}
        except Exception as e:
            return {"success": False, "text": "", "duration_ms": 0, "error": str(e)}


class VoskSTTProvider(STTProvider):
    """Local offline STT using Vosk."""

    name = "local"
    display_name = "Local (Vosk)"

    def __init__(self, config: APIConfig):
        super().__init__(config)
        self._model = None

    def _get_model(self):
        if self._model is None:
            try:
                from vosk import Model
                # Try common model paths
                model_paths = [
                    os.path.join(os.path.dirname(__file__), "models", "vosk-model-small-en-us-0.15"),
                    os.path.expanduser("~/.vosk/model"),
                    "/usr/share/vosk/model",
                ]
                for path in model_paths:
                    if os.path.exists(path):
                        self._model = Model(path)
                        break
                if self._model is None:
                    raise FileNotFoundError("Vosk model not found. Download from https://alphacephei.com/vosk/models")
            except ImportError:
                raise ImportError("vosk package not installed")
        return self._model

    def transcribe(self, audio_path: str, language: str = "en-US") -> dict:
        try:
            from vosk import KaldiRecognizer
            import wave
        except ImportError:
            return {"success": False, "text": "", "duration_ms": 0, "error": "vosk not installed"}

        start = time.time()
        try:
            model = self._get_model()
            wf = wave.open(audio_path, "rb")

            # Convert to 16-bit mono 16kHz if needed
            if wf.getframerate() != 16000 or wf.getnchannels() != 1:
                wf.close()
                # Use pydub to convert
                try:
                    from pydub import AudioSegment
                    audio = AudioSegment.from_file(audio_path)
                    audio = audio.set_frame_rate(16000).set_channels(1).set_sample_width(2)
                    import tempfile
                    tmp = tempfile.mktemp(suffix=".wav")
                    audio.export(tmp, format="wav")
                    wf = wave.open(tmp, "rb")
                except ImportError:
                    return {"success": False, "text": "", "duration_ms": 0, "error": "pydub needed for audio conversion"}

            rec = KaldiRecognizer(model, wf.getframerate())
            rec.SetWords(True)

            text_parts = []
            while True:
                data = wf.readframes(4000)
                if len(data) == 0:
                    break
                if rec.AcceptWaveform(data):
                    import json
                    result = json.loads(rec.Result())
                    if result.get("text"):
                        text_parts.append(result["text"])

            import json
            final = json.loads(rec.FinalResult())
            if final.get("text"):
                text_parts.append(final["text"])

            wf.close()
            duration = (time.time() - start) * 1000
            return {"success": True, "text": " ".join(text_parts), "duration_ms": duration, "error": ""}
        except Exception as e:
            return {"success": False, "text": "", "duration_ms": 0, "error": str(e)}


class STTProviderManager:
    """Manages all STT providers."""

    def __init__(self, config: APIConfig):
        self.config = config
        self.providers: dict[str, STTProvider] = {
            "openai": OpenAISTTProvider(config),
            "google": GoogleSTTProvider(config),
            "azure": AzureSTTProvider(config),
            "local": VoskSTTProvider(config),
        }

    def get_available_providers(self) -> list[str]:
        return [name for name, provider in self.providers.items() if provider.is_available()]

    def transcribe(self, provider_name: str, audio_path: str, language: str = "en-US") -> dict:
        provider = self.providers.get(provider_name)
        if not provider:
            return {"success": False, "text": "", "duration_ms": 0, "error": f"Unknown provider: {provider_name}"}
        return provider.transcribe(audio_path, language)

    def transcribe_all(self, audio_path: str, language: str = "en-US") -> dict:
        results = {}
        for name, provider in self.providers.items():
            if provider.is_available():
                results[name] = provider.transcribe(audio_path, language)
        return results
