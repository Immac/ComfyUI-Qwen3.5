# QWEN-003: Inference Could Not Be Interrupted From ComfyUI

## ID

QWEN-003

## Summary

The Qwen3.5 inference nodes did not observe ComfyUI's prompt interrupt flag while generation was running, so clicking Stop or sending an interrupt request left both transformers and GGUF inference running until they completed on their own.

## Location

- `nodes.py` — transformers generation loop interrupt checks
- `nodes_gguf.py` — llama.cpp subprocess interrupt polling and termination

## Impact

- **User-facing regression**: ComfyUI showed `Interrupting prompt`, but these nodes kept consuming GPU/CPU time until generation finished.
- **Resource contention**: Cancelled runs could continue holding VRAM and subprocess resources longer than expected.
- **Workflow friction**: Users could not quickly stop mistaken prompts or recover from runaway generations.

## Status

**Solved** — Implemented and statically validated.

**Verification**:
- ✅ Transformers path now injects `comfy.model_management.throw_exception_if_processing_interrupted()` into `generate()` via a stopping criterion.
- ✅ GGUF path now polls ComfyUI interrupt state during subprocess execution and terminates the child process before re-raising the interrupt.
- ✅ Repository diagnostics run after patching reported no errors in the modified files.

## Next Action

1. Restart ComfyUI so the updated custom node code is reloaded.
2. Run one transformers prompt and one GGUF prompt, then trigger `/interrupt` or click Stop to confirm both stop promptly.
3. If you want faster cancel responsiveness for GGUF, tune the polling interval further after runtime testing.