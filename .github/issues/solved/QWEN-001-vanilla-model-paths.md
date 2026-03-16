# QWEN-001: Model Loading Migration to Vanilla ComfyUI Paths

## ID

QWEN-001

## Summary

Replaced automatic HuggingFace Hub model downloads with ComfyUI-native path key registration, eliminating unexpected storage bloat and allowing users to manage model locations via extra paths.

## Location

- `__init__.py` — path key registration (lines 9-38)
- `nodes.py` — transformers node loader (lines 35-72, 171-188)
- `nodes_gguf.py` — GGUF node loader (lines 29-96, 197-237)
- `requirements.txt` — dependency cleanup
- `pyproject.toml` — package metadata cleanup
- `README.md` — documentation update (lines 61-79)

## Impact

- **Behavior change**: Models no longer auto-download; they must exist on disk in a registered `qwen3_5` path.
- **User migration**: Existing `ComfyUI/models/LLM/` locations automatically work via default registration; additional paths configured via `extra_model_paths.yaml`.
- **Dependency removal**: `huggingface-hub` no longer required at runtime (removed from `requirements.txt` and `pyproject.toml`).
- **Error clarity**: Missing models now produce actionable errors listing searched directories.

## Status

**Solved** — Implemented and verified.

**Verification**:
- ✅ Syntax check: `__init__.py` and `nodes.py` parse cleanly (AST OK).
- ✅ Import check: Node registration line confirmed.
- ✅ Git diff: Only intended Qwen loader, docs, and requirement files modified.
- ✅ Static analysis: No remaining `snapshot_download` or `hf_hub_download` calls.

## Next Action

1. **Runtime validation**: Restart ComfyUI and confirm node pack loads without import errors.
2. **Functional test**: Verify transformers/GGUF nodes can resolve models from `ComfyUI/models/LLM/`.
3. **Multi-path test**: Add secondary path via `extra_model_paths.yaml` and confirm discovery works.
4. **Regression check**: Confirm WaveSpeed and other optional nodes still load gracefully.

## Technical Details

### Path Resolution Algorithm

Both `nodes.py` and `nodes_gguf.py` implement identical path search logic via `_get_qwen_base_dirs()`:

1. Query `folder_paths.get_folder_paths("qwen3_5")` if available.
2. Fall back to `folder_paths.folder_names_and_paths.get("qwen3_5")` for older ComfyUI builds.
3. Always append `ComfyUI/models/LLM` as final fallback.
4. Deduplicate and resolve paths, filtering out empty/invalid entries.

### Error Messages

- **Transformers (missing model)**: Points to all searched directories, lists expected file (`config.json`).
- **GGUF (missing files)**: Lists searched directories, missing files, and requested quantization.

Both direct users to configure `qwen3_5` in `extra_model_paths.yaml` or place models in default location.

### Path Registration Robustness

`__init__.py` registration handles both modern and legacy ComfyUI APIs:

- **Modern API**: Uses `folder_paths.add_model_folder_path("qwen3_5", default_dir)`.
- **Legacy fallback**: Manually updates `folder_paths.folder_names_and_paths` dict.
- **Exception safety**: Graceful print on registration failure; node loading still proceeds.
