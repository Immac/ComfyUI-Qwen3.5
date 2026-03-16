---
description: "Use when doing review or debug tasks in this repository and tracking bugs, regressions, TODO issues, or review findings. Keeps an issues folder with found, deferred, and solved states plus an index for fast lookup."
name: "Issues Tracking Workflow"
---
# Issues Tracking Workflow

Use the repository-level `.github/issues/` folder as persistent issue memory during review and debug work.

## Structure

- Keep status folders:
  - `.github/issues/found/`: Newly discovered or active issues.
  - `.github/issues/deferred/`: Issues postponed by decision, dependency, or approval wait.
  - `.github/issues/solved/`: Issues fixed and verified.
- Keep `.github/issues/index.md` updated as the single lookup table for all issues.

## Required Issue Entry Format

Create one markdown file per issue using:

- Path: `.github/issues/<status>/<ID>-short-slug.md` where `<ID>` is a short tag such as `QWEN-001`
- Sections:
  - `## ID`
  - `# <Issue Title>`
  - `## Summary`
  - `## Location`
  - `## Impact`
  - `## Status`
  - `## Next Action`

## Index Rules

- `.github/issues/index.md` must include every issue in all three status folders.
- For each issue, include: ID, title, status, area/file, last update date, and issue file path.
- Update the index whenever an issue is created, moved, solved, or deferred.
- When status changes, move the file to the matching status folder and update the index row.

## Safety Rule

For potentially breaking ComfyUI behavior changes, ask for user confirmation before applying the change and note the item as deferred until approved.
