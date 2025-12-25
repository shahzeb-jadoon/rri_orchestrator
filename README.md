# RRI Orchestrator

**AI-powered orchestration system for robot-robot interactions with web-based interface**

## What Is This?

The RRI Orchestrator is a research platform that simulates and studies robot-to-robot communication using Large Language Models. Researchers can create experiments where AI-powered robot personas interact with each other, while the system tracks conversations, manages context windows, and provides detailed analytics. Perfect for studying emergent behaviors in multi-agent AI systems.

---

## Overview

The RRI Orchestrator is designed for research teams to:

- Create and manage robot interaction experiments
- Simulate robot conversations using various AI providers (Gemini, OpenAI, local LLMs)
- Track and analyze conversation histories
- Manage context windows efficiently to optimize AI costs
- Access experiments from multiple devices through a secure web interface

### Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Devices                         │
│  (Alienware, MacBooks, etc. - Access via Web Browser)       │
└────────────────────────┬────────────────────────────────────┘
                         │
                         │ HTTPS (Cloudflare Tunnel)
                         │
┌────────────────────────▼────────────────────────────────────┐
│                   Dell Server (Ubuntu)                       │
│  ┌─────────────────────────────────────────────────────┐   │
│  │  NiceGUI Web App (Port 8080)                        │   │
│  │  - FastAPI Backend                                   │   │
│  │  - Chat Interface                                    │   │
│  │  - Experiment Management                             │   │
│  └──────────────┬──────────────────┬───────────────────┘   │
│                 │                  │                         │
│  ┌──────────────▼─────────┐  ┌────▼──────────────────┐     │
│  │  PostgreSQL Database    │  │  LiteLLM Adapter      │     │
│  │  - Experiments          │  │  - Gemini/OpenAI      │     │
│  │  - Messages             │  │  - Ollama (future)    │     │
│  │  - Users                │  │                        │     │
│  └─────────────────────────┘  └────────────────────────┘     │
└─────────────────────────────────────────────────────────────┘
```

---

## Project Structure

```
rri-orchestrator/
├── .github/
│   └── workflows/
│       └── test.yml           # CI/CD pipeline
├── scripts/
│   ├── init_db.py             # Initialize database tables
│   └── create_user.py         # Create admin user
├── src/
│   ├── __init__.py
│   ├── main.py                # Application entry point
│   ├── config.py              # Configuration management
│   ├── ai/                    # AI integration (Phase 2)
│   ├── database/
│   │   ├── models.py          # Database schema
│   │   └── session.py         # Connection management
│   ├── ui/                    # User interface (Phase 1)
│   └── utils/
│       └── logger.py          # Logging setup
├── tests/
│   ├── conftest.py            # Test configuration
│   ├── test_db.py             # Database tests
│   ├── test_ai.py             # AI integration tests
│   └── test_ui.py             # UI tests
├── .env                       # Environment variables (DO NOT COMMIT)
├── .env.example               # Template for .env
├── .gitignore
├── docker-compose.yml         # PostgreSQL + Adminer
├── pyproject.toml             # Project dependencies
└── README.md
```

---

## Setup Instructions

### Prerequisites

- **Python 3.11+**
- **Docker** (for PostgreSQL)
- **uv** (Python package manager)

### 1. Install uv

On Ubuntu/WSL:

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

After installation, restart your terminal or run:

```bash
source $HOME/.cargo/env
```

### 2. Clone and Navigate to Project

```bash
cd ~/projects/rri_orchestrator
```

### 3. Install Dependencies

```bash
uv sync
```

This creates a virtual environment and installs all required packages.

### 4. Configure Environment Variables

Create a `.env` file from the template:

```bash
cp .env.example .env
```

Edit `.env` with your actual values:

```bash
nano .env
```

**Required values:**

- `GEMINI_API_KEY`: Get from [Google AI Studio](https://makersuite.google.com/app/apikey)
- `OPENAI_API_KEY`: Get from [OpenAI Platform](https://platform.openai.com/api-keys)
- `SECRET_KEY`: Generate with `openssl rand -hex 32`

### 5. Start PostgreSQL Database

```bash
docker-compose up -d
```

This starts:
- PostgreSQL on port `5432`
- Adminer (database UI) on port `8081`

Verify it's running:

```bash
docker ps
```

### 6. Initialize Database

```bash
uv run python scripts/init_db.py
```

This creates all necessary tables in PostgreSQL.

### 7. Create Admin User

```bash
uv run python scripts/create_user.py
```

Follow the prompts to create your first user account.

---

## Running the Application

### Development Mode

**On the Dell server:**

```bash
uv run python src/main.py
```

The application will be available at `http://localhost:8080`

### Production Mode (Systemd Service)

For production deployment with automatic startup on boot, see the [Deployment Guide](deployment/README.md).

**Quick setup:**

