"""
Meta MMS (Massively Multilingual Speech) Providers.

TTS: facebook/mms-tts-khm  — Khmer TTS (VitsModel)
STT: facebook/mms-300m     — 1000+ language STT (Wav2Vec2ForCTC + per-language adapter)

Models are downloaded once from HuggingFace and cached locally (~130 MB TTS, ~1.2 GB STT).
Both run fully offline after the first download.
"""

import os
import time
import tempfile
import threading
from pathlib import Path
from typing import Optional

# ──────────────────────────────────────────────────────────────────────────────
# Language map: language code used in the app → MMS adapter id
# ──────────────────────────────────────────────────────────────────────────────
MMS_LANG_MAP = {
    "km-KH": "khm",
    "en-US": "eng",
    "en-GB": "eng",
    "fr-FR": "fra",
    "de-DE": "deu",
    "es-ES": "spa",
    "ja-JP": "jpn",
    "zh-CN": "zho",
}

MMS_TTS_MODELS = {
    "khm": "facebook/mms-tts-khm",
    "eng": "facebook/mms-tts-eng",
    "fra": "facebook/mms-tts-fra",
    "deu": "facebook/mms-tts-deu",
    "spa": "facebook/mms-tts-spa",
}

MMS_STT_MODEL = "facebook/mms-300m"


# ──────────────────────────────────────────────────────────────────────────────
# MMS TTS Provider
# ──────────────────────────────────────────────────────────────────────────────
class MMSTTSProvider:
    """
    Meta MMS Text-to-Speech — runs fully offline via HuggingFace transformers.
    Uses VitsModel (facebook/mms-tts-{lang}).
    """

    name = "mms_tts"
    display_name = "Meta MMS TTS"

    def __init__(self):
        self._models: dict = {}        # lang_code -> (model, tokenizer)
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        try:
            import transformers  # noqa
            import torch         # noqa
            import scipy         # noqa
            return True
        except ImportError:
            return False

    def _load_model(self, lang: str):
        """Load and cache the VITS model for a given MMS lang code."""
        if lang in self._models:
            return self._models[lang]

        model_id = MMS_TTS_MODELS.get(lang, f"facebook/mms-tts-{lang}")

        from transformers import VitsModel, AutoTokenizer
        tokenizer = AutoTokenizer.from_pretrained(model_id)
        model = VitsModel.from_pretrained(model_id)
        model.eval()

        with self._lock:
            self._models[lang] = (model, tokenizer)
        return model, tokenizer

    def synthesize(self, text: str, language: str, output_path: str) -> dict:
        """
        Synthesize speech.
        language: app language code e.g. 'km-KH' or MMS lang code e.g. 'khm'
        """
        if not self.is_available():
            return {
                "success": False, "duration_ms": 0,
                "error": "transformers / torch / scipy not installed. "
                         "Run: pip install transformers torch scipy"
            }

        start = time.time()
        try:
            import torch
            import scipy.io.wavfile
            import numpy as np

            # Resolve language code
            lang = MMS_LANG_MAP.get(language, language)
            if len(lang) > 3:
                lang = "khm"  # safe default for unknown codes

            model, tokenizer = self._load_model(lang)

            inputs = tokenizer(text, return_tensors="pt")
            with torch.no_grad():
                output = model(**inputs).waveform

            waveform = output.squeeze().numpy().astype(np.float32)
            sample_rate = model.config.sampling_rate

            # Normalise to int16 for WAV
            max_val = np.abs(waveform).max()
            if max_val > 0:
                waveform = waveform / max_val
            waveform_int16 = (waveform * 32767).astype(np.int16)

            scipy.io.wavfile.write(output_path, rate=sample_rate, data=waveform_int16)

            duration = (time.time() - start) * 1000
            return {"success": True, "duration_ms": duration, "error": "",
                    "output_path": output_path, "sample_rate": sample_rate}

        except Exception as e:
            return {"success": False, "duration_ms": 0, "error": str(e)}


# ──────────────────────────────────────────────────────────────────────────────
# MMS STT Provider
# ──────────────────────────────────────────────────────────────────────────────
class MMSSTTProvider:
    """
    Meta MMS Speech-to-Text — runs fully offline via HuggingFace transformers.
    Uses Wav2Vec2ForCTC (facebook/mms-300m) with per-language adapters.
    Supports 1000+ languages including Khmer.
    """

    name = "mms_stt"
    display_name = "Meta MMS STT"

    def __init__(self):
        self._model = None
        self._processor = None
        self._current_lang: Optional[str] = None
        self._lock = threading.Lock()

    def is_available(self) -> bool:
        try:
            import transformers  # noqa
            import torch         # noqa
            import soundfile     # noqa
            return True
        except ImportError:
            return False

    def _load_model(self, lang: str):
        """Load base model + switch adapter to target language."""
        from transformers import Wav2Vec2ForCTC, Wav2Vec2Processor
        import torch

        with self._lock:
            if self._model is None:
                self._processor = Wav2Vec2Processor.from_pretrained(MMS_STT_MODEL)
                self._model = Wav2Vec2ForCTC.from_pretrained(MMS_STT_MODEL)
                self._model.eval()

            if self._current_lang != lang:
                self._processor.tokenizer.set_target_lang(lang)
                self._model.load_adapter(lang)
                self._current_lang = lang

        return self._model, self._processor

    def transcribe(self, audio_path: str, language: str = "km-KH") -> dict:
        """
        Transcribe audio file.
        language: app language code e.g. 'km-KH' or MMS lang code e.g. 'khm'
        """
        if not self.is_available():
            return {
                "success": False, "text": "", "duration_ms": 0,
                "error": "transformers / torch / soundfile not installed."
            }

        start = time.time()
        try:
            import torch
            import soundfile as sf
            import numpy as np

            lang = MMS_LANG_MAP.get(language, language)
            if len(lang) > 3:
                lang = "khm"

            model, processor = self._load_model(lang)

            # Load audio — resample to 16 kHz if needed
            audio, sample_rate = sf.read(audio_path, dtype="float32")
            if audio.ndim > 1:
                audio = audio.mean(axis=1)  # stereo → mono

            if sample_rate != 16000:
                from scipy.signal import resample
                target_len = int(len(audio) * 16000 / sample_rate)
                audio = resample(audio, target_len).astype(np.float32)
                sample_rate = 16000

            inputs = processor(audio, sampling_rate=16000, return_tensors="pt")

            with torch.no_grad():
                logits = model(**inputs).logits

            predicted_ids = torch.argmax(logits, dim=-1)
            text = processor.batch_decode(predicted_ids)[0]

            duration = (time.time() - start) * 1000
            return {"success": True, "text": text, "duration_ms": duration, "error": ""}

        except Exception as e:
            return {"success": False, "text": "", "duration_ms": 0, "error": str(e)}


# Module-level singletons — shared across tabs so the model loads only once
_mms_tts_instance: Optional[MMSTTSProvider] = None
_mms_stt_instance: Optional[MMSSTTProvider] = None


def get_mms_tts() -> MMSTTSProvider:
    global _mms_tts_instance
    if _mms_tts_instance is None:
        _mms_tts_instance = MMSTTSProvider()
    return _mms_tts_instance


def get_mms_stt() -> MMSSTTProvider:
    global _mms_stt_instance
    if _mms_stt_instance is None:
        _mms_stt_instance = MMSSTTProvider()
    return _mms_stt_instance
