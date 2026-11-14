# AI-assisted: generated with Claude Code (pending Ravi review)
"""Voice spike: Piper TTS (pt-BR) -> OGG/Opus -> faster-whisper STT, fully offline.

Proves the voice round trip planned for the Telegram bot (front B) without any bot,
network service or key. Run from this folder after the setup in README.md:

    .venv/bin/python spike.py "Amanhã deve chover pouco em Aracaju."
"""

from __future__ import annotations

import argparse
import os
import time
import wave
from pathlib import Path

import av
import numpy as np

DEFAULT_TEXT = "Bom dia! A umidade do solo está baixa. Vale a pena irrigar o milho hoje à tarde."
VOICE_DIR = Path(os.environ.get("PIPER_VOICE_DIR", Path.home() / ".local/share/space-apps-voice/piper"))
VOICE = os.environ.get("PIPER_VOICE", "pt_BR-faber-medium")
OUT_DIR = Path(__file__).parent / "out"  # git-ignored


def synthesize(text: str, wav_path: Path) -> float:
    from piper import PiperVoice

    start = time.perf_counter()
    voice = PiperVoice.load(VOICE_DIR / f"{VOICE}.onnx")
    with wave.open(str(wav_path), "wb") as wav_file:
        voice.synthesize_wav(text, wav_file)
    return time.perf_counter() - start


def wav_to_ogg_opus(wav_path: Path, ogg_path: Path) -> None:
    """Telegram voice notes are OGG/Opus; Opus wants 48 kHz, so resample on the way."""
    with wave.open(str(wav_path), "rb") as wav_file:
        rate = wav_file.getframerate()
        samples = np.frombuffer(wav_file.readframes(wav_file.getnframes()), dtype=np.int16)
    with av.open(str(ogg_path), "w", format="ogg") as container:
        stream = container.add_stream("libopus", rate=48000)
        stream.layout = "mono"
        stream.bit_rate = 32000
        frame = av.AudioFrame.from_ndarray(samples.reshape(1, -1), format="s16", layout="mono")
        frame.sample_rate = rate
        resampler = av.AudioResampler(format="s16", layout="mono", rate=48000)
        for resampled in resampler.resample(frame) + resampler.resample(None):
            for packet in stream.encode(resampled):
                container.mux(packet)
        for packet in stream.encode(None):
            container.mux(packet)


def transcribe(ogg_path: Path, model_size: str) -> tuple[str, float, float]:
    from faster_whisper import WhisperModel

    start = time.perf_counter()
    model = WhisperModel(model_size, device="cpu", compute_type="int8")
    loaded = time.perf_counter() - start
    start = time.perf_counter()
    segments, _ = model.transcribe(str(ogg_path), language="pt", beam_size=1, vad_filter=True)
    text = " ".join(segment.text.strip() for segment in segments)
    return text, loaded, time.perf_counter() - start


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    parser.add_argument("text", nargs="?", default=DEFAULT_TEXT)
    parser.add_argument("--model", default="small", help="faster-whisper size (small or medium for a CPU server)")
    args = parser.parse_args()

    OUT_DIR.mkdir(exist_ok=True)
    wav_path, ogg_path = OUT_DIR / "reply.wav", OUT_DIR / "reply.ogg"

    tts_s = synthesize(args.text, wav_path)
    with wave.open(str(wav_path), "rb") as wav_file:
        audio_s = wav_file.getnframes() / wav_file.getframerate()
    wav_to_ogg_opus(wav_path, ogg_path)
    heard, load_s, stt_s = transcribe(ogg_path, args.model)

    print(f"text in : {args.text}")
    print(f"TTS     : Piper {VOICE}, {audio_s:.1f} s of audio in {tts_s:.1f} s (incl. model load)")
    print(f"OGG/Opus: {ogg_path.stat().st_size / 1024:.1f} KiB ({ogg_path})")
    print(f"STT     : faster-whisper {args.model} cpu/int8, load {load_s:.1f} s, transcribe {stt_s:.1f} s")
    print(f"text out: {heard}")


if __name__ == "__main__":
    main()
