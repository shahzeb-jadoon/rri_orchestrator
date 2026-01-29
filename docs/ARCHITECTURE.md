# RRI Orchestrator: System Architecture

**Last Updated:** January 29, 2026  
**Version:** Phase 1.6 with Dynamic Model Discovery  
**Production URL:** https://rri.zylot.tech

---

## Table of Contents

1. [Overview](#overview)
2. [System Architecture](#system-architecture)
3. [Component Breakdown](#component-breakdown)
4. [Database Schema](#database-schema)
5. [Data Flow](#data-flow)
6. [Model Discovery System](#model-discovery-system)
7. [Operational Commands](#operational-commands)
8. [Next Steps](#next-steps)

---

## Overview

The RRI Orchestrator is a research platform for studying robot-to-robot communication using Large Language Models. Researchers create experiments where AI-powered robot personas interact with each other, while the system tracks conversations, manages context windows, and provides analytics.

### Technology Stack

| Layer | Technology | Version |
|-------|------------|---------|
| Runtime | Python | 3.12 |
| Package Manager | uv | 0.9.x |
| Web Framework | NiceGUI + FastAPI | 1.4.x |
| Database | PostgreSQL | 16.11 |
| ORM | Tortoise ORM | 0.20.x |
| AI Integration | LiteLLM | 1.30.x |
| Containerization | Docker Compose | v2 |
| Process Manager | systemd | native |
| Authentication | Cloudflare Zero Trust | managed |

---

## System Architecture

```
                                    INTERNET
                                        |
                                   HTTPS (443)
                                        |
                            +-----------v-----------+
                            |   Cloudflare Tunnel   |
                            |   Zero Trust Auth     |
                            |   rri.zylot.tech      |
                            +-----------+-----------+
                                        |
================================================================================
                              JARVIS SERVER
                        Ubuntu 24.04 LTS (Dell)
           LAN: 192.168.0.5  |  Tailscale: 100.91.104.124
            i7-6700HQ (4c/8t)  |  16GB RAM  |  931GB SSD
================================================================================
                                        |
            +---------------------------v---------------------------+
            |                                                       |
            |              APPLICATION (Port 8080)                  |
            |              systemd: rri-orchestrator.service        |
            |                                                       |
            |   +-----------------------------------------------+   |
            |   |                  main.py                      |   |
            |   |  Startup: DB -> Model Cache -> BatchExecutor  |   |
            |   +-----------------------------------------------+   |
            |                          |                            |
            |   +----------------------+----------------------+     |
            |   |                      |                      |     |
            |   v                      v                      v     |
            |   +-----------+   +-----------+   +------------+      |
            |   | MIDDLEWARE|   |    UI     |   |     AI     |      |
            |   +-----------+   +-----------+   +------------+      |
            |   | auth.py   |   | pages/    |   | llm_service|      |
            |   | CF header |   | viewmodels|   | model_disc |      |
            |   | routing   |   | components|   | model_cfg  |      |
            |   +-----------+   +-----------+   | conversatn |      |
            |                                   +------------+      |
            |                          |                            |
            |   +----------------------v----------------------+     |
            |   |              BATCH PROCESSING               |     |
            |   |  executor.py (background asyncio worker)    |     |
            |   |  csv_parser.py (batch file handling)        |     |
            |   +---------------------------------------------+     |
            |                          |                            |
            +--------------------------|----------------------------+
                                       |
            +--------------------------|----------------------------+
            |                          v                            |
            |                    DATABASE LAYER                     |
            |   +---------------------------------------------+     |
            |   |           Tortoise ORM (models.py)          |     |
            |   |  User | Experiment | RobotProfile | Batch   |     |
            |   |  ChatMessage | ExperimentQueue | Summary    |     |
            |   +---------------------------------------------+     |
            |                          |                            |
            +--------------------------|----------------------------+
                                       |
            +--------------------------|----------------------------+
            |                    DOCKER SERVICES                    |
            |                                                       |
            |   +-------------------+   +-------------------+       |
            |   |   rri_postgres    |   |   rri_adminer     |       |
            |   |   postgres:16     |   |   adminer:latest  |       |
            |   |   Port: 5432      |   |   Port: 8081      |       |
            |   +-------------------+   +-------------------+       |
            +-------------------------------------------------------+
                                       |
================================================================================
                                       |
                                  HTTPS (API)
                                       |
            +--------------------------|----------------------------+
            |                   AI PROVIDERS                        |
            |                                                       |
            |   +-----------+   +-----------+   +------------+      |
            |   |  Gemini   |   |  OpenAI   |   | Anthropic  |      |
            |   |  30 models|   |  87 models|   |  5 models  |      |
            |   +-----------+   +-----------+   +------------+      |
            |                                                       |
            |         Dynamic Discovery with 24h Cache              |
            +-------------------------------------------------------+
```

---

## Component Breakdown

### Application Layer

| Module | Path | Purpose |
|--------|------|---------|
| Entry Point | `src/main.py` | Lifecycle management, startup/shutdown hooks |
| Configuration | `src/config.py` | Pydantic Settings, loads from `.env` |
| Logger | `src/utils/logger.py` | Centralized logging configuration |

### Middleware Layer

| Module | Path | Purpose |
|--------|------|---------|
| Authentication | `src/middleware/auth.py` | Cloudflare Zero Trust header parsing, user session |

**Authentication Flow:**
1. Cloudflare injects `CF-Access-Authenticated-User-Email` header
2. Middleware extracts email, finds or creates User record
3. First user automatically receives admin role
4. Subsequent users require admin approval via `/admin/users`

### UI Layer

| Module | Path | Purpose |
|--------|------|---------|
| Robots | `src/ui/pages/robots.py` | Robot profile CRUD with model selection |
| Experiments | `src/ui/pages/experiments.py` | Experiment list and chat interface |
| Batch | `src/ui/pages/batch.py` | CSV upload and batch creation |
| Batch Progress | `src/ui/pages/batch_progress.py` | Real-time monitoring with 2s refresh |
| Admin | `src/ui/pages/admin.py` | User management and approval |
| Deleted | `src/ui/pages/deleted_experiments.py` | Soft-deleted item recovery |
| Onboarding | `src/ui/pages/onboarding.py` | New user display name collection |
| ViewModels | `src/ui/viewmodels.py` | Zero-flicker state management |
| Navbar | `src/ui/components/navbar.py` | Navigation with user context |

**ViewModels Pattern:**
The application uses `@ui.refreshable` decorators combined with ViewModel classes to achieve zero-flicker updates. Instead of calling `.clear()` on containers (which destroys and rebuilds DOM elements), ViewModels hold state that NiceGUI diffs efficiently.

### AI Layer

| Module | Path | Purpose |
|--------|------|---------|
| LLM Service | `src/ai/llm_service.py` | LiteLLM integration, retry logic, error handling |
| Model Discovery | `src/ai/model_discovery.py` | Dynamic API-based model fetching with cache |
| Model Config | `src/ai/model_config.py` | Token pricing, default models, validation |
| Conversation | `src/ai/conversation.py` | Context window management, summarization |

### Batch Processing Layer

| Module | Path | Purpose |
|--------|------|---------|
| Executor | `src/batch/executor.py` | Background worker, concurrency control |
| CSV Parser | `src/batch/csv_parser.py` | Batch file parsing and validation |

**Executor Behavior:**
- Runs in separate process via multiprocessing
- Respects `max_concurrent` limit per batch (1-10)
- Pre-flight validation: API keys, robot existence, model availability
- Automatic retry on recoverable errors (rate limits, network timeouts)
- Graceful shutdown on SIGTERM

---

## Database Schema

```
+------------------+       +-------------------+       +------------------+
|      User        |       |    RobotProfile   |       | ExperimentBatch  |
+------------------+       +-------------------+       +------------------+
| id (PK)          |       | id (PK)           |       | id (PK)          |
| email (unique)   |       | name              |       | name             |
| display_name     |       | system_prompt     |       | status           |
| role             |<---+  | ai_provider       |       | max_concurrent   |
| is_active        |    |  | model_name        |       | created_by_id--->|
| is_approved      |    |  | default_temp      |       | paused_at        |
| approved_by_id   |    +--| created_by_id     |       | completed_at     |
| created_at       |       | created_at        |       +--------+---------+
| last_login       |       +-------------------+                |
+--------+---------+                                            |
         |                                                      |
         |  +---------------------------------------------------+
         |  |
         v  v
+------------------+       +-------------------+       +------------------+
|   Experiment     |       |   ChatMessage     |       | ExperimentQueue  |
+------------------+       +-------------------+       +------------------+
| id (PK)          |       | id (PK)           |       | id (PK)          |
| name             |       | experiment_id --->|       | batch_id ------->|
| description      |       | role              |       | experiment_id -->|
| created_by_id -->|       | content           |       | status           |
| created_by_email |       | timestamp         |       | queue_order      |
| robot_a_profile->|       | tokens_used       |       | started_at       |
| robot_b_profile->|       | input_tokens      |       | completed_at     |
| initial_prompt   |       | output_tokens     |       | error_message    |
| max_turns        |       | cost_usd          |       +------------------+
| batch_id ------->|       | robot_name        |
| batch_index      |       | robot_provider    |
| deleted_at       |       | is_interjection   |
| deleted_by_id -->|       | interjection_tgt  |
+------------------+       +-------------------+

+----------------------+
| ConversationSummary  |
+----------------------+
| id (PK)              |
| experiment_id ------>|
| summary_text         |
| messages_summarized  |
| created_at           |
+----------------------+
```

### Key Relationships

| Parent | Child | Cardinality | On Delete |
|--------|-------|-------------|-----------|
| User | Experiment | 1:N | SET NULL |
| User | RobotProfile | 1:N | SET NULL |
| User | ExperimentBatch | 1:N | SET NULL |
| RobotProfile | Experiment (as robot_a) | 1:N | SET NULL |
| RobotProfile | Experiment (as robot_b) | 1:N | SET NULL |
| ExperimentBatch | Experiment | 1:N | SET NULL |
| ExperimentBatch | ExperimentQueue | 1:N | CASCADE |
| Experiment | ChatMessage | 1:N | CASCADE |
| Experiment | ConversationSummary | 1:N | CASCADE |

The use of `SET NULL` instead of `CASCADE` on user-related foreign keys preserves data integrity when users are deactivated. Backup fields (`created_by_email`, `created_by_name`) maintain attribution even if the user record is modified.

---

## Data Flow

### Experiment Lifecycle

```
USER ACTION                           SYSTEM PROCESSING
-----------                           -----------------

[Manual Creation]
     |
     v
Click "New Experiment"
     |
     v
Select Robot A, Robot B
     |
     v
Enter initial prompt
     |
     +-----> CREATE Experiment (status: active)
             CREATE ChatMessage (role: system, content: prompt)


[Batch Creation]
     |
     v
Upload CSV file
     |
     v
Parser validates format -----> Error? Display validation message
     |
     v
Select Robot A, Robot B
Set max_concurrent (1-10)
     |
     +-----> CREATE ExperimentBatch
             FOR EACH row in CSV:
                 CREATE Experiment (status: queued)
                 CREATE ExperimentQueue (status: pending)


[Execution - BatchExecutor]
     |
     v
Poll for pending queue entries
     |
     v
Pre-flight checks:
  - API key configured?  -----> No? Mark failed: "API key not configured"
  - Robots exist?        -----> No? Mark failed: "Robot not found"
  - Model available?     -----> No? Refresh cache, suggest alternative
     |
     v
UPDATE ExperimentQueue (status: running)
     |
     v
FOR turn = 1 to max_turns:
  |
  +---> Robot A generates response
  |       |
  |       +---> Build context: system prompt + message history
  |       +---> Call LiteLLM -> Provider API
  |       |       |
  |       |       +---> Rate limit? Retry with backoff (1s, 2s, 4s)
  |       |       +---> 404 error? Refresh model cache
  |       |       +---> Success? Continue
  |       |
  |       +---> CREATE ChatMessage (role: robot_a)
  |               Record: tokens, cost, latency
  |
  +---> Robot B generates response (same flow, role: robot_b)
     |
     v
UPDATE Experiment (status: completed)
UPDATE ExperimentQueue (status: completed)
Calculate: total_tokens, total_cost, duration


[User Views Results]
     |
     +---> Batch Progress Page (auto-refresh 2s)
     |       BatchViewModel updates
     |       Progress bar, statistics, experiment list
     |
     +---> Experiments List
     |       Status badges: Complete, Running, Queued, Failed
     |       Click to open chat interface
     |
     +---> Export (CSV/JSON)
             Full metadata: messages, tokens, costs, timestamps
```

---

## Model Discovery System

The model discovery system eliminates manual maintenance of supported AI models. It queries provider APIs at startup and caches results for 24 hours.

### Startup Sequence

```
Application Start
       |
       v
initialize_model_cache()
       |
       v
Check: .nicegui/model_cache.json exists?
       |
       +--[No]--> Query APIs (Gemini, OpenAI, Anthropic)
       |              |
       |              v
       |          Save to disk
       |              |
       +--[Yes]-> Check: Cache age > 24 hours?
                      |
                      +--[No]--> Load from disk (fast path)
                      |
                      +--[Yes]-> Query APIs, update disk cache
```

### Error Recovery Flow

```
LLM Call
   |
   v
Response: 404 Model Not Found
   |
   v
retry_with_backoff() catches NotFoundError
   |
   v
handle_model_not_found()
   |
   +---> Refresh cache for provider
   |
   +---> Check migration mappings:
   |       gemini-pro      -> gemini-2.5-flash
   |       gemini-1.5-pro  -> gemini-2.5-pro
   |       gemini-1.5-flash-> gemini-2.5-flash
   |       gpt-4           -> gpt-4o
   |
   +---> Return error with suggestion:
           "Model 'gemini-pro' not available. Suggested: 'gemini-2.5-flash'"
```

### Cache Contents

The cache file `.nicegui/model_cache.json` contains:
- Timestamp of last refresh
- List of available models per provider
- Any discovery errors encountered

Current counts (as of January 2026):
- Gemini: 30 models
- OpenAI: 87 models
- Anthropic: 5 models

---

## Operational Commands

### Service Management

```bash
# View service status
systemctl status rri-orchestrator

# Restart after configuration changes
sudo systemctl restart rri-orchestrator

# View live logs
sudo journalctl -u rri-orchestrator -f

# View recent errors
sudo journalctl -u rri-orchestrator --since "1 hour ago" | grep -i error
```

### Model Cache Management

```bash
# View cache status and available models
uv run python scripts/model_cache_tool.py status

# Force refresh from provider APIs
uv run python scripts/model_cache_tool.py refresh

# Show deprecated model mappings
uv run python scripts/model_cache_tool.py migrations
```

### Database Operations

```bash
# Migrate robots using deprecated models
uv run python scripts/migrate_deprecated_models.py

# Initialize database schema
uv run python scripts/init_db.py

# Create admin user
uv run python scripts/create_user.py

# Verify setup
uv run python scripts/verify_setup.py
```

### Docker Services

```bash
# Check container status
docker compose ps

# View PostgreSQL logs
docker logs rri_postgres

# Access database shell
docker exec -it rri_postgres psql -U rri_user -d rri_orchestrator

# Backup database
docker exec rri_postgres pg_dump -U rri_user rri_orchestrator > backup.sql
```

---

## Next Steps

The following items represent the planned development roadmap, organized by priority and estimated effort.

### Phase 1.6 Completion (Estimated: 2 hours)

```
CURRENT STATE                              TARGET STATE
-------------                              ------------

Experiments Page                           Experiments Page
  |                                          |
  +-- Chat uses .clear()                     +-- Chat uses ViewModels
  |   (causes flicker)                       |   (zero flicker)
  |                                          |
  +-- No active user indicator               +-- Navbar shows "3 Active"
                                             |   with dropdown details
                                             |
                                             +-- Batch experiments
                                                 grouped/collapsible
```

| Task | File | Effort | Description |
|------|------|--------|-------------|
| Upgrade Chat | `experiments.py` | 1 hour | Replace `.clear()` with MessageViewModel pattern |
| Active Users Widget | `navbar.py` | 45 min | Display running experiments per user |
| Collapsible Batches | `experiments.py` | 30 min | Group batch experiments under expandable cards |

### Sprint 2.5: Advanced Controls (Estimated: 7 hours)

These features enable researchers to interact with experiments mid-execution.

```
EXPERIMENT LIFECYCLE (Enhanced)
-------------------------------

[Paused State]
     |
     +---> [Dynamic max_turns]
     |       Edit turn limit without restart
     |       Validation: new limit >= current turns
     |
     +---> [Researcher Interjection]
     |       Inject message visible to one or both robots
     |       Marked as system message in context
     |       Special styling in UI (yellow badge)
     |
     +---> [Message Impersonation]
             Write message as if from a robot
             Option: visible to other robot or hidden
             Tracked: actual_author_id for audit
```

| Task | Effort | Database Changes | Description |
|------|--------|------------------|-------------|
| Dynamic max_turns | 2 hours | None | Edit max_turns from pause menu |
| Interjection System | 3 hours | `is_interjection`, `interjection_target` | Inject researcher messages |
| Impersonation | 2 hours | `is_researcher_written`, `visible_to_other_robot`, `actual_author_id` | Ghost-write as robot |

### Database Migration for Sprint 2.5

```sql
-- Interjection fields (already added)
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS is_interjection BOOLEAN DEFAULT FALSE;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS interjection_target VARCHAR(20);

-- Impersonation fields (pending)
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS is_researcher_written BOOLEAN DEFAULT FALSE;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS visible_to_other_robot BOOLEAN DEFAULT TRUE;
ALTER TABLE chat_messages ADD COLUMN IF NOT EXISTS actual_author_id INTEGER REFERENCES users(id);
```

### Future Considerations

| Area | Description |
|------|-------------|
| Local LLMs | Ollama integration for offline/private experiments |
| Cost Analytics | Dashboard showing spend per provider, model, user |
| Experiment Templates | Save robot pairs and prompts as reusable templates |
| API Access | REST endpoints for programmatic experiment creation |
| Export Formats | PowerPoint generation for presentations |

---

## Appendix: Environment Variables

| Variable | Required | Description |
|----------|----------|-------------|
| `DATABASE_URL` | Yes | PostgreSQL connection string |
| `GEMINI_API_KEY` | Yes* | Google Gemini API key |
| `OPENAI_API_KEY` | Yes* | OpenAI API key |
| `SECRET_KEY` | Yes | Session encryption key |
| `ENVIRONMENT` | No | development or production |
| `HOST` | No | Bind address (default: 0.0.0.0) |
| `PORT` | No | Listen port (default: 8080) |
| `DEFAULT_AI_PROVIDER` | No | Default provider (default: gemini) |
| `MAX_TOKENS` | No | Max response tokens (default: 4096) |
| `TEMPERATURE` | No | Response temperature (default: 0.7) |
| `MAX_CONVERSATION_HISTORY` | No | Context window size (default: 50) |
| `ENABLE_AUTO_SUMMARY` | No | Auto-summarization (default: true) |

*At least one AI provider key is required for experiments to run.