```bash
sudo cp deployment/rri-orchestrator.service /etc/systemd/system/
sudo systemctl daemon-reload
sudo systemctl enable rri-orchestrator
sudo systemctl start rri-orchestrator
```

### Access from Other Devices (via Cloudflare Tunnel)

1. Install Cloudflare Tunnel:

```bash
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb
```

2. Create a tunnel:

```bash
cloudflared tunnel --url http://localhost:8080
```

3. Access the provided URL from any device on the internet

---

## Development Workflow

### Git Branching Strategy

```
main (production-ready code)
├── phase-1-foundation (integration branch)
│   ├── feat/ui-skeleton
│   ├── feat/chat-component
│   └── feat/cloudflare-deploy
├── phase-2-ai-integration (integration branch)
│   ├── feat/litellm-setup
│   ├── feat/ai-service
│   └── feat/memory-management
└── phase-3-advanced-features
```

**Workflow:**

1. Create a feature branch from a phase branch
2. Implement and test your changes
3. Commit with descriptive messages (e.g., `feat: add chat interface component`)
4. Merge feature back into phase branch
5. When phase is complete, merge into `main`

### Running Tests

Run all tests:

```bash
uv run pytest
```

Run specific test file:

```bash
uv run pytest tests/test_db.py
```

Run with coverage report:

```bash
uv run pytest --cov=src --cov-report=html
```

View coverage report:

```bash
open htmlcov/index.html
```

### Database Management

**Access Adminer (Database UI):**

Open `http://localhost:8081` in your browser

- **System:** PostgreSQL
- **Server:** postgres
- **Username:** rri_user
- **Password:** rri_password
- **Database:** rri_orchestrator

**Create database backup:**

```bash
docker exec rri_postgres pg_dump -U rri_user rri_orchestrator > backup.sql
```

**Restore from backup:**

```bash
cat backup.sql | docker exec -i rri_postgres psql -U rri_user -d rri_orchestrator
```

---

## Database Schema

### Core Tables

**users**
- Authentication and user profiles
- Tracks admin privileges

**experiments**
- Research sessions with specific parameters
- Links to users and contains multiple messages

**chat_messages**
- Individual conversation messages
- Stores role (user/assistant/system), content, and metadata

**conversation_summaries**
- Summarized history for context window management
- Links to message ranges

**robot_profiles**
- Reusable robot personality definitions
- System prompts and behavioral parameters

---

## Configuration

All settings are managed through environment variables (`.env` file) or can be overridden at runtime.

### Key Settings

| Variable | Default | Description |
|----------|---------|-------------|
| `DATABASE_URL` | `postgresql+asyncpg://...` | PostgreSQL connection string |
| `GEMINI_API_KEY` | - | Google Gemini API key |
| `OPENAI_API_KEY` | - | OpenAI API key |
| `DEFAULT_AI_PROVIDER` | `gemini` | Which AI provider to use |
| `MAX_CONVERSATION_HISTORY` | `50` | Messages to keep in context |
| `ENABLE_AUTO_SUMMARY` | `true` | Auto-summarize old conversations |
| `HOST` | `0.0.0.0` | Server bind address |
| `PORT` | `8080` | Server port |

---

## Phase Roadmap

### ✅ Phase 1: Foundation (Current)

- [x] Project structure and configuration
- [x] Database setup with PostgreSQL
- [x] Basic web interface skeleton
- [x] User authentication
- [x] Testing infrastructure
- [x] CI/CD pipeline

### 🔄 Phase 2: AI Integration (Next)

- [ ] LiteLLM service implementation
- [ ] Chat interface with streaming responses
- [ ] Context window management
- [ ] AI cost tracking
- [ ] Multi-provider fallback

### 📋 Phase 3: Advanced Features

- [ ] Robot profile management
- [ ] Experiment analytics
- [ ] Real-time collaboration
- [ ] Export/import functionality
- [ ] Local LLM support (Ollama)

---

## Troubleshooting

### Database Connection Failed

Check if PostgreSQL is running:

```bash
docker ps | grep postgres
```

Restart if needed:

```bash
docker-compose restart postgres
```

### Port Already in Use

Find process using port 8080:

```bash
lsof -i :8080
```

Kill the process:

```bash
kill -9 <PID>
```

### Import Errors

Ensure you're using the virtual environment:

```bash
uv sync
uv run python src/main.py
```

---

## Contributing

1. Create a feature branch: `git checkout -b feat/your-feature`
2. Write tests for your changes
3. Ensure all tests pass: `uv run pytest`
4. Commit with clear messages: `feat: add description`
5. Push and create a pull request

---

## License

This project is for research purposes. See your institution's policies regarding code ownership and distribution.

---

## Support

For issues or questions:
- Check the [Troubleshooting](#troubleshooting) section
- Review test files for usage examples
- Check logs in the console output

---

**Built with:** NiceGUI, FastAPI, PostgreSQL, Tortoise ORM, LiteLLM
