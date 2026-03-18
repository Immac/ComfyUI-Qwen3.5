# ComfyUI-Qwen3.5
# Custom node for Qwen3.5-9B unified natively multimodal model.
# Supports text-only, image, and video inputs.
#
# Model: https://huggingface.co/Qwen/Qwen3.5-9B
# License: Apache-2.0

import gc
import re
import os
from pathlib import Path

import numpy as np
import torch
from PIL import Image
import comfy.model_management

try:
    from transformers import AutoModelForImageTextToText as AutoVLModel
except ImportError:
    from transformers import AutoModelForVision2Seq as AutoVLModel
from transformers import AutoProcessor, AutoTokenizer, BitsAndBytesConfig, StoppingCriteria, StoppingCriteriaList

import folder_paths

QUANTIZATION_OPTIONS = ["FP16", "8-bit", "4-bit"]
THINK_BLOCK_RE = re.compile(r"<think[^>]*>.*?</think>", flags=re.IGNORECASE | re.DOTALL)
# Matches Qwen-style special tokens like <|im_end|>, <|endoftext|> that remain
# when decoding with skip_special_tokens=False.
_QWEN_SPECIAL_RE = re.compile(r"<\|[^|]*\|>")
QWEN_PATH_KEY = "qwen3_5"
NO_TRANSFORMERS_MODELS = "<no transformers models found>"


class _InterruptStoppingCriteria(StoppingCriteria):
    """Abort generation as soon as ComfyUI marks the prompt interrupted."""

    def __call__(self, input_ids, scores, **kwargs):
        comfy.model_management.throw_exception_if_processing_interrupted()
        return False


def _get_qwen_base_dirs() -> list[Path]:
    """Return configured qwen3_5 search roots, always including models/LLM fallback."""
    raw_paths = []
    get_folder_paths = getattr(folder_paths, "get_folder_paths", None)
    if callable(get_folder_paths):
        try:
            raw_paths.extend(get_folder_paths(QWEN_PATH_KEY) or [])
        except Exception:
            pass

    if not raw_paths:
        names_and_paths = getattr(folder_paths, "folder_names_and_paths", {})
        entry = names_and_paths.get(QWEN_PATH_KEY)
        if isinstance(entry, (tuple, list)) and entry:
            candidate_paths = entry[0]
            if isinstance(candidate_paths, (tuple, list, set)):
                raw_paths.extend(candidate_paths)
            elif isinstance(candidate_paths, str):
                raw_paths.append(candidate_paths)

    raw_paths.append(os.path.join(folder_paths.models_dir, "LLM"))

    resolved = []
    seen = set()
    for raw in raw_paths:
        if not raw:
            continue
        path = Path(raw).expanduser()
        key = str(path)
        if key in seen:
            continue
        seen.add(key)
        resolved.append(path)

    return resolved


def _discover_transformers_models() -> list[str]:
    """Discover local transformers model folders recursively from qwen3_5 paths."""
    discovered = set()
    for base_dir in _get_qwen_base_dirs():
        if not base_dir.is_dir():
            continue
        for config_path in base_dir.rglob("config.json"):
            model_dir = config_path.parent
            try:
                relative = model_dir.relative_to(base_dir).as_posix()
            except ValueError:
                continue
            if relative and not relative.startswith("."):
                discovered.add(relative)
    return sorted(discovered, key=str.lower)


