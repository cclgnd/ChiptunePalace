## Audio Engine Architecture (2026)

The audio system has been redesigned for real chip emulation.

See:
- `docs/AUDIO_ENGINE_VISION.md` — overall goal
- `chiptunepalace/audio/README.md` — module overview
- `chiptunepalace/audio/backends/SPECIFICATION.md` — strict backend contract (most important)

The old WAV-transcoding pipeline (VGMPlay/vgmstream) is deprecated for all formats supported by libgme. The new system loads tracks in memory and generates samples in real time using emulated sound chips.