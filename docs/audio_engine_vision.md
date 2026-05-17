# ChiptunePalace Audio Engine Vision (Permanent Directive)

## Core Objective
Replace the current WAV-transcoding pipeline (VGMPlay, vgmstream, nsf2wav, etc.) with real-time chip emulation engines. The system must generate audio samples on-the-fly from emulated sound chips instead of writing large temporary WAV files.

## Non-Negotiable Goals
- True live synthesis / chip emulation (not decoded recordings).
- Full in-memory support for ZIP members (critical for "ZIP Streaming" feature). Never extract to disk when bytes are available.
- High authenticity/fidelity to original console sound chips.
- No more sidecar .wav files polluting user folders.
- Drastically reduce temporary file I/O.
- Maintain full compatibility with existing Qt GUI (same signals: playback_state_changed, track_finished, error_occurred, position_changed, etc.).

## Preferred Technology Stack (in order)
1. libgme (Game Music Emu) via ctypes — FIRST backend to implement. Supports VGM/VGZ, NSF, SPC, GBS, HES, and many others.
2. libvgm for higher-fidelity VGM/Genesis/arcade chips (Phase 2).
3. sounddevice (with callback + numpy float32 buffers) as primary audio output. VLC only as fallback for unsupported formats.
4. numpy for all sample buffers (float32, -1.0..1.0 range, stereo preferred).

## Strict Rules
- Never fall back to mock sine wave for supported formats. Only use diagnostic tone when absolutely no backend can load the file.
- All backends MUST support loading from bytes (in-memory).
- Emulators must expose duration, seeking, volume, and (when possible) per-channel muting.
- Keep code clean, well-typed, and heavily commented about how the emulation works.

## Success Criteria
- A .vgz from a ZIP member plays with zero temporary WAV files created.
- Seeking is near-instant.
- CPU usage is reasonable.
- Sound quality is at least as good as previous VGMPlay path, preferably better.
- Logs clearly state which real emulator backend is active ("Using GmeBackend for SPC emulation").

This file is authoritative. All other audio-related development must align with this vision.