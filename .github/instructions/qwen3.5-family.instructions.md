---
description: "Use for local Qwen3.5 model changes in this repo: preserve vanilla ComfyUI model-loading patterns, local-only model resolution, and recursive qwen3_5 path discovery."
applyTo: "__init__.py,nodes.py,nodes_gguf.py,README.md,workflows/qwen3.5*.json"
---

# Qwen3.5 Local Model Conventions

When working on local Qwen3.5 model support in this repository, follow these rules:

## Architecture

- Prefer vanilla ComfyUI structure over wrapper-style abstractions.
- For local transformers models, keep model selection in `Qwen35Loader` and pass the loader output into `Qwen35`.
- Do not collapse loader-driven model selection back into inline node dropdowns when the node should behave like a vanilla ComfyUI loader/consumer pair.
- Preserve stable node IDs and category naming unless a migration is explicitly requested.

## Model Resolution

- Automatic model downloads must remain disabled.
- Resolve models only from local disk via the `qwen3_5` model path key and the default `ComfyUI/models/LLM/` fallback.
- Model discovery must support nested folders, not only direct children of configured model roots.
- Discovery and runtime lookup should stay aligned: if the loader or node can list a model, the execution path should be able to resolve that same model from disk.

## Node-Specific Rules

- `Qwen35Loader` should expose dynamically discovered local transformers models.
- `Qwen35` should consume the loader output rather than owning local model selection directly.
- `Qwen35GGUF` should dynamically discover local GGUF models from `qwen3_5` paths.
- Keep error messages actionable and specific about searched locations and expected files.

## Scope Discipline

- Keep changes scoped to local Qwen3.5 model support and avoid unrelated architectural cleanup.
- If changing model-loading behavior, update the bundled workflows and README in the same change.
- Prefer minimal fixes that preserve the established Qwen3.5 conventions in this repo.

## Explicit Exclusion

- Do not apply these rules to `nodes_wavespeed.py` unless a task explicitly says to unify or refactor WaveSpeed behavior.
- WaveSpeed is out of scope for this instruction file and may follow different API and model-selection rules.
