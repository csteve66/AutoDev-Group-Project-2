from __future__ import annotations

from rich.console import Console
from rich.panel import Panel

from autodev.agent import AutoDevAgent
from autodev.config import Settings
from autodev.mcp.client import MCPServerStatus


def _configure_execution_mode(console: Console, settings: Settings) -> None:
    console.print("\nExecution mode:")
    console.print("1) confirm - ask before write/shell actions")
    console.print("2) auto    - auto-execute write/shell actions\n")
    choice = console.input("Select mode [1/2, Enter keeps current]: ").strip().lower()

    if choice in {"", "1", "confirm", "c"}:
        settings.execution_mode = "confirm"
        console.print("[cyan]Using confirm mode.[/cyan]\n")
        return

    if choice in {"2", "auto", "a"}:
        confirm = console.input(
            "[bold yellow]Enable auto mode for this session?[/bold yellow] [y/N]: "
        ).strip().lower()
        if confirm in {"y", "yes"}:
            settings.execution_mode = "auto"
            settings.allow_unsafe_auto_exec = True
            console.print("[bold yellow]Auto mode enabled for this session.[/bold yellow]\n")
        else:
            settings.execution_mode = "confirm"
            console.print("[cyan]Keeping confirm mode.[/cyan]\n")
        return

    settings.execution_mode = "confirm"
    console.print("[cyan]Invalid choice; using confirm mode.[/cyan]\n")


def _show_mcp_status(console: Console, statuses: list[MCPServerStatus]) -> None:
    if not statuses:
        console.print("[yellow]MCP: no configured servers found.[/yellow]")
        return
    console.print("[bold]MCP Server Status[/bold]")
    for status in statuses:
        if status.connected:
            console.print(f"[green]CONNECTED[/green] {status.server_name} ({status.tool_count} tools)")
        else:
            console.print(
                f"[red]FAILED[/red] {status.server_name} - {status.error or 'Unknown connection error'}"
            )
    console.print("")


def run_repl(agent: AutoDevAgent, settings: Settings, mcp_statuses: list[MCPServerStatus]) -> None:
    console = Console()
    console.print(Panel("[bold cyan]AutoDev[/bold cyan] autonomous coding assistant"))
    _show_mcp_status(console, mcp_statuses)
    _configure_execution_mode(console, settings)
    console.print("Type a task, then press Enter. Type `exit` to quit.\n")

    while True:
        task = console.input("[bold green]autodev> [/bold green]").strip()
        if task.lower() in {"exit", "quit"}:
            console.print("Bye.")
            return
        if not task:
            continue

        console.print("[yellow]Running agent loop...[/yellow]")
        result = agent.run(task)
        console.print(Panel(result, title="Result"))
