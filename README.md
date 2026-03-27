# AutoDev Project Planning Document

## 1. Executive Summary
AutoDev is an autonomous AI coding assistant accessible via a command-line interface (CLI). It interprets natural language instructions to read, edit, and execute code within a local codebase. Unlike standard conversational assistants, AutoDev operates as an agent that autonomously orchestrates tool calls to complete tasks, relying on flexible model providers, the Model Context Protocol (MCP), and a Retrieval-Augmented Generation (RAG) system for documentation constraints.

## 2. Project Goals & Core Requirements
The primary goal is to build an extensible, locally capable, and capable autonomous agent.
- **Agentic Loop:** An autonomous loop that can invoke tools, observe outputs (including error states), and decide when tasks are fulfilled.
- **Model Agnosticism (Provider Abstraction):** Seamlessly switch between local models (Ollama) and cloud APIs (e.g., Groq) without changing agent logic.
- **Native Tool Calling:** Give the agent abilities to search code, read/write files, and execute shell commands safely.
- **CLI Interface:** A robust REPL interface featuring streaming responses, tool-call tracking, and intuitive status indicators using `rich`.
- **Model Context Protocol (MCP) Integration:** A dynamic MCP client to communicate with external tools via standard I/O, supporting at least:
  - An official Filesystem MCP server.
  - An external tool server like Tavily for web search.
  - A custom Advanced RAG MCP server.
- **Advanced RAG (Custom MCP):** Implement a vector store (Chroma) with semantic chunking and advanced retrieval techniques like HyDE to process and query library documentation.

## 3. Architecture & Technology Stack
- **Language:** Python 3.10+
- **LLM/Agent Framework:** LangChain & LangChain Experimental
- **CLI Framework:** Rich (for REPL, status tables, and syntax highlighting)
- **Local Inference:** Ollama 
- **Cloud Inference:** Groq API
- **Vector Database:** Chroma (`langchain_chroma`)
- **Embeddings/RAG:** `SentenceTransformerEmbeddings`, LangChain `SemanticChunker`
- **MCP Client:** Custom dynamic standard I/O (Stdio) integration for `mcp` servers
- **Dependency Management:** `pip` & `pyproject.toml`

## 4. Component Breakdown
The codebase will be modularized into the following primary components:
- `autodev/agent.py`: Houses the core agentic loop, defining tool binding, step limits, and response evaluation.
- `autodev/cli/repl.py`: Manages the terminal user interface, streaming tokens, outputting observed tool calls, and capturing user input.
- `autodev/providers/factory.py`: Implements the factory pattern to instantiate Chat Model instances for either Ollama or Groq based on configuration.
- `autodev/tools.py`: Contains native python-based tools that the agent can execute (regex codebase search, local file mod, shell execution).
- `autodev/mcp/client.py`: The MCP client responsible for spawning subprocesses for MCP servers, discovering tool schemas, and converting them to Pydantic-backed LangChain tools.
- `autodev/rag_server.py`: A standalone MCP Stdio server script exposing advanced RAG capabilities (ingestion, semantic chunking, HyDE retrieval) as tools.

## 5. System Information Flow (State Diagram)

The following state diagram illustrates how information flows through the core components of the AutoDev system:

<img src="images/state-diagram.png" alt="state-diagram" width="50%" height="50%">

## 6. Sequence Diagrams (Usage Scenarios)

The following sequence diagrams illustrate three distinct end-to-end operational flows showing how the overarching Autonomous Agent, CLI, LLM, MCP, and tools interact.

### Scenario 1: Querying Library Documentation via Custom MCP RAG
<img src="images/sequence-diagram-1.png" alt="sequence-diagram-1" width="75%" height="75%">

### Scenario 2: Reading and Editing a File (With User Confirmation)
<img src="images/sequence-diagram-2.png" alt="sequence-diagram-2" width="75%" height="75%">

### Scenario 3: Web Search leading to Implementation Plan Generation
<img src="images/sequence-diagram-3.png" alt="sequence-diagram-3" width="75%" height="75%">


## 7. Implementation Phases

### Phase 1: Project Scaffolding
- Initialize project wrapper (`pyproject.toml`, `requirements.txt`).
- Setup basic environment management (`.env.example`).
- Create package structure (`autodev/` directory).

### Phase 2: CLI & Provider Abstraction
- Implement model connection factories (`autodev/providers/factory.py`) to connect to ChatGroq and ChatOllama.
- Build the initial skeleton for the `rich`-powered CLI (`autodev/cli/repl.py`).
- Link CLI arguments (`--groq`, `--ollama`) to the provider factory.

### Phase 3: Core Native Tools
- Write LangChain-compatible `@tool` decorators for file reading, file writing, regex code search, and running shell commands in `autodev/tools.py`.
- Implement user confirmation logic vs. autonomous auto-execute modes.

### Phase 4: Foundational Agentic Loop
- Assemble the system prompt outlining AutoDev's role.
- Combine the selected LLM provider and the native tools into a LangChain agent loop (`autodev/agent.py`).
- Hook the agent loop up to the CLI for proper streaming.

### Phase 5: Model Context Protocol (MCP) Integration
- Create the generic standard I/O MCP client (`autodev/mcp/client.py`).
- Configure loading capabilities from a `mcp_servers.json` schema.
- Dynamically parse MCP `list_tools` into LangChain-compatible tools.
- Validate integration with `@modelcontextprotocol/server-filesystem` and the Tavily MCP server.

### Phase 6: Advanced RAG Custom Server
- Build the `autodev/rag_server.py` as an MCP-compliant JSON-RPC over Stdio server.
- Implement `ingest_docs` logic using LangChain `SemanticChunker` to parse texts and store them in local Chroma DB vectors.
- Implement the `query_docs_hyde` tool that generates hypothetical answers using `ChatOllama` before embedding and querying the chroma vector store.
- Integrate the custom server into `mcp_servers.json.example`.

### Phase 7: Optimization & Polish
- Ensure error resilience in the agent loop (e.g., catching parsing errors or invalid tool calls returning string errors rather than crashing).
- Refine system messages for better autonomous decision making.
- Test documentation queries end-to-end to verify the HyDE RAG chunks integrate back into the agent's context.

## 8. Testing & Delivery
- **Unit Testing:** Basic validation of the factory and native tools logic.
- **Integration Testing:** Running queries requiring combinations of MCP tools and native tools (e.g. "Use RAG to find how to initialize an app, and write it to `app.py`").
- **Documentation:** Create final `README.md` defining setup, running instructions, and architecture outlines.
