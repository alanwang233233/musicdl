from __future__ import annotations

import json
import os
from pathlib import Path

from musicdl import MusicDLConfig

CONFIG_DIR = Path.home() / ".config" / "musicdl-gui"


def _config_file() -> Path:
    return CONFIG_DIR / "config.json"

DEFAULT_CONFIG = {
    "base_url": "https://nextmusic.toubiec.cn",
    "timeout": 30.0,
    "max_retries": 3,
    "retry_backoff": 0.5,
    "ip": None,
    "ip_fetch_url": "https://api.ipify.org?format=json",
    "ip_cache_ttl": 3600.0,
    "default_level": "standard",
    "user_agent": None,
    "output_dir": "./music",
    "naming_template": "{singer} - {title}",
}


class ConfigManager:
    def __init__(self) -> None:
        self._config: dict = {}

    def load(self) -> dict:
        config_file = _config_file()
        if config_file.exists():
            with open(config_file, "r", encoding="utf-8") as f:
                saved = json.load(f)
            self._config = {**DEFAULT_CONFIG, **saved}
        else:
            self._config = DEFAULT_CONFIG.copy()
        return self._config

    def save(self, config: dict) -> None:
        CONFIG_DIR.mkdir(parents=True, exist_ok=True)
        config_file = _config_file()
        with open(config_file, "w", encoding="utf-8") as f:
            json.dump(config, f, indent=2, ensure_ascii=False)
        self._config = config

    def get_config(self) -> MusicDLConfig:
        cfg = self.load()
        return MusicDLConfig(
            base_url=cfg["base_url"],
            timeout=cfg["timeout"],
            max_retries=cfg["max_retries"],
            retry_backoff=cfg["retry_backoff"],
            ip=cfg["ip"],
            ip_fetch_url=cfg["ip_fetch_url"],
            ip_cache_ttl=cfg["ip_cache_ttl"],
            default_level=cfg["default_level"],
            user_agent=cfg["user_agent"],
        )

    def validate(self, config: dict) -> list[str]:
        errors = []
        if config.get("timeout", 0) <= 0:
            errors.append("timeout must be positive")
        if config.get("max_retries", 0) < 0:
            errors.append("max_retries must be non-negative")
        if config.get("retry_backoff", 0) < 0:
            errors.append("retry_backoff must be non-negative")
        if not config.get("base_url"):
            errors.append("base_url is required")
        if not config.get("output_dir"):
            errors.append("output_dir is required")
        return errors