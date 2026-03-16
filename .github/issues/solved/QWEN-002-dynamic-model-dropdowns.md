## ID

QWEN-002

# Regressed Preselected Model Lists in Local Nodes

## Summary

`Qwen 3.5` and `Qwen 3.5 (GGUF)` regressed to hardcoded model dropdown options. This was incorrect after moving to ComfyUI-native local-path loading because it hid available local models and implied a fixed set. The transformers path is now loader-first (`Qwen 3.5 Loader` -> `Qwen 3.5`) in a vanilla ComfyUI style.

## Location

- `nodes.py`
- `nodes_gguf.py`
- `README.md`
- `workflows/qwen3.5.json`

## Impact

- Local model pickers now reflect models actually present on disk in configured `qwen3_5` paths.
- Avoids misleading preselected model catalogs.
- Provides explicit, actionable errors when no local models are discovered.
- Restores vanilla loader wiring for transformers workflows.

## Status

Solved

## Next Action

Restart ComfyUI and verify both local nodes show discovered model names from your `qwen3_5` directories.
