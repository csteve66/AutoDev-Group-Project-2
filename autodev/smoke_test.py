from __future__ import annotations

from autodev.config import load_settings
from autodev.mcp.client import MCPClient


def main() -> None:
    settings = load_settings()
    client = MCPClient(settings.mcp_servers)
    client.connect()
    tools = client.dynamic_tools()

    print("== Dynamic MCP Tools ==")
    for tool in tools:
        print(f"- {tool.name}")

    tool_map = {t.name: t for t in tools}

    fs_list = tool_map.get("filesystem__list_directory")
    if fs_list:
        print("\n== filesystem__list_directory ==")
        print(fs_list.invoke({"path": "."}))
    else:
        print("\nfilesystem__list_directory not available.")

    rag_ingest = tool_map.get("autodev-rag__ingest_docs")
    if rag_ingest:
        print("\n== autodev-rag__ingest_docs ==")
        print(rag_ingest.invoke({"path": "docs"}))
    else:
        print("\nautodev-rag__ingest_docs not available.")

    rag_query = tool_map.get("autodev-rag__query_docs_hyde")
    if rag_query:
        print("\n== autodev-rag__query_docs_hyde ==")
        print(rag_query.invoke({"query": "What is AutoDev?"}))
    else:
        print("\nautodev-rag__query_docs_hyde not available.")


if __name__ == "__main__":
    main()
