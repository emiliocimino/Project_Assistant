# Wiki Agent

The **Wiki Agent** is an intelligent document management system designed to transform static PDF documents into a structured, searchable, and editable knowledge base (Wiki). It utilizes a multi-agent architecture to handle document parsing, information extraction, and wiki maintenance with a human-in-the-loop approval process.

## 🚀 Features

- **PDF to Wiki Pipeline**: Upload PDF documents which are automatically converted to Markdown and integrated into the project wiki.
- **Multi-Agent Orchestration**: Uses specialized agents for master coordination, source management, and wiki reading.
- **Human-in-the-Loop (HITL)**: Critical modifications to the knowledge base require explicit user approval or rejection.
- **Session Management**: Maintain multiple independent conversation threads with persistent history.
- **Live Planning**: A real-time "Case File" plan panel that shows the agent's current to-do list and progress status.
- **Modern Interface**: A professional, dossier-style UI built with Gradio.

## 🛠 Tech Stack

- **Language**: Python >=3.12
- **Package Manager**: `uv`
- **UI Framework**: [Gradio](https://gradio.app/)
- **PDF Processing**: `MarkItDown`, `PyPDF2`
- **Agent Logic**: LangGraph 

## 📁 Project Structure

```plain text
src/
├── agents/             # Agent definitions (Master, Source Manager, Wiki Reader)
├── conversations/      # SQLite database for session memory and checkpoints
├── data/               # Knowledge base storage
│   ├── sources/        # Raw Markdown conversions of uploaded PDFs
│   └── wiki/           # Structured project wiki files
├── memory/             # Logic for managing conversation threads
├── app.py              # Main Gradio application entry point
├── handlers.py         # UI event handlers and PDF processing logic
└── styles.py           # Custom CSS and theming for the dossier interface
```


## 🏁 Getting Started


### Prerequisites
Ensure you have `uv` installed on your system.

### Environment Configuration
Create a `.env` file in the root directory and configure the required variables:
```dotenv 
API_URL=https://ollama.com/v1 #Or any OpenAI compatible Providers
API_KEY=YOUR_PROVIDER_API_KEY
MODEL_NAME="gemma4:31b-cloud" #Or any model with tool support

# Project Title (Default: Project)
PROJECT_TITLE=YOUR_PROJECT_NAME

# OPTIONAL: LangSmith Tracing (Token consumption)
LANGSMITH_TRACING=true
LANGSMITH_ENDPOINT=https://api.smith.langchain.com
LANGSMITH_API_KEY=YOUR_LANGSMITH_API_KEY
LANGSMITH_PROJECT=YOUR_PROJECT_NAME
```

### Installation & Execution

1. **Clone the repository**
2. **Install NodeJS** 
[Here](https://nodejs.org/en/download) a guide, choose your platform
3**Run the application**:
```shell script
cd PROJECT_FOLDER/src
uv run app.py
```

### Docker Deployment
For a containerized setup (easier and equipped with everything) use Docker Compose:

1. Configure **ENV variables in docker compose**
2. **Build and start the container**:
```shell script
docker-compose up -d --build
```
3. **Access the UI**: Open your browser and go to `http://localhost:7860`


## 📖 How it Works

1. **Asking**: You can ask the agent questions about the existing wiki. The agent reads the structured files to provide accurate answers.
2. **Enriching**: When you upload a PDF, the system:
   - Splits the PDF into individual pages.
   - Converts each page to Markdown.
   - Triggers the `WikiAgent` to analyze the new content and propose updates to the wiki.
3. **Reviewing**: If the agent decides to modify a file, the system pauses and presents "Approve" or "Reject" buttons. The change is only committed upon approval.
4. **Tracking**: The side panel tracks every step the agent takes (e.g., `T-01: Read source`, `T-02: Update wiki`), updating statuses from `Open` $\rightarrow$ `In progress` $\rightarrow$ `Done`.

### Known Limitations
1. Some models, i.e: Google Gemini models may provide thinking tokens, breaking structured outputs and tool calling. This will be covered in future versions
2. There is a "Warning Shower" with MCP
3. Currently PDF Files upload are limited to **1 File per upload**.

### Acknowledgements
0. Thanks [Ed Donner](https://github.com/ed-donner) for your Agentic AI Course
1. This Readme is AI-generated but reviewed. It may contain errors.
2. This project is developed with the LLM-Wiki approach, from a human, to humans, with AI support for bug fixing (and UI)

### ⚠️ WARNING ⚠️
**Share sensitive data with extreme care.** I strongly suggest to use well-documented providers and models with **clear no-retention policy**. 

Alternatively, prefer use of **locally-deployed models** or **proprietary models**


## License

This project is licensed under the Apache 2.0 License. See [License](LICENSE) for information
