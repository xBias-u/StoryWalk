import shutil
import subprocess
from tempfile import TemporaryDirectory
from pathlib import Path


class AppleSpeechError(RuntimeError):
    """Raised when the local macOS MVP voice cannot produce an MP3."""


class AppleSpeechClient:
    def __init__(self, voice='Milena', rate=165):
        self.voice = voice
        self.rate = rate

    def synthesize(self, text, language_code='ru'):
        text = text.strip()
        if not text:
            raise AppleSpeechError('The narration text is empty')
        if not shutil.which('say') or not shutil.which('ffmpeg'):
            raise AppleSpeechError('macOS say and ffmpeg are required for local MVP audio')

        with TemporaryDirectory() as temp_dir:
            aiff_path = Path(temp_dir) / 'narration.aiff'
            mp3_path = Path(temp_dir) / 'narration.mp3'
            try:
                subprocess.run(
                    ['say', '-v', self.voice, '-r', str(self.rate), '-o', str(aiff_path), text],
                    check=True,
                    capture_output=True,
                    timeout=120,
                )
                subprocess.run(
                    [
                        'ffmpeg', '-loglevel', 'error', '-y', '-i', str(aiff_path),
                        '-codec:a', 'libmp3lame', '-b:a', '128k', '-ar', '44100', str(mp3_path),
                    ],
                    check=True,
                    capture_output=True,
                    timeout=120,
                )
            except (subprocess.CalledProcessError, subprocess.TimeoutExpired) as exc:
                raise AppleSpeechError('The local MVP voice could not generate audio') from exc

            audio = mp3_path.read_bytes() if mp3_path.exists() else b''
            if not audio:
                raise AppleSpeechError('The local MVP voice returned an empty audio file')
            return audio
