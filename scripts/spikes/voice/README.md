<!-- AI-assisted: generated with Claude Code (pending Ravi review) -->
# Voice spike: Piper TTS + faster-whisper STT (offline)

Proves the voice round trip decided for the Telegram bot (front B, see [docs/team/decisions.md](../../../docs/team/decisions.md)): **text → Piper pt-BR speech → OGG/Opus (Telegram's voice format) → faster-whisper → text**, on CPU, with no bot, no network service and no API key. It is a throwaway spike, not product code.

## Run

```bash
cd scripts/spikes/voice
uv venv -p 3.12 .venv && uv pip install --python .venv/bin/python -r requirements.txt
.venv/bin/python -m piper.download_voices --download-dir ~/.local/share/space-apps-voice/piper pt_BR-faber-medium   # once, ~63 MB
.venv/bin/python spike.py "Quero plantar feijão no próximo mês. Vai ter chuva suficiente?"
```

The first run downloads the Whisper model from Hugging Face (`small` ≈ 0.5 GB, `medium` ≈ 1.5 GB). Set `HF_HOME` to keep it outside the repo. Outputs go to `out/` (git-ignored). No `ffmpeg` needed: PyAV encodes Opus.

## Results (Nov 14, 2026, laptop CPU, int8)

| Step | Result |
|---|---|
| Piper `pt_BR-faber-medium` | 5.5 s of speech in 0.4 s (incl. model load) |
| OGG/Opus 48 kHz mono, 32 kbit/s | 20.8 KiB for 5.5 s |
| Whisper `small`, CPU int8 | load 1.1 s, transcribe 1.2 s; one word wrong (*milho* → *mio*) |
| Whisper `medium`, CPU int8 | transcribe 3.5 s, exact text (first load is slow: it includes the model download) |
| Second phrase, `small` | "Quero plantar feijão no próximo mês. Vai ter chuva suficiente" (only the "?" lost) |

Takeaways for the PRD: `small` is fast enough for short voice notes; `medium` is more accurate for crop names at ~3× the time. Both run without a GPU.

**License note (decide before product code):** `piper-tts` 1.8.0 (the maintained `piper1-gpl` project) is **GPL-3.0-or-later**, while this repo is Apache-2.0. Running it as a separate process or service is the usual way to keep the boundary clean; importing it into product code would pull GPL terms in. Check the `pt_BR-faber-medium` voice's model card for its own license too. faster-whisper and the Whisper weights are MIT.

## Credits

- [Piper](https://github.com/OHF-Voice/piper1-gpl) and the `pt_BR-faber-medium` voice from [rhasspy/piper-voices](https://huggingface.co/rhasspy/piper-voices).
- [faster-whisper](https://github.com/SYSTRAN/faster-whisper) (CTranslate2 port of OpenAI Whisper).
