"""Abstract base for case exporters (Strategy pattern)."""

from abc import ABC, abstractmethod
from pathlib import Path
from typing import Any


class CaseExporter(ABC):
    """Interface for exporting case records to various formats (Dependency Inversion)."""

    @property
    @abstractmethod
    def format_name(self) -> str:
        """Display name of output format."""
        ...

    @property
    @abstractmethod
    def file_extension(self) -> str:
        """Default file extension (e.g. .json, .pdf)."""
        ...

    @abstractmethod
    def export(self, case: dict[str, Any], output_path: Path) -> None:
        """Write case to output_path."""
        ...
