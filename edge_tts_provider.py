"""
Edge TTS Provider - Free Microsoft Text-to-Speech via Edge online voices.
No API key needed! Works out of the box.

Uses the edge-tts library which connects to Microsoft Edge's free TTS endpoint.
"""

import asyncio
import time
from typing import Optional

from config import APIConfig


# Available Microsoft Edge voices (free!)
EDGE_VOICES = {
    # English voices
    "en-US-AriaNeural": "English (US) - Aria (Female)",
    "en-US-JennyNeural": "English (US) - Jenny (Female)",
    "en-US-GuyNeural": "English (US) - Guy (Male)",
    "en-US-SaraNeural": "English (US) - Sara (Female)",
    "en-US-DavisNeural": "English (US) - Davis (Male)",
    "en-US-AmberNeural": "English (US) - Amber (Female)",
    "en-US-AndrewNeural": "English (US) - Andrew (Male)",
    "en-US-AvaNeural": "English (US) - Ava (Female)",
    "en-US-ChristopherNeural": "English (US) - Christopher (Male)",
    "en-US-EmmaNeural": "English (US) - Emma (Female)",
    "en-US-MichelleNeural": "English (US) - Michelle (Female)",
    "en-US-RogerNeural": "English (US) - Roger (Male)",
    "en-US-SteffanNeural": "English (US) - Steffan (Male)",
    "en-GB-SoniaNeural": "English (UK) - Sonia (Female)",
    "en-GB-RyanNeural": "English (UK) - Ryan (Male)",
    "en-AU-NatashaNeural": "English (AU) - Natasha (Female)",
    "en-AU-WilliamNeural": "English (AU) - William (Male)",
    "en-CA-ClaraNeural": "English (CA) - Clara (Female)",
    "en-CA-LiamNeural": "English (CA) - Liam (Male)",

    # Other popular languages
    "km-KH-PisethNeural": "Khmer - Piseth (Male)",
    "km-KH-SreymomNeural": "Khmer - Sreymom (Female)",
    "fr-FR-DeniseNeural": "French - Denise (Female)",
    "fr-FR-HenriNeural": "French - Henri (Male)",
    "de-DE-KatjaNeural": "German - Katja (Female)",
    "de-DE-ConradNeural": "German - Conrad (Male)",
    "es-ES-ElviraNeural": "Spanish - Elvira (Female)",
    "es-ES-AlvaroNeural": "Spanish - Alvaro (Male)",
    "ja-JP-NanamiNeural": "Japanese - Nanami (Female)",
    "ja-JP-KeitaNeural": "Japanese - Keita (Male)",
    "ko-KR-SunHiNeural": "Korean - SunHi (Female)",
    "ko-KR-InJoonNeural": "Korean - InJoon (Male)",
    "zh-CN-XiaoxiaoNeural": "Chinese - Xiaoxiao (Female)",
    "zh-CN-YunxiNeural": "Chinese - Yunxi (Male)",
    "vi-VN-HoaiMyNeural": "Vietnamese - HoaiMy (Female)",
    "vi-VN-NamMinhNeural": "Vietnamese - NamMinh (Male)",
    "th-TH-PremwadeeNeural": "Thai - Premwadee (Female)",
    "th-TH-NiwatNeural": "Thai - Niwat (Male)",
    "id-ID-GadisNeural": "Indonesian - Gadis (Female)",
    "id-ID-ArdiNeural": "Indonesian - Ardi (Male)",
    "ru-RU-SvetlanaNeural": "Russian - Svetlana (Female)",
    "ru-RU-DmitryNeural": "Russian - Dmitry (Male)",
    "ar-SA-ZariyahNeural": "Arabic - Zariyah (Female)",
    "ar-SA-HamedNeural": "Arabic - Hamed (Male)",
    "hi-IN-SwaraNeural": "Hindi - Swara (Female)",
    "hi-IN-MadhurNeural": "Hindi - Madhur (Male)",
}


class EdgeTTSProvider:
    """
    Free Microsoft Edge TTS - no API key required!
    Uses Microsoft's public Edge TTS endpoint.
    """

    name = "edge"
    display_name = "Edge TTS (Free)"

    def __init__(self, config: APIConfig):
        self.config = config
        self._available = None

    def is_available(self) -> bool:
        """Check if edge-tts is installed."""
        if self._available is not None:
            return self._available
        try:
            import edge_tts
            self._available = True
        except ImportError:
            self._available = False
        return self._available

    def get_voices(self) -> dict:
        """Return available voices."""
        return EDGE_VOICES

    def synthesize(self, text: str, voice: str, output_path: str) -> dict:
        """
        Synthesize speech using Edge TTS (free, no key needed).
        Returns: {"success": bool, "duration_ms": float, "error": str, "output_path": str}
        """
        try:
            import edge_tts
        except ImportError:
            return {
                "success": False,
                "duration_ms": 0,
                "error": "edge-tts not installed. Run: pip install edge-tts",
                "output_path": ""
            }

        start = time.time()
        try:
            async def _synthesize():
                communicate = edge_tts.Communicate(text, voice)
                await communicate.save(output_path)

            # Use a brand-new event loop to avoid conflicts with Qt's event loop
            # asyncio.run() can fail when called from inside a QThread
            loop = asyncio.new_event_loop()
            try:
                loop.run_until_complete(_synthesize())
            finally:
                loop.close()

            duration = (time.time() - start) * 1000
            return {
                "success": True,
                "duration_ms": duration,
                "error": "",
                "output_path": output_path
            }
        except Exception as e:
            return {
                "success": False,
                "duration_ms": 0,
                "error": str(e),
                "output_path": ""
            }
