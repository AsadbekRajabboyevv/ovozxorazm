import os
import asyncio
from pathlib import Path
from pydub import AudioSegment
from bot.config import VOICES_DIR

try:
    import imageio_ffmpeg
    ffmpeg_exe = imageio_ffmpeg.get_ffmpeg_exe()
    if ffmpeg_exe and os.path.exists(ffmpeg_exe):
        AudioSegment.converter = ffmpeg_exe
except Exception:
    pass

class AudioService:
    @staticmethod
    async def convert_mp3_to_voice_ogg(input_path: str, output_name: str) -> str:
        output_path = os.path.join(VOICES_DIR, f"{output_name}.ogg")

        def _convert():
            audio = AudioSegment.from_file(input_path)
            audio = audio.set_frame_rate(48000).set_channels(1)
            audio.export(output_path, format="ogg", codec="libopus")
            return output_path

        loop = asyncio.get_running_loop()
        try:
            res = await loop.run_in_executor(None, _convert)
            return res
        except Exception:
            def _fallback_convert():
                audio = AudioSegment.from_file(input_path)
                audio.export(output_path, format="ogg")
                return output_path
            return await loop.run_in_executor(None, _fallback_convert)

    @staticmethod
    def cleanup_file(file_path: str):
        if os.path.exists(file_path):
            try:
                os.remove(file_path)
            except Exception:
                pass
