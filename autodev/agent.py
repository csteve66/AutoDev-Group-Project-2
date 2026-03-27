from __future__ import annotations

from langchain_core.messages import HumanMessage, SystemMessage, ToolMessage

from autodev.config import Settings


SYSTEM_PROMPT = """
You are AutoDev, an autonomous coding agent.

Rules:
- Decide the next best action until the task is complete.
- Prefer tools for filesystem and shell actions.
- Show concise reasoning and progress.
- After each tool result, reassess and continue.
- Stop only when the task is fully complete.
"""


class AutoDevAgent:
    def __init__(self, llm, tools: list, settings: Settings):
        self.settings = settings
        self.tools = {t.name: t for t in tools}
        self.llm = llm.bind_tools(list(self.tools.values()))

    @staticmethod
    def _tool_requires_confirmation(tool_name: str) -> bool:
        lower = tool_name.lower()
        mutating_keywords = (
            "write",
            "edit",
            "create",
            "delete",
            "remove",
            "move",
            "rename",
            "shell",
            "run_shell",
            "execute",
        )
        return any(keyword in lower for keyword in mutating_keywords)

    def _confirm_tool_call(self, tool_name: str, args: dict) -> bool:
        if self.settings.execution_mode != "confirm":
            return True
        preview = str(args)
        if len(preview) > 200:
            preview = preview[:200] + "..."
        answer = input(
            f"[confirm] Allow tool `{tool_name}` with args {preview}? (y/N): "
        ).strip().lower()
        return answer in {"y", "yes"}

    def run(self, task: str, max_steps: int | None = None) -> str:
        step_limit = max_steps or self.settings.max_steps
        messages = [
            SystemMessage(content=SYSTEM_PROMPT),
            HumanMessage(content=task),
        ]

        for _ in range(step_limit):
            response = self.llm.invoke(messages)
            messages.append(response)
            tool_calls = getattr(response, "tool_calls", []) or []

            if not tool_calls:
                return str(response.content)

            for call in tool_calls:
                tool_name = call["name"]
                tool_args = call.get("args", {})
                tool = self.tools.get(tool_name)
                if not tool:
                    tool_result = f"Tool not found: {tool_name}"
                else:
                    if self._tool_requires_confirmation(tool_name) and not self._confirm_tool_call(
                        tool_name, tool_args
                    ):
                        tool_result = f"Cancelled by user: {tool_name}"
                        messages.append(
                            ToolMessage(
                                content=tool_result,
                                tool_call_id=call["id"],
                            )
                        )
                        continue
                    try:
                        tool_result = str(tool.invoke(tool_args))
                    except Exception as exc:  # noqa: BLE001
                        tool_result = f"Tool error: {exc}"

                messages.append(
                    ToolMessage(
                        content=tool_result,
                        tool_call_id=call["id"],
                    )
                )

        return (
            f"Stopped after max steps ({step_limit}). Partial progress made; "
            "increase AUTODEV_MAX_STEPS in .env for longer tasks."
        )
