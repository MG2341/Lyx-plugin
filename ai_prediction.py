"""AI-based prediction utilities for LaTeX/text completions.

This module integrates a Hugging Face transformers causal language model
(e.g. "facebook/galactica-1.3b" or a lightweight "gpt2") and exposes a
single high-level function:

    get_ai_prediction(context_text: str, cancel_event: Optional[threading.Event]) -> str

Key behaviours:
- Uses only the last 100 characters of the provided context_text.
- Generates at most 10 new tokens to keep latency low and preserve an
  "autocomplete" feel.
- Attempts to cancel promptly if cancel_event is set while generating.
- Returns a cleaned LaTeX/plain-text continuation string (not the full
  context), suitable for insertion into LyX.

Configuration:
- The model name can be overridden with the environment variable
  LYX_AUTOCOMPLETE_MODEL. Default: "gpt2".

Note:
- Large models like "facebook/galactica-1.3b" require substantial compute
  resources. For development and testing, prefer a small model such as
  "gpt2" or another lightweight causal LM hosted on Hugging Face.
"""

from __future__ import annotations

import os
import re
from typing import Optional
from threading import Event

try:
    from transformers import AutoTokenizer, AutoModelForCausalLM
    import torch
except ImportError as exc:  # pragma: no cover - import-time guard
    AutoTokenizer = None  # type: ignore
    AutoModelForCausalLM = None  # type: ignore
    torch = None  # type: ignore
    _IMPORT_ERROR = exc
else:
    _IMPORT_ERROR = None


_TOKENIZER = None
_MODEL = None
_DEVICE = None


def _load_model_if_needed() -> None:
    """Lazily load tokenizer and model into global variables.

    Uses environment variable LYX_AUTOCOMPLETE_MODEL to choose the model,
    defaulting to "gpt2". The model is kept in memory between calls so
    subsequent predictions are fast.
    """
    global _TOKENIZER, _MODEL, _DEVICE

    if _IMPORT_ERROR is not None:
        raise RuntimeError(
            "transformers (and its dependencies) are required for AI "
            "prediction but could not be imported. Install with "
            "'pip install transformers torch'."
        ) from _IMPORT_ERROR

    if _TOKENIZER is not None and _MODEL is not None:
        return

    model_name = os.environ.get("LYX_AUTOCOMPLETE_MODEL", "gpt2")

    print(f"[AI] Loading model '{model_name}' (this may take a while the first time)...")
    _TOKENIZER = AutoTokenizer.from_pretrained(model_name)
    _MODEL = AutoModelForCausalLM.from_pretrained(model_name)

    if torch is not None and torch.cuda.is_available():
        _DEVICE = torch.device("cuda")
    else:
        _DEVICE = torch.device("cpu") if torch is not None else None

    if _DEVICE is not None:
        _MODEL.to(_DEVICE)  # type: ignore

    _MODEL.eval()  # type: ignore
    print("[AI] Model loaded and ready.")


def _clean_output(text: str) -> str:
    """Clean raw model output to be usable LaTeX/plain text.

    - Strip non-printable control characters.
    - Collapse consecutive whitespace to a single space.
    - Remove obvious artifacts like stray unmatched quotes at the edges.
    - Trim leading/trailing whitespace.
    """
    # Remove control characters except common whitespace
    text = "".join(ch for ch in text if ch == "\n" or ch >= " " )

    # Collapse whitespace (including newlines) to single spaces
    text = re.sub(r"\s+", " ", text)

    # Strip leading/trailing quotes or backticks which models sometimes emit
    text = text.strip(" \t\n\r'\"`")

    # Very short or empty predictions are not useful
    return text


def get_ai_prediction(context_text: str, cancel_event: Optional[Event] = None) -> str:
    """Return a short LaTeX/plain-text continuation for the given context.

    Args:
        context_text: Full context text; only the last 100 characters are used.
        cancel_event: Optional threading.Event that, when set, requests
            cancellation. The function checks this between token generations
            and returns an empty string if cancellation is requested.

    Returns:
        A cleaned continuation string of up to ~10 tokens, or an empty string
        if generation is cancelled or fails.
    """
    try:
        _load_model_if_needed()
    except Exception as exc:  # pragma: no cover - defensive; logs and degrades to no-op
        print(f"[AI][ERROR] Could not load model: {exc}")
        return ""

    if cancel_event is not None and cancel_event.is_set():
        return ""

    if not context_text:
        return ""

    # Use only the last 100 characters as required
    context_tail = context_text[-100:]

    tokenizer = _TOKENIZER  # type: ignore
    model = _MODEL  # type: ignore
    device = _DEVICE

    try:
        inputs = tokenizer(context_tail, return_tensors="pt")
        input_ids = inputs["input_ids"]
        if device is not None:
            input_ids = input_ids.to(device)
    except Exception as exc:  # pragma: no cover
        print(f"[AI][ERROR] Tokenization failed: {exc}")
        return ""

    # Iteratively generate up to 10 new tokens, checking for cancellation
    max_new_tokens = 10
    generated_ids = input_ids

    for _ in range(max_new_tokens):
        if cancel_event is not None and cancel_event.is_set():
            return ""

        try:
            with torch.no_grad():  # type: ignore
                outputs = model.generate(  # type: ignore
                    generated_ids,
                    max_new_tokens=1,
                    do_sample=False,
                    pad_token_id=tokenizer.eos_token_id,
                    eos_token_id=tokenizer.eos_token_id,
                )
        except Exception as exc:  # pragma: no cover
            print(f"[AI][ERROR] Generation failed: {exc}")
            return ""

        new_ids = outputs[0]
        if new_ids.shape[0] <= generated_ids.shape[1]:  # no progress
            break

        # Keep the newly generated sequence as the base for the next step
        generated_ids = new_ids.unsqueeze(0)

        # Optional: early stop if model produced an EOS token at the end
        if tokenizer.eos_token_id is not None and new_ids[-1].item() == tokenizer.eos_token_id:
            break

    # Decode only the suffix relative to the original context
    try:
        full_text = tokenizer.decode(generated_ids[0], skip_special_tokens=True)
    except Exception as exc:  # pragma: no cover
        print(f"[AI][ERROR] Decoding failed: {exc}")
        return ""

    if not full_text:
        return ""

    # Extract continuation by removing the context tail if it appears
    if full_text.endswith(context_tail):
        # Model just echoed the context, no continuation
        continuation = ""
    else:
        # Heuristic: take the part after the first occurrence of context_tail
        idx = full_text.find(context_tail)
        if idx != -1:
            continuation = full_text[idx + len(context_tail):]
        else:
            # Fallback: if context_tail is not found (tokenization differences),
            # just take the last part as the continuation.
            continuation = full_text[len(context_tail):]

    continuation = _clean_output(continuation)
    return continuation