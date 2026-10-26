"""Pick the brain: Meta's models when a key is set, otherwise rules only."""
from __future__ import annotations

import os

from .base import Brain, OfflineBrain


def pick_brain(offline: bool = False) -> Brain:
    if offline or not os.environ.get("MODEL_API_KEY"):
        return OfflineBrain()
    from .meta import MetaBrain
    return MetaBrain()
