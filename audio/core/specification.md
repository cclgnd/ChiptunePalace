# core/SPECIFICATION.md

This folder contains the main orchestration logic.

## Components
- AudioEngine.py → Main class (inherits from QObject). Must emit the same Qt signals as the old version so GUI requires zero changes.
- format_detector.py → Chooses correct backend based on file extension/magic bytes. Prefer real emulator over VLC.
- Track metadata and state management.

## Required Behavior
- On load_track(path_or_bytes, member_name=None):
  - If member_name is given, load ZIP member directly into memory (bytes).
  - Detect format.
  - Try real emulator backend first.
  - Only if no emulator supports it, fall back to old VLC + transcoding path (temporary measure).
- Audio output is delegated to audio/output/ layer.
- Log clearly: "Loaded track with GmeBackend (real chip emulation)" or "Falling back to VLC transcoding".

Do not re-introduce VGMPlay.ini modification, sidecar WAV files, or heuristic WAV size polling.