class Qwen35:
    """Qwen3.5 unified multimodal node for ComfyUI."""

    model = None
    processor = None
    tokenizer = None
    current_signature = None

    @classmethod
    def INPUT_TYPES(cls):
        return {
            "required": {
                "model": ("QWEN35_MODEL", {"tooltip": "Model handle from Qwen 3.5 Loader."}),
                "prompt": ("STRING", {
                    "default": "Describe this image in detail.",
                    "multiline": True,
                    "tooltip": "Text prompt for the model",
                }),
                "system_prompt": ("STRING", {
                    "default": "",
                    "multiline": True,
                    "tooltip": "Optional system prompt to set model behavior",
                }),
                "max_tokens": ("INT", {
                    "default": 4096,
                    "min": 64,
                    "max": 81920,
                    "tooltip": "Maximum tokens to generate",
                }),
                "temperature": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.0,
                    "max": 2.0,
                    "step": 0.05,
                    "tooltip": "Sampling temperature. Thinking mode recommends 1.0, instruct mode 0.7",
                }),
                "top_p": ("FLOAT", {
                    "default": 0.95,
                    "min": 0.0,
                    "max": 1.0,
                    "step": 0.05,
                    "tooltip": "Nucleus sampling. Thinking mode recommends 0.95, instruct mode 0.8",
                }),
                "top_k": ("INT", {
                    "default": 20,
                    "min": 1,
                    "max": 100,
                    "tooltip": "Top-K sampling. Recommended: 20",
                }),
                "repetition_penalty": ("FLOAT", {
                    "default": 1.0,
                    "min": 0.5,
                    "max": 2.0,
                    "step": 0.05,
                    "tooltip": "Penalty for repeated tokens. Recommended: 1.0",
                }),
                "enable_thinking": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Enable thinking mode. Model outputs <think>...</think> reasoning before response.",
                }),
                "quantization": (QUANTIZATION_OPTIONS, {
                    "default": "FP16",
                    "tooltip": "Model quantization. 4-bit needs ~7GB VRAM, 8-bit ~12GB, FP16 ~20GB",
                }),
                "keep_model_loaded": ("BOOLEAN", {
                    "default": True,
                    "tooltip": "Keep model in VRAM between runs for faster inference",
                }),
                "seed": ("INT", {
                    "default": 1,
                    "min": 1,
                    "max": 2**32 - 1,
                    "tooltip": "Random seed for reproducibility",
                }),
            },
            "optional": {
                "image": ("IMAGE", {"tooltip": "Single image input"}),
                "video": ("IMAGE", {"tooltip": "Video frames input (batch of images)"}),
                "frame_count": ("INT", {
                    "default": 16,
                    "min": 1,
                    "max": 64,
                    "tooltip": "Maximum number of frames to sample from video",
                }),
            },
        }

    RETURN_TYPES = ("STRING", "STRING")
    RETURN_NAMES = ("RESPONSE", "THINKING")
    FUNCTION = "process"
    CATEGORY = "Qwen3.5"

    @staticmethod
    def _get_model_path(model_name: str) -> Path:
        """Resolve model folder from ComfyUI qwen3_5 paths without downloading."""
        searched_dirs = []
        for base_dir in _get_qwen_base_dirs():
            candidate_dir = base_dir / model_name
            searched_dirs.append(str(candidate_dir))
            if (candidate_dir / "config.json").is_file():
                return candidate_dir

        # Compatibility: if model_name is only a leaf dir name, allow nested lookup.
        for base_dir in _get_qwen_base_dirs():
            if not base_dir.is_dir():
                continue
            for config_path in base_dir.rglob("config.json"):
                model_dir = config_path.parent
                if model_dir.name == model_name:
                    return model_dir

        searched = "\n  - ".join(searched_dirs) if searched_dirs else "(no qwen3_5 paths configured)"
        raise FileNotFoundError(
            "[Qwen3.5] Model files not found. Automatic downloads are disabled.\n"
            f"Requested model: {model_name}\n"
            "Expected transformers layout with config.json at one of:\n"
            f"  - {searched}\n"
            "Configure ComfyUI extra model paths under key 'qwen3_5' or place models in ComfyUI/models/LLM/."
        )

    @staticmethod
    def _tensor_to_pil(tensor: torch.Tensor) -> Image.Image:
        """Convert a ComfyUI IMAGE tensor to PIL Image."""
        if tensor.dim() == 4:
            tensor = tensor[0]
        array = (tensor.cpu().numpy() * 255).clip(0, 255).astype(np.uint8)
        return Image.fromarray(array)

    @classmethod
    def _clear(cls):
        """Release model from memory."""
        cls.model = None
        cls.processor = None
        cls.tokenizer = None
        cls.current_signature = None
        gc.collect()
        if torch.cuda.is_available():
            torch.cuda.empty_cache()

    @classmethod
    def _load_model(cls, model_name: str, quantization: str, keep_model_loaded: bool):
        """Load or reuse the model based on current config."""
        if model_name == NO_TRANSFORMERS_MODELS:
            raise FileNotFoundError(
                "[Qwen3.5] No local transformers models found in configured qwen3_5 paths. "
                "Add a model folder containing config.json under ComfyUI/models/LLM/ "
                "or an extra qwen3_5 path."
            )

        signature = f"{model_name}_{quantization}"

        if cls.model is not None and cls.current_signature == signature:
            print(f"[Qwen3.5] Reusing loaded {model_name} ({quantization})")
            return

        if cls.model is not None:
            cls._clear()

        model_path = cls._get_model_path(model_name)

        # Build quantization config
        quant_config = None

        if quantization == "4-bit":
            quant_config = BitsAndBytesConfig(
                load_in_4bit=True,
                bnb_4bit_compute_dtype=torch.float16,
                bnb_4bit_quant_type="nf4",
                bnb_4bit_use_double_quant=True,
            )
        elif quantization == "8-bit":
            quant_config = BitsAndBytesConfig(load_in_8bit=True)

        # Reset any VRAM memory fraction limit set by ComfyUI
        if torch.cuda.is_available():
            try:
                torch.cuda.set_per_process_memory_fraction(1.0)
            except Exception:
                pass

        device = "cuda" if torch.cuda.is_available() else "cpu"

        load_kwargs = {
            "use_safetensors": True,
            "device_map": device,
        }

        if quant_config:
            load_kwargs["quantization_config"] = quant_config
        else:
            load_kwargs["torch_dtype"] = torch.float16 if torch.cuda.is_available() else torch.float32

        if torch.cuda.is_available():
            free_mem, total_mem = torch.cuda.mem_get_info(0)
            free_gb = free_mem / (1024 ** 3)
            print(f"[Qwen3.5] GPU memory: {free_gb:.1f} GiB free / {total_mem / (1024**3):.1f} GiB total")

        print(f"[Qwen3.5] Loading {model_name} ({quantization})...")
        cls.model = AutoVLModel.from_pretrained(
            str(model_path),
            **load_kwargs,
        ).eval()

        cls.processor = AutoProcessor.from_pretrained(str(model_path), trust_remote_code=True)
        cls.tokenizer = AutoTokenizer.from_pretrained(str(model_path), trust_remote_code=True)
        cls.current_signature = signature
        print("[Qwen3.5] Model loaded.")

    @classmethod
    @torch.no_grad()
    def _generate(
        cls,
        prompt: str,
        system_prompt: str,
        image,
        video,
        frame_count: int,
        max_tokens: int,
        temperature: float,
        top_p: float,
        top_k: int,
        repetition_penalty: float,
        enable_thinking: bool,
    ) -> tuple[str, str]:
        """Run inference with the loaded model. Returns (response, thinking)."""
        # Build conversation
        messages = []

        if system_prompt and system_prompt.strip():
            messages.append({"role": "system", "content": system_prompt.strip()})

        user_content = []

        # Image mode
        if image is not None:
            pil_image = cls._tensor_to_pil(image)
            user_content.append({"type": "image", "image": pil_image})

        # Video mode
        if video is not None:
            frames = [cls._tensor_to_pil(frame) for frame in video]
            if len(frames) > frame_count:
                idx = np.linspace(0, len(frames) - 1, frame_count, dtype=int)
                frames = [frames[i] for i in idx]
            if frames:
                user_content.append({"type": "video", "video": frames})

        # Text prompt (always present)
        user_content.append({"type": "text", "text": prompt})
        messages.append({"role": "user", "content": user_content})

        # Apply chat template with thinking mode control.
        # Base models may lack a chat template on the processor; fall back to the
        # tokenizer. Also handle older transformers that don't accept chat_template_kwargs.
        def _apply_template(fn):
            try:
                return fn(
                    messages,
                    tokenize=False,
                    add_generation_prompt=True,
                    chat_template_kwargs={"enable_thinking": enable_thinking},
                )
            except TypeError:
                # chat_template_kwargs not supported by this transformers version
                return fn(messages, tokenize=False, add_generation_prompt=True)

        try:
            chat = _apply_template(cls.processor.apply_chat_template)
        except Exception:
            chat = _apply_template(cls.tokenizer.apply_chat_template)

        # Process inputs
        images = [item["image"] for item in user_content if item.get("type") == "image"]
        video_frames = [
            frame
            for item in user_content
            if item.get("type") == "video"
            for frame in item["video"]
        ]
        videos = [video_frames] if video_frames else None

        processed = cls.processor(
            text=chat,
            images=images or None,
            videos=videos,
            return_tensors="pt",
        )

        model_device = next(cls.model.parameters()).device
        model_inputs = {
            key: value.to(model_device) if torch.is_tensor(value) else value
            for key, value in processed.items()
        }

        # Stop tokens
        stop_tokens = [cls.tokenizer.eos_token_id]
        if hasattr(cls.tokenizer, "eot_id") and cls.tokenizer.eot_id is not None:
            stop_tokens.append(cls.tokenizer.eot_id)

        # Generate
        gen_kwargs = {
            "max_new_tokens": max_tokens,
            "do_sample": True,
            "temperature": temperature,
            "top_p": top_p,
            "top_k": top_k,
            "repetition_penalty": repetition_penalty,
            "eos_token_id": stop_tokens,
            "pad_token_id": cls.tokenizer.pad_token_id,
            "stopping_criteria": StoppingCriteriaList([_InterruptStoppingCriteria()]),
        }

        outputs = cls.model.generate(**model_inputs, **gen_kwargs)

        if torch.cuda.is_available():
            torch.cuda.synchronize()

        # Decode — trim input tokens
        input_len = model_inputs["input_ids"].shape[-1]
        generated = outputs[0, input_len:]
        # Decode with skip_special_tokens=False so that <think>...</think> markers
        # are preserved — Qwen3/Qwen3.5 registers them as special tokens and
        # skip_special_tokens=True would silently strip them, breaking extraction.
        text = cls.tokenizer.decode(generated, skip_special_tokens=False).strip()

        # Extract thinking content and clean response separately.
        # Handle both <think>...</think> and cases where only </think> remains.
        thinking = ""
        match = THINK_BLOCK_RE.search(text)
        if match:
            thinking = re.sub(r"</?think[^>]*>", "", match.group(0)).strip()
            text = THINK_BLOCK_RE.sub("", text).strip()
        if "</think>" in text:
            parts = text.split("</think>", 1)
            if not thinking:
                thinking = parts[0].strip()
            text = parts[1].strip()

        # Strip residual Qwen special tokens (e.g. <|im_end|>, <|endoftext|>)
        # that appear because we decoded with skip_special_tokens=False.
        text = _QWEN_SPECIAL_RE.sub("", text).strip()
        thinking = _QWEN_SPECIAL_RE.sub("", thinking).strip()

        return text, thinking

    def process(
        self,
        model,
        prompt: str,
        system_prompt: str,
        max_tokens: int,
        temperature: float,
        top_p: float,
        top_k: int,
        repetition_penalty: float,
        enable_thinking: bool,
        quantization: str,
        keep_model_loaded: bool,
        seed: int,
        image=None,
        video=None,
        frame_count: int = 16,
    ):
        model = str(model).strip() if model is not None else ""
        if not model:
            raise ValueError("[Qwen3.5] Invalid model handle. Connect Qwen 3.5 Loader to the model input.")

        if quantization not in QUANTIZATION_OPTIONS:
            raise ValueError(f"[Qwen3.5] Unsupported quantization: {quantization}")

        torch.manual_seed(seed)

        Qwen35._load_model(model, quantization, keep_model_loaded)

        try:
            response, thinking = Qwen35._generate(
                prompt=prompt,
                system_prompt=system_prompt,
                image=image,
                video=video,
                frame_count=frame_count,
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=top_p,
                top_k=top_k,
                repetition_penalty=repetition_penalty,
                enable_thinking=enable_thinking,
            )
            return (response, thinking)
        finally:
            if not keep_model_loaded:
                Qwen35._clear()


NODE_CLASS_MAPPINGS = {"Qwen35": Qwen35}
NODE_DISPLAY_NAME_MAPPINGS = {"Qwen35": "Qwen 3.5"}


class Qwen35Loader:
    """Model loader for Qwen3.5 local transformers models."""

    @classmethod
    def INPUT_TYPES(cls):
        model_options = _discover_transformers_models()
        if not model_options:
            model_options = [NO_TRANSFORMERS_MODELS]
        default_model = "Qwen3.5-9B" if "Qwen3.5-9B" in model_options else model_options[0]
        return {
            "required": {
                "model": (model_options, {
                    "default": default_model,
                    "tooltip": "Discovered from qwen3_5 model paths (folders containing config.json).",
                }),
            },
        }

    RETURN_TYPES = ("QWEN35_MODEL",)
    RETURN_NAMES = ("model",)
    FUNCTION = "load"
    CATEGORY = "Qwen3.5"

    def load(self, model: str):
        return (model,)


NODE_CLASS_MAPPINGS["Qwen35Loader"] = Qwen35Loader
NODE_DISPLAY_NAME_MAPPINGS["Qwen35Loader"] = "Qwen 3.5 Loader"
