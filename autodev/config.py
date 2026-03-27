from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


@dataclass
class ServerConfig:
    name: str
    transport: str
    command: str
    args: list[str]
    env: dict[str, str]


@dataclass
class Settings:
    app_name: str
    provider: str
    model: str
    execution_mode: str
    allow_unsafe_auto_exec: bool
    embedding_model: str
    max_steps: int
    workspace: Path
    mcp_servers: list[ServerConfig]


def _bool_env(key: str, default: bool = False) -> bool:
    value = os.getenv(key)
    if value is None:
        return default
    return value.lower() in {"1", "true", "yes", "on"}


def _int_env(key: str, default: int) -> int:
    value = os.getenv(key)
    if value is None:
        return default
    try:
        return int(value)
    except ValueError:
        return default


def _resolve_env_placeholders(values: dict[str, str]) -> dict[str, str]:
    resolved: dict[str, str] = {}
    for k, v in values.items():
        if v.startswith("${") and v.endswith("}"):
            resolved[k] = os.getenv(v[2:-1], "")
        else:
            resolved[k] = v
    return resolved


def load_settings() -> Settings:
    load_dotenv()
    workspace = Path.cwd()
    config_path = workspace / "mcp_servers.json"
    servers_data: list[dict[str, Any]] = []
    if config_path.exists():
        servers_data = json.loads(config_path.read_text(encoding="utf-8")).get("servers", [])

    server_configs = [
        ServerConfig(
            name=s["name"],
            transport=s.get("transport", "stdio"),
            command=s["command"],
            args=s.get("args", []),
            env=_resolve_env_placeholders(s.get("env", {})),
        )
        for s in servers_data
    ]

    return Settings(
        app_name=os.getenv("AUTODEV_NAME", "AutoDev"),
        provider=os.getenv("AUTODEV_PROVIDER", "ollama"),
        model=os.getenv("AUTODEV_MODEL", "llama3.1"),
        execution_mode=os.getenv("AUTODEV_EXECUTION_MODE", "confirm"),
        allow_unsafe_auto_exec=_bool_env("ALLOW_UNSAFE_AUTO_EXEC", False),
        embedding_model=os.getenv("AUTODEV_EMBEDDING_MODEL", "all-MiniLM-L6-v2"),
        max_steps=max(5, _int_env("AUTODEV_MAX_STEPS", 40)),
        workspace=workspace,
        mcp_servers=server_configs,
    )
