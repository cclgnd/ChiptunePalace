# PROJECT CONTROLLER DIRECTIVE: CHIPTUNEPALACE_PLAYER

## WORKSPACE & BOUNDARIES
- ACTIVE DIR: `./chiptunepalace/` ONLY. Zero writes outside.
- REFERENCE: `D:\MusicDupReview` (VLC engine + chiptunes bridge). READ-ONLY. Verify paths before access.
- CORE STACK: PySide6 GUI, SQLite (WAL mode), adaptive web scrapers, non-stop shuffle queue, SNES 16-bit pixel theme. \n- Autonomously proceed with Phase 1 steps until halted by user input.
- Autonomously proceed with Phase 1 steps until halted by user input.

## AGENT LIFECYCLE PROTOCOL
### [FIRST_AGENT_TRIGGER]
Execute ONLY when `./chiptunepalace/STATE.md` does not exist.
1. Create directory tree per architecture spec.
2. Initialize `./chiptunepalace/STATE.md` with baseline schema.
3. Generate `./chiptunepalace/db/schema.sql` + ORM stub.
4. Generate `./chiptunepalace/gui/main_window.py` skeleton (pixel theme, no logic).
5. Output Phase 1 deliverables. Update `STATE.md` with `[CHECKPOINT]` + `[PENDING]`.
6. Halt. Await explicit resume command.

### [RETURNING_AGENT_TRIGGER]
Execute ONLY when `./chiptunepalace/STATE.md` exists.
1. Read `STATE.md`. Extract `[LAST_CHECKPOINT]`, `[PENDING]`, `[KNOWN_ISSUES]`.
2. Verify workspace matches checkpoint state. Skip completed phases.
3. Resume exact task from `[PENDING]` list. Do not rewrite finished artifacts.
4. Execute Phase 2/3 pipeline. Update `STATE.md` before halting.
5. Output `[HANDOFF_COMPLETE]` + next-step instructions.

## STATE & HANDOFF SYSTEM
- Single source of truth: `./chiptunepalace/STATE.md`
- Agents MUST read `STATE.md` at session start. Agents MUST update `STATE.md` at session end.
- State format: