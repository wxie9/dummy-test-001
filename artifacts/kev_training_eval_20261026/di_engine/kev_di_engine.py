"""Decision Index engine adapter for a local Kev checkpoint.

This adapter intentionally uses the fixed Decision Index request fields unchanged:
``state`` and ``questions`` are handed directly to Kev's serving-format
``LocalPredictor``.  It is not the stock DI Transformers engine, because a Kev
checkpoint consists of a LoRA adapter plus its learned pointer head.
"""

from __future__ import annotations

import hashlib
import os
import sys
from pathlib import Path

from decision_index.engines.base import Engine


DEFAULT_KEV_SOURCE = "/C20545/kev-08b-official-repro-20261026/stages/stage3"


class KevDecisionIndexEngine(Engine):
    """Score DI multiple-choice requests using Kev's native probability head."""

    name = "kev-decision-index"
    latency = (
        "Device-synchronized local Kev pointer-head scoring time per DI request; "
        "includes request encoding and excludes checkpoint loading."
    )

    def __init__(self, run, device="cuda:0", kev_source=DEFAULT_KEV_SOURCE, **options):
        super().__init__(**options)
        source = str(Path(kev_source).resolve())
        if source not in sys.path:
            sys.path.insert(0, source)

        import torch
        from kev.checkpoint import Checkpoint, LoadOptions
        from kev.predictors import LocalPredictor

        self.torch = torch
        self.device = str(device)
        self.run = str(Path(run).resolve())
        self.predictor = LocalPredictor(
            self.run,
            self.device,
            LoadOptions.from_env(),
        )
        checkpoint = Checkpoint(self.run)
        head = Path(self.run) / "head.pt"
        adapter = Path(self.run) / "adapter_model.safetensors"
        self.provenance = {
            "kind": "local-kev-checkpoint",
            "checkpoint": self.run,
            "base": checkpoint.meta.base,
            "base_revision": checkpoint.meta.base_revision,
            "device": self.device,
            "kev_source": source,
            "head_sha256": _sha256(head),
            "adapter_sha256": _sha256(adapter),
            "policy": (
                "The DI state and each DI question are passed unchanged into Kev's "
                "serving-format LocalPredictor. Option probabilities are its native "
                "pointer-head softmax; no generation, few-shot examples, answer parsing, "
                "or benchmark-specific prompt transformation is used."
            ),
        }

    def runtime(self):
        out = {"torch": self.torch.__version__, "device": self.device}
        if self.device.startswith("cuda"):
            index = self.torch.device(self.device).index
            out.update(
                cuda=self.torch.version.cuda,
                gpu=self.torch.cuda.get_device_name(index),
            )
        return out

    def synchronize(self):
        if self.device.startswith("cuda"):
            self.torch.cuda.synchronize(self.device)

    def warmup(self):
        """DI's generic warm-up request has no labels; Kev's internal record needs them.

        The runner's first real request remains the only meaningful warm-up here.
        """
        return None

    def __call__(self, state, questions):
        # Kev's internal materializer was written for labelled evaluation records;
        # its label is only an encoding placeholder during inference. DI rightly
        # omits gold answers from the request, so attach a deterministic dummy
        # key without changing the supplied state, instructions, or options.
        kev_questions = {
            key: {
                **question,
                "label": next(iter(question["criteria"])),
                "src": "decision-index",
            }
            for key, question in questions.items()
        }
        prediction = self.predictor({"state": state, "questions": kev_questions})
        answers = {}
        for key, question in questions.items():
            if question["type"] != "choice":
                raise ValueError(
                    f"This selected traditional-benchmark run only supports choice questions; got {question['type']!r}."
                )
            probabilities = {
                option: float(probability)
                for option, probability in prediction["probabilities"][key].items()
            }
            choice = max(probabilities, key=probabilities.get)
            answers[key] = {
                "type": "choice",
                "choice": choice,
                "probabilities": probabilities,
            }
        raw = {
            "latency_ms": float(prediction["latency_ms"]),
            "input_tokens": int(prediction["input_tokens"]),
        }
        return {"model": Path(self.run).name, "answers": answers}, raw


def _sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    return digest.hexdigest()
