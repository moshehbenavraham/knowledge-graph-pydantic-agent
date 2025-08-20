# Installation

## System Requirements
- Python 3.11 or higher
- Supabase project with pgvector extension enabled
- 4GB+ RAM for local LLM deployment (if using Ollama)

## Deployment Options

### Docker Desktop Installation (Ubuntu)
Docker Desktop is required for local Supabase deployment.

1.  **Download Docker Desktop:**
    Download the `.deb` package for Ubuntu from the official Docker Desktop website: [https://docs.docker.com/desktop/install/ubuntu/](https://docs.docker.com/desktop/install/ubuntu/)

2.  **Install Docker Desktop:**
    Open your terminal and navigate to the directory where you downloaded the `.deb` package. Then run:
    ```bash
    sudo apt-get install ./docker-desktop-amd64.deb
    ```
    Follow any on-screen prompts to complete the installation.

3.  **Start Docker Desktop:**
    After installation, launch Docker Desktop from your applications menu. Ensure it is running before attempting to start local Supabase services.

## Deployment Options

### Cloud Deployment
**Required Services:**
- Supabase project with pgvector enabled
- OpenAI API key or OpenRouter account
- Brave Search API key (optional: use SearXNG instead)

### Local Deployment
**Required Software:**
- [Local AI Package](https://github.com/coleam00/local-ai-packaged) (all-in-one)
  - OR manually: Ollama + SearXNG
- Supabase project (cloud database)
- Deno (for MCP code execution server)

### Hybrid Deployment
- Cloud LLM (OpenAI/OpenRouter) + Supabase database
- Local LLM (Ollama) + Supabase database

## Quick Start

1. **Install Agent Dependencies**
   ```bash
   make setup
   ```

2. **Install RAG Pipeline Dependencies**
   ```bash
   cd RAG_Pipeline
   python -m venv .venv
   # Windows: .venv\Scripts\activate
   # Unix: source .venv/bin/activate
   pip install -r requirements.txt
   ```

3. **Configure Environment**
   ```bash
   # Copy example configuration
   cp .env.example .env
   # Edit .env with your service credentials
   ```

4. **Supabase Setup**
   To use the database features, you need a Supabase project.
   - Go to [Supabase](https://supabase.com/) and create a new project.
   - Once your project is created, navigate to "Database" -> "Extensions" and enable the `pgvector` extension.
   - Obtain your project's URL and `service_role` key from "Project Settings" -> "API".
   - Update the `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` in your `.env` file with these credentials.
   - Run the SQL scripts located in the `sql/` directory to set up the necessary tables:
     ```bash
     # Example for running SQL scripts (replace with actual method, e.g., Supabase SQL Editor)
     # You can copy and paste the content of each .sql file into the Supabase SQL Editor and run them.
     # Files to run: documents.sql, document_metadata.sql, document_rows.sql
     ```

4b. **Local Supabase Deployment (Ubuntu)**
    If you prefer to run Supabase locally, follow these steps:

    **Install Supabase CLI:**
    ```bash
    sudo snap install supabase --channel=v1
    ```

    **Start Local Supabase Services:**
    Navigate to your project root directory and run:
    ```bash
    supabase init
    supabase start
    ```
    This will start all Supabase services (PostgreSQL, Auth, Storage, etc.) locally using Docker.

    **Get Local Supabase Credentials:**
    After `supabase start` completes, it will output the `API URL` and `anon key`. Use these values to update `SUPABASE_URL` and `SUPABASE_SERVICE_KEY` in your `.env` file.

    **Run SQL Scripts on Local Supabase:**
    You can run the SQL migration scripts using the Supabase CLI:
    ```bash
    supabase db diff --local > migrations/<timestamp>_initial_schema.sql
    supabase db push
    ```
    Alternatively, you can connect to your local PostgreSQL database (usually `postgresql://postgres:postgres@localhost:54322/postgres`) using a client like `psql` or `DBeaver` and execute the SQL files from the `sql/` directory manually.

4c. **Database Setup (using Makefile)**
    The `Makefile` includes a placeholder command for database setup. This command currently serves as a reminder to configure your Supabase project manually.
    ```bash
    make db-setup
    ```
    Follow the instructions in step 4 or 4b to set up your Supabase project and run the SQL scripts.

5. **Run the Streamlit UI**
   ```bash
   make run-ui
   ```
