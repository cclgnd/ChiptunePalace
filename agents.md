# AGENTS.md — Instructions for AI Coding Agents (Gemini, etc.)

This repository uses persistent Markdown specifications to guide development.

**Primary Directive:**
Before writing or modifying any code in the audio system, you MUST read:
- docs/AUDIO_ENGINE_VISION.md
- chiptunepalace/audio/README.md
- All SPECIFICATION.md files in the audio/ folder

The goal is a real-time chip emulation engine (libgme first) that eliminates large temporary WAV files and supports true in-memory playback from ZIP archives.

Never re-introduce old transcoding patterns unless explicitly approved.
Always follow the SPECIFICATION.md contracts exactly.