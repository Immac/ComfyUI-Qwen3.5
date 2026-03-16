# ComfyUI Node API Checklist

Use this checklist when creating or migrating server-side custom nodes.

## Minimal Node Skeleton

```python
class MyNode:
    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "text": ("STRING", {"default": "hello"}),
            },
            "optional": {
                "image": ("IMAGE", {}),
            },
        }

    RETURN_TYPES = ("STRING",)
    RETURN_NAMES = ("result",)
    FUNCTION = "run"
    CATEGORY = "my_nodes/text"

    def run(self, text, image=None):
        return (text,)
```

## Registration Skeleton (`__init__.py`)

```python
from .my_node_file import MyNode

NODE_CLASS_MAPPINGS = {
    "MyNode": MyNode,
}

NODE_DISPLAY_NAME_MAPPINGS = {
    "MyNode": "My Node",
}

__all__ = ["NODE_CLASS_MAPPINGS", "NODE_DISPLAY_NAME_MAPPINGS"]
```

## Current API Notes

- `INPUT_TYPES` must be a classmethod and return a dict with `required` (and optionally `optional`, `hidden`).
- `RETURN_TYPES` must always be a tuple. For one output use trailing comma: `("IMAGE",)`.
- `FUNCTION` must point to an existing method on the class.
- Node methods return tuples matching `RETURN_TYPES` length and order.
- `OUTPUT_NODE = True` only for sink/output nodes.
- `VALIDATE_INPUTS` returns `True` or an error message string.
- `IS_CHANGED` should return a fingerprint object, not a bool-based "changed" flag.
- `INPUT_IS_LIST = True` changes all method args to list mode.
- `OUTPUT_IS_LIST` is a tuple of bool flags aligned with outputs.

## Hidden Inputs Patterns

```python
@classmethod
def INPUT_TYPES(cls):
    return {
        "required": {},
        "hidden": {
            "unique_id": "UNIQUE_ID",
            "prompt": "PROMPT",
            "extra_pnginfo": "EXTRA_PNGINFO",
            "dynprompt": "DYNPROMPT",
        },
    }
```

## Safe Validation Patterns

```python
@classmethod
def VALIDATE_INPUTS(cls, threshold):
    if threshold < 0:
        return "threshold must be >= 0"
    return True
```

```python
@classmethod
def VALIDATE_INPUTS(cls, input_types):
    allowed = {"INT", "FLOAT"}
    if input_types.get("value") not in allowed:
        return "value must be INT or FLOAT"
    return True
```

## Cache Control Pattern

```python
@classmethod
def IS_CHANGED(cls, file_path):
    # Return a stable fingerprint of external state, such as file hash.
    return compute_hash(file_path)
```

## Migration Guardrails

- Keep existing mapping keys stable unless a rename was requested.
- Keep old display names if users rely on search behavior.
- Add compatibility shims when changing method signatures.
- Prefer additive changes over deletions in public node packs.

## Quick Review Questions

- Does the class expose all required properties?
- Do function args align with `INPUT_TYPES` and optional defaults?
- Are all tuple lengths and output names correct?
- Are exceptions actionable for end users?
- Are optional dependencies imported safely?
