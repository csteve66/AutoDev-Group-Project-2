from __future__ import annotations

import argparse

from autodev.agent import AutoDevAgent
from autodev.cli.repl import run_repl
from autodev.config import load_settings
from autodev.mcp.client import MCPClient
from autodev.providers.factory import build_chat_model
from autodev.tools import build_builtin_tools


def main(provider_override: str | None = None) -> None:
    settings = load_settings()
    if provider_override:
        settings.provider = provider_override
    llm = build_chat_model(settings)
    builtin_tools = build_builtin_tools(settings)

    mcp_client = MCPClient(settings.mcp_servers)
    mcp_client.connect()
    mcp_tools = mcp_client.dynamic_tools()
    mcp_statuses = mcp_client.connection_statuses()

    agent = AutoDevAgent(llm=llm, tools=[*builtin_tools, *mcp_tools], settings=settings)
    run_repl(agent, settings, mcp_statuses)


def cli_main() -> None:
    parser = argparse.ArgumentParser(prog="autodev", description="AutoDev CLI")
    provider_group = parser.add_mutually_exclusive_group()
    provider_group.add_argument("--ollama", action="store_true", help="Use Ollama provider")
    provider_group.add_argument("--groq", action="store_true", help="Use Groq provider")
    args = parser.parse_args()

    provider_override = None
    if args.ollama:
        provider_override = "ollama"
    elif args.groq:
        provider_override = "groq"
    main(provider_override=provider_override)


if __name__ == "__main__":
    cli_main()
