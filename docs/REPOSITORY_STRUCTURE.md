# Repository Structure

This document defines where files should live so future AI sessions do not confuse retired plans, temporary outputs, and current project documents.

## Root

Keep only high-level entrypoints and active coordination files in the repository root.

- `README.md`: external overview
- `PROJECT_CONTEXT.md`: first file for new AI sessions
- `project-handoff.md`: long coordination log and session history
- `DATABASE_SETUP.md`: compatibility pointer to `docs/current/DATABASE_SETUP.md`
- `prototype_all_in_one.py`: central prototype used by current scripts
- `index.html`, `vercel.json`: dashboard deployment entrypoints
- `requirements.txt`, `pyproject.toml`, `uv.lock`: environment metadata

Avoid adding one-off handoff notes, scratch scripts, generated reports, test scripts, or tool outputs to the root.

## Current Documentation

Use `docs/current/` for the active early-warning project direction.

- `PROJECT_PLAN.md`
- `VALIDATION_PLAN.md`
- `DATA_COLLECTION_GUIDE.md`
- `LLM_SYSTEM_SUMMARY.md`
- `DATABASE_SETUP.md`
- `PRESENTATION_PORTFOLIO_NARRATIVE.md`
- `PORTFOLIO_AND_REPORT_GUIDE.md`

If a document describes what the project is now, put it here.

## Session Prompts and Handoffs

Use `docs/SESSION_PROMPTS.md` for reusable role prompts.

Use `docs/handoff/` for completed session handoff reports, such as DB-track, LLM/dashboard-track, or comprehensive handoff notes. Short message artifacts from other agents go under `docs/handoff/agent_messages/`.

## History and Archive

Use `docs/history/` for concise narrative documents explaining major pivots.

- prediction approach retired
- chatbot pivot parked
- project evolution timeline

Use `docs/archive/` for old planning files, retired handoff documents, legacy guides, and prototype folders. These files are retained for traceability but should not define current behavior.

## Evidence

Use `docs/evidence/` for validation evidence that supports the project story.

- backtest reports
- Reddit or expert feedback exports
- audit evidence

Generated operational outputs should stay under `reports/`, `output/`, or `data/` unless they are being curated as evidence for the final portfolio.

## Data

Use `data/` for current pipeline inputs and outputs. Subfolders should reflect signal type, for example:

- `data/signal_gap/`
- `data/reddit_signals/`
- `data/polls/`
- `data/us_signals/`

Do not move data files casually because scripts may read fixed paths.

## Scripts

Keep executable pipeline scripts under `scripts/`.

Do not reorganize scripts by role until call paths are audited. Many scripts are called directly by name or expect repository-relative paths. If a script becomes obsolete, move it to `scripts/archive/` only after checking that no active pipeline imports or calls it.

## Tests

Use `tests/` for manual smoke tests and regression checks.

- `tests/test_db_connection.py`: verifies MySQL connectivity using the root `.env`
- `tests/test_language_models.py`: verifies local Ollama language model routing

Run these from the repository root, for example `python tests/test_language_models.py`.

## Scratch

Use `scratch/` for temporary refactor helpers, search scripts, patch drafts, and one-off outputs. Scratch files are not part of the final project story unless they are promoted into `docs/`, `scripts/`, or `data/`.

Generated runtime caches can be moved under `scratch/cache/` when cleaning the File Explorer view.
