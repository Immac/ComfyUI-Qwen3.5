---
name: comfyui-custom-node-api
description: 'Create, migrate, or review ComfyUI custom nodes using the latest backend API conventions. Use when adding NODE_CLASS_MAPPINGS, INPUT_TYPES, RETURN_TYPES, FUNCTION, CATEGORY, VALIDATE_INPUTS, IS_CHANGED, INPUT_IS_LIST/OUTPUT_IS_LIST, hidden inputs, and WEB_DIRECTORY.'
argument-hint: 'What node should be built or updated, and what inputs/outputs should it expose?'
user-invocable: true
---

# ComfyUI Custom Node API

## What This Skill Produces

This skill produces production-ready ComfyUI custom node changes that:
- Follow current Comfy backend node API expectations.
- Fit existing repository style and category conventions.
- Include safe execution and validation behavior.
- Register correctly through `__init__.py` exports.

## When To Use

Use this skill when you need to:
- Build a new server-side custom node.
- Update old node definitions to current Comfy conventions.
- Add list-aware behavior (`INPUT_IS_LIST`, `OUTPUT_IS_LIST`).
- Add robust validation and cache behavior (`VALIDATE_INPUTS`, `IS_CHANGED`).
- Add hidden inputs (`PROMPT`, `UNIQUE_ID`, `EXTRA_PNGINFO`, `DYNPROMPT`) for advanced workflows.
- Review a node pack for API regressions.

## Workflow

1. Clarify the node contract
- Define node purpose in one sentence.
- Define exact inputs (required/optional/hidden), outputs, and category path.
- Decide if this is server-only, client-only, or mixed (JS + Python).

2. Verify latest Comfy API before coding
- Check current docs first:
- `https://docs.comfy.org/custom-nodes/backend/server_overview`
- `https://docs.comfy.org/custom-nodes/backend/lifecycle`
- `https://docs.comfy.org/custom-nodes/backend/more_on_inputs`
- `https://docs.comfy.org/custom-nodes/backend/lists`
- If docs and local patterns conflict, prefer current docs and preserve backward compatibility when possible.

3. Choose implementation path
- Scalar node path:
- Use standard `INPUT_TYPES` + `RETURN_TYPES` + `FUNCTION`.
- List-processing path:
- Use `INPUT_IS_LIST = True` when full lists are needed in a single call.
- Use `OUTPUT_IS_LIST = (...)` to mark outputs that should remain lists.
- Output/sink path:
- Set `OUTPUT_NODE = True` only for true terminal/output behavior.

4. Implement node class with modern required attributes
- Implement `@classmethod INPUT_TYPES` returning `required`, optional `optional`, optional `hidden`.
- Define `RETURN_TYPES` tuple (include trailing comma for single output).
- Optionally define `RETURN_NAMES`.
- Define `FUNCTION` and `CATEGORY`.
- Implement the function named by `FUNCTION` and return tuple matching outputs.

5. Add execution-control and validation only when needed
- Use `VALIDATE_INPUTS` for domain checks and type flexibility.
- Use `IS_CHANGED` only when default cache invalidation is insufficient.
- Never return bool from `IS_CHANGED` as a change signal; return a stable fingerprint or `float("NaN")` only when always-run is required.

6. Register and expose nodes cleanly
- Update or create module exports in `__init__.py`:
- `NODE_CLASS_MAPPINGS` is required.
- `NODE_DISPLAY_NAME_MAPPINGS` is optional but recommended.
- If frontend JS is shipped, export `WEB_DIRECTORY` (do not use legacy JS-copy patterns).
- Keep graceful optional imports where dependencies are optional.

7. Enforce safety and compatibility
- Preserve existing node names in mappings unless migration is explicitly requested.
- For potentially breaking behavior changes, ask for approval before applying.
- Keep errors actionable and specific (missing model, invalid input, missing binary, etc.).

8. Validate end-to-end
- Static checks:
- Mapping keys unique and stable.
- `FUNCTION` exists and signature matches expected inputs.
- Output tuple length matches `RETURN_TYPES`.
- Runtime checks:
- Node loads in Comfy startup logs without import failure.
- Node appears in expected category and executes a minimal workflow.
- Optional/list/hidden input branches run correctly.

## Decision Rules

- Need dynamic dropdown options at runtime:
- Compute options in `INPUT_TYPES` classmethod.

- Need values not shown as widgets/ports:
- Use `hidden` inputs in `INPUT_TYPES`.

- Need broad type acceptance (`*` or custom multi-type):
- Implement `VALIDATE_INPUTS` with `input_types` handling.

- Need deterministic caching for external file/API data:
- Implement `IS_CHANGED` using content hash/version token.

- Need API-mode compatibility:
- Avoid hard client-server coupling unless explicitly required.

## Completion Checklist

A task is complete only when all are true:
- Node class uses current property conventions (`INPUT_TYPES`, `RETURN_TYPES`, `FUNCTION`, `CATEGORY`).
- Optional behavior (`VALIDATE_INPUTS`, `IS_CHANGED`, list flags, hidden inputs) is justified and tested.
- `NODE_CLASS_MAPPINGS` registration is present and import-safe.
- No accidental breaking rename of node IDs or categories.
- A minimal execution path was validated or a clear blocker was documented.

## References

- API checklist and templates: [ComfyUI Node API Checklist](./references/comfyui-node-api-checklist.md)
