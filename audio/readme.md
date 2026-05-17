# audio/ Module — Architecture Overview

This folder contains the new real-time chip emulation audio system for ChiptunePalace.

## Folder Structure & Responsibility
- **backends/** — Concrete emulator implementations (GmeBackend, VgmBackend, etc.). Each must follow backends/SPECIFICATION.md.
- **core/** — Main AudioEngine (Qt-compatible), FormatDetector, track loading logic.
- **output/** — Low-latency audio output layer (sounddevice callback preferred).
- **docs/** — Architecture, vision, and roadmap.

## Core Principles (Read This Every Time)
- In-memory first: Prefer loading directly from bytes (ZIP member data).
- Real emulation over decoding: Use libraries that emulate the original sound chips.
- Minimal temporary files: Only use temp files for formats that absolutely cannot be handled in memory.
- Progressive enhancement: Start with libgme, then add specialized backends.
- GUI compatibility: The public API of AudioEngine must not break existing UI code.

See docs/AUDIO_ENGINE_VISION.md for the full permanent directive.
See backends/SPECIFICATION.md and core/SPECIFICATION.md for strict technical contracts.