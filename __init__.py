import os
import folder_paths

# Disable transformers 5.x async weight loading to prevent OOM with ComfyUI's
# cudaMallocAsync allocator. Concurrent GPU allocations fragment memory pools.
# https://huggingface.co/docs/transformers/en/reference/environment_variables
os.environ["HF_DEACTIVATE_ASYNC_LOAD"] = "1"

QWEN_PATH_KEY = "qwen3_5"


def _register_model_paths() -> None:
    """Register default qwen3_5 model path so users can extend it via extra paths."""
    default_qwen_dir = os.path.join(folder_paths.models_dir, "LLM")
    try:
        add_model_folder_path = getattr(folder_paths, "add_model_folder_path", None)
        if callable(add_model_folder_path):
            add_model_folder_path(QWEN_PATH_KEY, default_qwen_dir)
            return

        # Compatibility fallback for older Comfy builds.
        names_and_paths = getattr(folder_paths, "folder_names_and_paths", None)
        if isinstance(names_and_paths, dict):
            existing = names_and_paths.get(QWEN_PATH_KEY)
            if isinstance(existing, (tuple, list)) and existing:
                paths = list(existing[0]) if isinstance(existing[0], (list, tuple, set)) else [existing[0]]
                exts = existing[1] if len(existing) > 1 else set()
                if default_qwen_dir not in paths:
                    paths.append(default_qwen_dir)
                names_and_paths[QWEN_PATH_KEY] = (paths, exts)
            else:
                names_and_paths[QWEN_PATH_KEY] = ([default_qwen_dir], set())
    except Exception as e:
        print(f"[Qwen3.5] Failed to register '{QWEN_PATH_KEY}' model path: {e}")


_register_model_paths()

from .nodes import NODE_CLASS_MAPPINGS as _HF, NODE_DISPLAY_NAME_MAPPINGS as _HF_NAMES

NODE_CLASS_MAPPINGS = dict(_HF)
NODE_DISPLAY_NAME_MAPPINGS = dict(_HF_NAMES)

try:
    from .nodes_gguf import NODE_CLASS_MAPPINGS as _GGUF, NODE_DISPLAY_NAME_MAPPINGS as _GGUF_NAMES
    NODE_CLASS_MAPPINGS.update(_GGUF)
    NODE_DISPLAY_NAME_MAPPINGS.update(_GGUF_NAMES)
except ImportError as e:
    print(f"[Qwen3.5] GGUF node not available: {e}")

try:
    from .nodes_wavespeed import NODE_CLASS_MAPPINGS as _WS, NODE_DISPLAY_NAME_MAPPINGS as _WS_NAMES
    NODE_CLASS_MAPPINGS.update(_WS)
    NODE_DISPLAY_NAME_MAPPINGS.update(_WS_NAMES)
except ImportError as e:
    print(f"[Qwen3.5] WaveSpeed node not available: {e}")

try:
    from .nodes_load_url import NODE_CLASS_MAPPINGS as _URL, NODE_DISPLAY_NAME_MAPPINGS as _URL_NAMES
    NODE_CLASS_MAPPINGS.update(_URL)
    NODE_DISPLAY_NAME_MAPPINGS.update(_URL_NAMES)
except ImportError as e:
    print(f"[Qwen3.5] Load URL node not available: {e}")

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
