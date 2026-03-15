"""Web app configuration - loaded from config, no hardcoding."""

from pathlib import Path
from typing import Any

from ..utils import CONFIG_ROOT, load_config


def get_web_config() -> dict[str, Any]:
    """Load web config from config/web_config.yaml."""
    return load_config("web_config.yaml", _default_config())


def _default_config() -> dict[str, Any]:
    return {
        "allowed_extensions": [".pdf", ".docx", ".doc", ".txt", ".md", ".html"],
        "max_content_length": 50 * 1024 * 1024,  # 50MB
        "default_export_formats": ["json", "pdf"],
    }


def get_upload_dir() -> Path:
    """Temporary directory for uploaded files."""
    # config.py -> web -> case_extraction -> src -> project_root
    project_root = Path(__file__).resolve().parents[3]
    return project_root / "upload_temp"
