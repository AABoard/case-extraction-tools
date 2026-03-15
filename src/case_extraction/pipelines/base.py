"""Base pipeline interface (Template Method)."""

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any


@dataclass
class PipelineResult:
    """Result of a pipeline run."""
    success: bool
    output_path: Path | None = None
    case: dict[str, Any] | None = None
    error: str | None = None
    source_path: Path | None = None


class BasePipeline(ABC):
    """Abstract pipeline. Subclasses implement run()."""

    @abstractmethod
    def run(self, input_path: Path, output_dir: Path | None = None, **kwargs: Any) -> PipelineResult:
        """Execute pipeline on input_path."""
        ...
