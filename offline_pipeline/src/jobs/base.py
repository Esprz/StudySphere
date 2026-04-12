"""Shared offline job interface."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any, Dict


class OfflineJob(ABC):
    name: str

    @abstractmethod
    def run(self) -> Dict[str, Any]:
        raise NotImplementedError

