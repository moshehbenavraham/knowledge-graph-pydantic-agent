# Gemini Agent Project Overview

This document provides a comprehensive overview of the AI Agent Mastery Pydantic Agent project.

## Project Description

This project is a powerful AI agent built with Python and Pydantic. It combines several advanced features to create a versatile and intelligent agent:

*   **Agentic RAG (Retrieval Augmented Generation):** The agent can query documents with contextual understanding. It supports both local files and Google Drive as data sources.
*   **Long-term Memory:** The agent can remember important information from previous conversations.
*   **Web Search:** The agent can search the internet using either the Brave API or a self-hosted SearXNG instance.
*   **Image Analysis:** The agent can analyze images using vision-capable LLMs.
*   **Code Execution:** The agent can generate and execute Python code in a secure environment.
*   **Multi-LLM Support:** The agent is designed to work with various LLM providers, including OpenAI, OpenRouter, and local Ollama models.
*   **Streamlit UI:** A simple and effective user interface is provided to interact with the agent.

## Project Structure

The project is organized into the following directories:

*   `src/`: This directory contains the core source code for the AI agent, including the main agent logic, client configurations, system prompts, tool implementations, and the Streamlit UI.
*   `RAG_Pipeline/`: This directory houses the components for the Retrieval Augmented Generation pipeline.
    *   `common/`: Contains shared code for the RAG pipeline, such as database handling and text processing.
    *   `Google_Drive/`: Implements the logic for watching and processing files from a Google Drive folder.
    *   `Local_Files/`: Implements the logic for watching and processing files from a local directory.
*   `sql/`: This directory contains the SQL scripts required to set up the necessary tables in the Supabase database.
*   `extras/`: This directory contains additional, standalone examples and components.
    *   `Basic_Pydantic_AI_Agent/`: A simpler version of the agent that focuses on web search functionality.
*   `docs/`: This directory contains project documentation, including planning documents and task lists.

## Setup and Usage

### Agent Setup

1.  **Navigate to the project directory.**
2.  **Create and activate a Python virtual environment.**
3.  **Install the required dependencies:** `pip install -r requirements.txt`
4.  **Configure your environment variables** by copying `.env.example` to `.env` and filling in the required API keys and endpoints for your chosen LLM provider, database, and web search service.
5.  **Run the Streamlit UI:** `streamlit run src/ui/streamlit_app.py`
    (Alternatively, you can run `streamlit run src/ui/streamlit_ui_simple.py` or `streamlit run src/ui/streamlit_ui_streaming.py` for different UI examples.)

### RAG Pipeline Setup

1.  **Navigate to the `RAG_Pipeline` directory.**
2.  **Create and activate a separate Python virtual environment.**
3.  **Install the RAG-specific dependencies:** `pip install -r requirements.txt`
4.  **Set up your Supabase database** by running the SQL scripts in the `sql/` directory.
5.  **Configure the `config.json` file** in either the `Google_Drive/` or `Local_Files/` directory to specify the folder to watch.
6.  **Run the desired pipeline:**
    *   For Google Drive: `python Google_Drive/main.py`
    *   For local files: `python Local_Files/main.py`

## Extras

The `extras/` directory provides additional resources:

*   **Basic_Pydantic_AI_Agent:** A lightweight, command-line-based agent that demonstrates the core web search functionality. This is a good starting point for understanding the basic principles of the agent.
