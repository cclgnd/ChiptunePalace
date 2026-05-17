# output/SPECIFICATION.md

Responsible for sending samples from an active EmulatorBackend to the sound card.

Preferred implementation:
- Use sounddevice.OutputStream with a callback.
- Callback pulls samples via backend.generate_samples().
- Target 44100 or 48000 Hz, low latency (try blocksize=512 or 1024).
- Graceful error handling and fallback to VLC if sounddevice fails.

Do not use VLC as primary output for emulated formats. VLC should only be used for unsupported media (mp3, flac, already-rendered tracks).