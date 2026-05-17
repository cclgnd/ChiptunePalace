
You are working on an existing Windows project in `D:\chiptunepalace`.

Your job is to first discover the real current state of the project, then cleanly reorganize it, and then complete the app.

Project/app goal:
- App name: `ChipTunePalace`
- Platform: Google AI Studio / Antigravity app workflow
- Engine/model context: Gemini 3 Flash
- The app is a simple chiptunes player
- Audio backend must use VLC engine/backend
- The app includes an integrated scraping/downloading engine to collect music files from websites
- The player UI must display a selector with:
  - console/system name
  - game name
  - track/file name
- The player should follow common multimedia player behavior/rules:
  - play/pause
  - stop
  - next/previous track
  - seek/progress
  - volume
  - current track info
  - playlist or queue behavior where appropriate
- Include Libretro integration to show:
  - game cover image
  - 1 in-game screenshot
- If anything is unclear, missing, contradictory, or risky, ask the user before making assumptions

Primary workflow:
1. Inspect the entire folder `D:\chiptunepalace`
2. Determine:
   - what framework/language is being used
   - what parts are already implemented
   - what parts are broken, duplicated, obsolete, or abandoned
   - whether there are multiple partial app attempts
   - current build/run status
3. Produce a concise project status summary before major changes
4. Reorganize the project into a clean, maintainable structure
5. Preserve useful work, archive or isolate dead/obsolete code instead of blindly deleting it
6. Complete the app according to the target behavior
7. Test the app and verify core flows
8. Report what was changed and what still needs user input

Important behavior rules:
- Do not assume the current folder structure is correct
- Do not assume the existing code is authoritative
- Prefer understanding before rewriting
- Be careful with destructive operations
- Move uncertain/legacy material into clearly named archive folders
- Keep a changelog of important restructuring decisions
- If scraping targets, legality, metadata sources, or Libretro source/details are ambiguous, ask the user
- If VLC backend integration is incomplete, implement it properly using the most suitable approach for the detected stack
- If multiple UI stacks exist, choose one and explain why
- If the app cannot be completed without choosing between alternatives, stop and ask the user

Required deliverables:
- A short “current state assessment”
- A proposed cleaned folder structure
- A list of preserved vs archived components
- The completed app implementation
- Notes on VLC integration
- Notes on scraping engine implementation
- Notes on Libretro metadata/image integration
- A final “open questions / needs confirmation” section if anything remains unclear

Functional expectations for the completed app:
- Scan or import scraped/local music files
- Organize them by console > game > track
- Let the user browse/select and play tracks
- Display playback controls and progress
- Show metadata for current selection if available
- Show game cover + one screenshot when available through Libretro-related metadata sources
- Handle missing metadata/images gracefully
- Handle unsupported or failed files gracefully
- Keep the UI simple and clean

Technical expectations:
- Detect and use the project’s existing stack if sensible
- If the existing stack is chaotic or unsuitable, recommend a minimal stable stack and ask before a full migration
- Keep implementation modular:
  - UI/player
  - VLC playback service
  - scraping/import service
  - metadata/image service
  - data model/indexing
- Add clear comments only where useful
- Add a README or update it with run/build instructions
- Add a TODO/Open Issues section where needed

Before coding heavily, start by:
1. auditing `D:\chiptunepalace`
2. summarizing the actual state
3. identifying the main app entrypoint
4. identifying duplicate/unused folders
5. asking the user any blocking questions

If you find incomplete instructions, stop and ask the user rather than inventing requirements.

If you want, I can also turn this into:
1. a shorter version for Antigravity,
2. a stricter “step-by-step agent contract” version,
or 3. a Windows-focused version with explicit file operation guidance.