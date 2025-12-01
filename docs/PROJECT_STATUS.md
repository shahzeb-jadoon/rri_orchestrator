# RRI Orchestrator - Complete Project Status & Roadmap

**Last Updated:** November 30, 2025  
**Current Branch:** `feature/batch-models`  
**Production URL:** https://rri.zylot.tech

---

## 📊 Executive Summary

**Phase 1.6 Status:** ~85% Complete ✅  
**What Works:** Batch automation, CSV upload, BatchExecutor, Queue UI, ViewModels pattern, Soft delete, Multi-user  
**What's Next:** Upgrade experiments page chat, navbar widget, collapsible batches  
**Estimated Time to Phase 1.6 Complete:** 2-3 hours

---

## ✅ COMPLETED FEATURES

### **Phase 1 + 1.5: Foundation** ✅ COMPLETE
- ✅ User authentication (Cloudflare Zero Trust)
- ✅ Experiment CRUD operations
- ✅ Robot profile management
- ✅ Chat interface (manual turn-by-turn)
- ✅ CSV/JSON export with full metadata
- ✅ Database schema (PostgreSQL + Tortoise ORM)
- ✅ Production deployment (systemd service)

### **Phase 1.6 Week 1: Core Batch System** ✅ COMPLETE

**Day 1: Database Foundation** ✅ COMPLETE
- ✅ `ExperimentBatch` model (batches table)
- ✅ `ExperimentQueue` model (queue management)
- ✅ `batch_id` field added to Experiment model
- ✅ Database migration executed
- ✅ Model tests written (11/11 passing)

**Day 2-3: CSV Parser & Batch Creator** ✅ COMPLETE
- ✅ CSV parser (`src/batch/csv_parser.py`)
  - Supports header format: `prompt,description,max_turns`
  - Supports simple format: one prompt per line
  - Validates format and handles errors
  - Max 100 experiments per batch
- ✅ Batch creation UI (`/batch/create`)
  - File upload component
  - Real-time preview table
  - Robot selection dropdowns (Robot A, Robot B)
  - Order flipping checkbox
  - Max concurrent slider (1-10)
  - Summary cards (total experiments, average turns)
- ✅ Batch creation logic
  - Generates experiments from CSV
  - Creates ExperimentQueue entries
  - Assigns to selected robots
  - Tests: 11/11 passing

**Day 4-5: Smart Executor** ✅ COMPLETE
- ✅ `BatchExecutor` class (`src/batch/executor.py`)
  - Background asyncio worker
  - Pre-flight checks (API keys, robot validation)
  - Concurrency management (respects `max_concurrent`)
  - Graceful shutdown on server stop
  - Skips already-completed experiments
  - Automatic retry on recoverable errors
- ✅ Fixed `max_turns` logic
  - Now correctly creates 2 messages per exchange (one per robot)
  - `max_turns=5` → 10 total messages (5 from each robot)
- ✅ **Bonus Features:**
  - Status badges on experiments list (✓ Complete, 🔄 Running, ⏳ Queued, ⚠ Failed)
  - Intelligent error messages (Rate Limited, Auth Error, Quota, Network, Content Policy)
  - Color-coded severity (red/orange/yellow)
  - Actionable tooltips ("Wait a few minutes", "Contact admin")
- ✅ Auto-start on server boot (integrated with systemd)

**Day 6-7: Queue System UI** ✅ COMPLETE
- ✅ Batch progress page (`/batch/{batch_id}`)
  - Real-time monitoring (2-second auto-refresh)
  - Progress bar and statistics (completed/running/queued/failed)
  - Experiments list with status icons
  - Intelligent error messages (unified with experiments page)
  - Permission checks (creator or admin only)
- ✅ Batch controls
  - Pause button (stops new experiments, running ones continue)
  - Resume button (re-enables batch)
  - Cancel button (with confirmation dialog)
  - Tracks pause/resume metadata (paused_by, paused_at)
- ✅ "View Batch" links from experiments list
- ✅ **Zero-Flicker Updates** (ViewModels Pattern)
  - Created `src/ui/viewmodels.py`
  - Implemented `ExperimentViewModel` and `BatchViewModel`
  - Uses `@ui.refreshable` pattern (no `.clear()` flicker)
  - Smooth updates every 2 seconds
  - Scroll position preserved automatically

### **Phase 1.6 Week 2: Multi-User & Permissions** ✅ COMPLETE (Done Early!)

**User Management** ✅
- ✅ `User` model with roles (admin/researcher)
- ✅ `display_name` field for friendly names
- ✅ `is_active`, `is_approved` for access control
- ✅ First user auto-promoted to admin
- ✅ Admin approval system for new users
- ✅ Admin panel (`/admin/users`)
  - View all users
  - Approve/deactivate users
  - Self-service reactivation requests
- ✅ Onboarding page (`/onboarding`)
  - Collects display name on first login
  - Shows approval status

**Soft Delete** ✅
- ✅ `deleted_at` and `deleted_by` fields on Experiment model
- ✅ Soft delete instead of hard delete
- ✅ Deleted experiments page (`/experiments/deleted`)
- ✅ Recovery functionality (creator or admin)
- ✅ Permanent delete (admin only with confirmation)
- ✅ Permission checks (only creator or admin can delete)
- ✅ Creator badges on all experiments

**RBAC (Role-Based Access Control)** ✅
- ✅ Admin vs Researcher roles
- ✅ Permission middleware
- ✅ Admin-only features (user management, permanent delete)
- ✅ Creator permissions (delete own experiments)

---

## 🔄 IN PROGRESS

### **UX Refinements - Phase 1** (Current Sprint)

**Status:** 2/4 Complete

1. ✅ **Fix Auto-Scroll Issue** - COMPLETE
   - Implemented ViewModels pattern
   - Zero flicker on batch progress page
   - 2-second auto-refresh (smooth as butter)
   
2. ✅ **Unify Error Messages** - COMPLETE
   - Created `src/ui/utils.py` with shared `get_friendly_error_message()`
   - Batch progress page uses same intelligent parsing as experiments page
   - Consistent UX across all pages

3. ⏳ **Collapsible Batch Experiments** - TODO (30 min)
   - Group batch experiments under expandable cards
   - Show summary: "📦 Batch #4: 8/10 ✓"
   - Reduces clutter on experiments list
   - **Status:** Ready to implement

4. ⏳ **Fix Name Suggestion** - TODO (5 min)
   - Change example from "Shahzeb Jadoon" to "Justin Case"
   - Update onboarding page
   - **Status:** Ready to implement

---

## 📋 PENDING FEATURES

### **UX Refinements - Phase 2** (High Priority)

**Estimated Time:** 2 hours

1. ⏳ **Upgrade Experiments Page Chat** (1 hour)
   - **Issue:** Chat messages still use `.clear()` inside `@ui.refreshable` 
   - **Location:** `src/ui/pages/experiments.py` lines 498-540
   - **Fix:** Apply ViewModels pattern
     - Create `MessageViewModel`
     - Store messages in dict: `{msg_id: MessageViewModel}`
     - Remove `.clear()` from `display_messages()`
     - Update ViewModels on refresh
   - **Benefit:** No flicker when new messages appear during active conversation

2. ⏳ **Navbar Active Users Widget** (45 min)
   - **Location:** `src/ui/components/navbar.py`
   - **Display:** "👥 3 Active" button (top-right)
   - **Dropdown:** Shows who's running what
     ```
     Alice: Running 2 experiments
     Bob: Running 1 experiment
     Charlie: Viewing experiments
     ```
   - **Updates:** Every 30 seconds
   - **Implementation:**
     - Use `ActiveUserViewModel` (already created!)
     - Query running experiments with user info
     - Display on all authenticated pages
   - **Benefit:** Multi-user awareness, prevents conflicts

### **Sprint 2.5: Advanced Experiment Controls** ⭐ NEW

**Estimated Time:** 7 hours  
**Priority:** 🔴 Critical (Research-critical features)  
**Prerequisites:** Sprint 1 & 2 complete

1. ⏳ **Dynamic max_turns Update** (2 hours)
   - **Location:** `src/ui/pages/experiments.py` (pause menu)
   - **Feature:** Edit max_turns during paused experiment
   - **Implementation:**
     - Add number input to pause controls
     - Update Experiment.max_turns in database
     - Recalculate remaining turns
     - Show "Updated max_turns to 15" notification
   - **Database:** Already has max_turns field, just update it
   - **Validation:** Ensure new max_turns ≥ current message count / 2
   - **Value:** Adapt experiment length without restarting

2. ⏳ **Researcher Interjection System** (3 hours)
   - **Location:** `src/ui/pages/experiments.py` (pause menu)
   - **Feature:** Inject researcher message into conversation
   - **UI Controls:**
     - "Interject" button when paused
     - Target selector: "Robot A", "Robot B", "Both"
     - Message input textarea
   - **Implementation:**
     - Create ChatMessage with role="interjection"
     - Add `is_interjection` boolean field to ChatMessage model
     - Insert at current position in conversation
     - Next turn: target robot sees interjection first
     - If "Both": Robot A sees it, then Robot B sees it in their next turn
   - **History Preservation:**
     - Mark as system message in API calls
     - Include in conversation context
     - Display with special styling (researcher badge)
   - **Value:** Guide conversation, test robot responses to external input

3. ⏳ **Message Impersonation ("Ghost Write")** (2 hours)
   - **Location:** `src/ui/pages/experiments.py` (pause menu)
   - **Feature:** Send message pretending to be a robot
   - **UI Controls:**
     - "Send as Robot" button when paused
     - Robot selector: "Robot A" or "Robot B"
     - Message input textarea
     - Checkbox: "Other robot sees this" (default: true)
   - **Implementation:**
     - Create ChatMessage with robot_name (e.g., "robot_a")
     - Add `is_researcher_written` boolean field to ChatMessage
     - Option 1 (visible): Include in conversation history for both robots
     - Option 2 (hidden): Only include for the robot who "sent" it
   - **Database Schema:**
     ```python
     is_researcher_written = fields.BooleanField(default=False)
     visible_to_other_robot = fields.BooleanField(default=True)
     actual_author_id = fields.ForeignKeyField('User', null=True)  # Track researcher
     ```
   - **Display:**
     - Show special badge: "👻 Researcher-written as [Robot Name]"
     - Export includes metadata for research integrity
   - **Value:** Test counterfactual scenarios, A/B testing robot responses

### **UX Refinements - Phase 3** (Optional)

**Estimated Time:** 1-2 hours

1. ⏳ **Jump Queue Functionality**
   - High-priority checkbox on experiment creation
   - "Boost" button for queued experiments
   - Queue position badges: "⏳ Queued (#3)"
   - **Value:** Manual experiments can jump ahead of batches

2. ⏳ **Global Queue Dashboard** (`/queue` route)
   - System-wide queue overview
   - Shows all batches and their status
   - Sortable/filterable
   - **Value:** Admin monitoring

3. ⏳ **Code Refactoring** (if needed)
   - Extract large functions in `experiments.py`
   - Create reusable components
   - Only if adding more features

---

## 🚧 NOT STARTED

### **Phase 1.6 Week 3: Advanced Features**

**Estimated Time:** 1-2 weeks

1. ⏳ **Overnight Scheduling**
   - Scheduled batch start times
   - "Wait for manual approval" checkbox
   - Time-based triggers (10 PM)
   - Higher overnight concurrency (10 instead of 5)
   - Email notifications on completion
   - **Use Case:** Large batches run while team sleeps

2. ⏳ **Adaptive Concurrency**
   - Automatically reduce concurrency on rate limits
   - Exponential backoff for retries
   - **Current:** Fixed at 5 concurrent
   - **Improved:** Dynamically adjusts 1-10 based on API response

3. ⏳ **Cost Tracking**
   - Per-batch cost summaries
   - Budget alerts
   - Cost predictions before running
   - **Data:** Already collected (cost_usd in messages)

4. ⏳ **Load Testing**
   - Test 50-100 experiment batches
   - Multi-user simulation (3-5 users)
   - Concurrent batches
   - Stress test Dell server

5. ⏳ **Documentation**
   - Researcher user guide
   - CSV format examples
   - Troubleshooting guide
   - API documentation

### **Phase 2: Code Quality & Polish** (2-3 weeks)

**Estimated Time:** 2-3 weeks

**Type Hints** (5 days)
- ⏳ Add type hints to `src/ai/*.py`
- ⏳ Add type hints to `src/database/*.py`
- ⏳ Add type hints to `src/ui/*.py`
- ⏳ Configure `mypy` for type checking
- **Current:** Minimal type hints
- **Target:** 80%+ coverage

**Test Coverage** (5 days)
- ⏳ Write tests for BatchExecutor
- ⏳ Write tests for queue system
- ⏳ Write tests for permissions
- ⏳ Write tests for soft delete
- ⏳ Write tests for ViewModels (✅ already done!)
- **Current:** 21% coverage (per test output)
- **Target:** 60%+ coverage

**JSON Batch Support** (3 days)
- ⏳ Design JSON schema
- ⏳ Build JSON parser
- ⏳ Support nested configurations
- ⏳ Add JSON validation
- **Benefit:** More powerful than CSV (nested config, multiple robots)

**In-Batch Robot Creation** (3 days)
- ⏳ "Create new robot" option in batch UI
- ⏳ Quick robot profile builder
- ⏳ Save robot for future use
- ⏳ Robot template library
- **Benefit:** Don't need pre-created robots

**Per-User API Keys** (3 days)
- ⏳ User model: `openai_api_key`, `gemini_api_key`
- ⏳ Encrypted storage
- ⏳ API key management page
- ⏳ LiteLLM integration
- **Benefit:** Users bring own keys, no shared quota

**Refactoring** (5 days)
- ⏳ Break down `experiments.py` (893 lines!)
- ⏳ Extract reusable components
- ⏳ Improve error messages
- ⏳ Add inline documentation

### **Phase 3: Analytics Dashboard** (2 weeks)

**Sentiment Analysis** (5 days)
- ⏳ Integrate sentiment library
- ⏳ Analyze message sentiment per robot
- ⏳ Track sentiment trends
- ⏳ Store sentiment scores in DB

**Metrics Collection** (5 days)
- ⏳ Average tokens per turn
- ⏳ Cost per experiment
- ⏳ Response time distribution
- ⏳ Conversation length statistics
- ⏳ Topic extraction (keywords)

**Comparison Engine** (3 days)
- ⏳ Compare 2+ experiments
- ⏳ Highlight differences
- ⏳ Statistical significance tests
- ⏳ Export comparison reports

**Analytics UI** (5 days)
- ⏳ Dashboard page (`/analytics`)
- ⏳ Overview cards (total experiments, cost, etc.)
- ⏳ Charts (cost over time, tokens per model)
- ⏳ Per-experiment analytics view
- ⏳ Batch performance summary

### **Phase 4: Multi-Robot Conversations** (1 week)

**Database Redesign** (3 days)
- ⏳ Redesign Experiment model for N robots
- ⏳ Create `RobotParticipant` junction table
- ⏳ Update `ChatMessage` for multi-robot

**Turn Logic** (2 days)
- ⏳ Flexible turn ordering (round-robin, custom, role-based)
- ⏳ Skip inactive robots
- ⏳ Dynamic participant addition

**UI Updates** (2 days)
- ⏳ Multi-robot selection interface
- ⏳ Turn order configuration
- ⏳ Conversation view for 3+ participants
- ⏳ Color coding per robot

**Advanced Features** (2 days)
- ⏳ Role-based participation (moderator, debater, observer)
- ⏳ Sub-conversations (2 robots talk, others listen)
- ⏳ Custom turn sequences

**Deliverables:**

✅ 3-10 robot support
✅ Flexible turn ordering
✅ Role-based participation

### **Sprint 4.5: Robot Survey System** ⭐ NEW (Research-Critical)

**Estimated Time:** 1 week  
**Priority:** 🔴 Critical (Core research methodology)  
**Prerequisites:** Sprint 2.5 complete

**Feature:** Survey robots during experiments to gather structured responses

**1. Database Schema** (1 day)
```python
class RobotSurvey(Model):
    """Survey sent to robot(s) during experiment."""
    id = fields.IntField(primary_key=True)
    experiment = fields.ForeignKeyField('Experiment')
    survey_name = fields.CharField(max_length=200)
    questions = fields.JSONField()  # [{"id": 1, "text": "...", "type": "text/scale/multiple"}]
    target_robots = fields.JSONField()  # ["robot_a", "robot_b"] or ["robot_a"]
    created_at = fields.DatetimeField(auto_now_add=True)
    created_by = fields.ForeignKeyField('User')
    
class SurveyResponse(Model):
    """Robot responses to survey questions."""
    id = fields.IntField(primary_key=True)
    survey = fields.ForeignKeyField('RobotSurvey')
    robot_name = fields.CharField(max_length=50)  # "robot_a" or "robot_b"
    question_id = fields.IntField()
    response = fields.TextField()
    response_time_ms = fields.IntField()
    cost_usd = fields.DecimalField(max_digits=10, decimal_places=6)
    created_at = fields.DatetimeField(auto_now_add=True)
```

**2. UI: Survey Creation** (1 day)
- **Location:** Pause menu in `/experiments/{id}`
- **Controls:**
  - "📋 Survey Robots" button
  - Survey name input
  - Question builder (add/remove questions)
  - Target selector: "Robot A", "Robot B", "Both"
  - "Include in history" checkbox (default: false)
  - "Send Survey" button

**3. Survey Execution** (2 days)
- **Flow:**
  1. Researcher creates survey while paused
  2. System sends each question to robot(s) via LLM API
  3. Robot responds based on conversation history
  4. Responses saved to database
  5. Survey completion notification
- **API Integration:**
  - Use existing `generate_robot_response()` function
  - Pass survey question as system message
  - Include full conversation history in context
  - Track costs separately from conversation

**4. History Management** (1 day)
- **Option A: Forget Survey (Default)**
  - Survey Q&A NOT included in subsequent API calls
  - Robot continues conversation as if survey never happened
  - Survey exists only in database for analysis
  - **Implementation:** Don't add survey to ChatMessage table
  
- **Option B: Remember Survey**
  - Survey Q&A included in conversation context
  - Robot can reference survey in future responses
  - **Implementation:** Add survey to ChatMessage with `is_survey=True` flag
  - Filter on `is_survey=False` when "Forget" mode enabled

**5. Survey Analysis UI** (1 day)
- **Location:** New tab in experiment detail page
- **Display:**
  - List of all surveys sent during experiment
  - Expandable cards per survey
  - Q&A pairs per robot
  - Timestamp and cost tracking
  - Export survey data (CSV/JSON)
  - Compare responses between Robot A and Robot B

**6. Research Features** (1 day)
- **Survey Templates:**
  - Save survey as template for reuse
  - Template library ("Ethical Alignment", "Factual Accuracy", etc.)
- **Batch Surveys:**
  - Send same survey to all experiments in batch
  - Aggregate responses
- **A/B Testing:**
  - Run experiment twice (same setup)
  - Once with "Forget Survey" mode
  - Once with "Remember Survey" mode
  - Compare conversation outcomes

**Use Cases:**
1. **Mid-Conversation Assessment:**
   - Ask robot its current stance on topic
   - Measure opinion shift during conversation
   
2. **Factual Recall Testing:**
   - Survey robot on facts mentioned earlier
   - Test memory/context retention
   
3. **Ethical Alignment Checks:**
   - Present ethical dilemmas
   - Compare responses to robot's stated values
   
4. **Sentiment Tracking:**
   - Ask robot to rate conversation quality
   - Self-reported engagement levels

**Value:**
- ✅ Structured data collection during experiments
- ✅ Non-invasive (survey doesn't disrupt conversation if "Forget" mode)
- ✅ A/B testing of survey impact on conversation
- ✅ Comparative analysis between robots
- ✅ Longitudinal tracking (same survey at different points)

### **Phase 5: Production Hardening** (1 week, optional)

**Monitoring** (2 days)
- ⏳ Prometheus metrics
- ⏳ Grafana dashboards
- ⏳ Alert system (email/Slack)
- ⏳ Performance monitoring

**Backup & Recovery** (2 days)
- ⏳ Automated database backups
- ⏳ S3 export for data
- ⏳ Disaster recovery plan
- ⏳ Data migration tools

**Security** (3 days)
- ⏳ Audit log viewer
- ⏳ IP whitelisting (optional)
- ⏳ API key rotation
- ⏳ Security headers

---

## 📂 Current File Structure

```
rri_orchestrator/
├── src/
│   ├── ai/                      # AI/LLM integration
│   │   ├── conversation.py      # Multi-turn orchestration
│   │   ├── llm_service.py       # LiteLLM wrapper
│   │   ├── model_config.py      # Model configs
│   │   ├── summarization.py     # Context window management
│   │   └── token_counter.py     # Token counting
│   ├── batch/                   # ✅ Batch automation
│   │   ├── csv_parser.py        # ✅ CSV parsing logic
│   │   ├── executor.py          # ✅ Background worker
│   │   └── __init__.py
│   ├── database/
│   │   ├── models.py            # ✅ All database models
│   │   └── session.py           # Database connection
│   ├── middleware/
│   │   └── auth.py              # ✅ Cloudflare auth
│   ├── ui/
│   │   ├── components/
│   │   │   └── navbar.py        # Global navbar
│   │   ├── pages/
│   │   │   ├── admin.py         # ✅ User management
│   │   │   ├── batch.py         # ✅ Batch creation
│   │   │   ├── batch_progress.py # ✅ Batch monitoring (ViewModels!)
│   │   │   ├── deleted_experiments.py # ✅ Soft delete recovery
│   │   │   ├── experiments.py   # ⚠️ Chat (needs ViewModel upgrade)
│   │   │   ├── onboarding.py    # ✅ First-time user setup
│   │   │   └── robots.py        # Robot CRUD
│   │   ├── utils.py             # ✅ Shared UI utilities (error messages)
│   │   └── viewmodels.py        # ✅ ViewModels pattern
│   ├── utils/
│   │   └── logger.py            # Logging
│   ├── config.py                # App configuration
│   └── main.py                  # Application entry point
├── tests/
│   ├── test_ai.py
│   ├── test_batch_models.py     # ✅ 11/11 passing
│   ├── test_csv_parser.py       # ✅ 11/11 passing
│   ├── test_db.py
│   ├── test_live_integration.py
│   ├── test_retry_logic.py
│   ├── test_robot_profiles.py
│   ├── test_ui.py
│   └── test_viewmodels.py       # ✅ NEW - 3/3 passing
├── docs/
│   ├── BATCH_TESTING_GUIDE.md
│   ├── TESTING.md
│   ├── VIEWMODELS_ARCHITECTURE.md  # ✅ NEW - Full pattern docs
│   └── VIEWMODELS_QUICKSTART.md    # ✅ NEW - Quick reference
├── scripts/
│   ├── create_user.py
│   ├── init_db.py
│   ├── migrate_phase2.5.py
│   ├── migrate_phase2.py
│   └── verify_phase2.py
├── pyproject.toml
├── README.md
└── docker-compose.yml
```

---

## 🎯 Immediate Next Steps (Recommended Priority)

### **Option A: Complete Phase 1 UX (Recommended)**
**Time:** 2 hours  
**Value:** Polished user experience, no flicker anywhere

1. ✅ Upgrade experiments page chat (1 hour)
2. ✅ Add navbar active users widget (45 min)
3. ✅ Implement collapsible batch experiments (30 min)

**After this:** Phase 1.6 is 100% complete! 🎉

### **Option B: Jump to Advanced Features**
**Time:** 1-2 weeks  
**Value:** More powerful functionality

1. ⏳ Overnight scheduling (3 days)
2. ⏳ Adaptive concurrency (2 days)
3. ⏳ Cost tracking (2 days)
4. ⏳ Load testing (1 day)

### **Option C: Improve Code Quality First**
**Time:** 2-3 weeks  
**Value:** Easier maintenance, fewer bugs

1. ⏳ Type hints everywhere (5 days)
2. ⏳ Increase test coverage to 60% (5 days)
3. ⏳ JSON batch support (3 days)
4. ⏳ Refactoring (5 days)

---

## 💡 My Recommendation

**Phase Priority:**
1. **Sprint 1:** Complete Phase 1.6 UX (2 hours) ← START HERE
2. **Sprint 2:** Advanced features (overnight scheduling, cost tracking)
3. **Sprint 2.5:** Advanced Experiment Controls (7 hours) ← RESEARCH-CRITICAL
4. **Sprint 4.5:** Robot Survey System (1 week) ← RESEARCH-CRITICAL
5. **Sprint 3:** Code quality (can happen in parallel)
6. **Sprint 4:** Multi-robot (if needed)

**Why Sprint 2.5 and 4.5 are HIGH PRIORITY:**
- These are **research methodology features**, not just "nice to have"
- Enable controlled experiments (interjection, impersonation)
- Provide structured data collection (surveys)
- Support A/B testing (survey memory vs. forget)
- Critical for academic rigor

**Recommended Order:**
1. ✅ Complete Sprint 1 (2 hours) - Finish Phase 1.6
2. ✅ Use system for 1 week - Validate basic batch automation
3. ✅ Implement Sprint 2.5 (7 hours) - Advanced controls for active research
4. ✅ Test controls with real experiments (1 week)
5. ✅ Implement Sprint 4.5 (1 week) - Survey system
6. ✅ Code quality improvements (Sprint 3) - In parallel with usage
7. ❓ Decide on analytics/multi-robot based on research needs

**Total Time to Research-Ready Platform:** ~3 weeks (not 3 months!)

---

## 📊 Feature Matrix

| Feature | Status | Time to Complete | Priority |
|---------|--------|------------------|----------|
| **Phase 1.6 Core** | ✅ 85% | 2 hours | 🔴 Critical |
| Upgrade chat page | ⏳ Pending | 1 hour | 🔴 Critical |
| Navbar widget | ⏳ Pending | 45 min | 🟡 High |
| Collapsible batches | ⏳ Pending | 30 min | 🟡 High |
| Fix name suggestion | ⏳ Pending | 5 min | ⚪ Low |
| **Sprint 2.5: Advanced Controls** | ⏳ Not Started | 7 hours | 🔴 Critical |
| Dynamic max_turns | ⏳ Not Started | 2 hours | 🔴 Critical |
| Researcher interjection | ⏳ Not Started | 3 hours | 🔴 Critical |
| Message impersonation | ⏳ Not Started | 2 hours | 🔴 Critical |
| **Sprint 4.5: Robot Surveys** | ⏳ Not Started | 1 week | 🔴 Critical |
| Survey database schema | ⏳ Not Started | 1 day | 🔴 Critical |
| Survey creation UI | ⏳ Not Started | 1 day | 🔴 Critical |
| Survey execution | ⏳ Not Started | 1 day | 🔴 Critical |
| History management | ⏳ Not Started | 1 day | 🔴 Critical |
| Survey analysis UI | ⏳ Not Started | 1 day | 🔴 Critical |
| Batch survey support | ⏳ Not Started | 1 day | 🔴 Critical |
| **Overnight Scheduling** | ⏳ Not Started | 3 days | 🟢 Medium |
| **Adaptive Concurrency** | ⏳ Not Started | 2 days | 🟢 Medium |
| **Cost Tracking** | ⏳ Not Started | 2 days | 🟢 Medium |
| **Load Testing** | ⏳ Not Started | 1 day | 🟢 Medium |
| **Type Hints** | ⏳ Not Started | 5 days | 🟢 Medium |
| **Test Coverage (60%)** | ⏳ Not Started | 5 days | 🟡 High |
| **JSON Batch Support** | ⏳ Not Started | 3 days | ⚪ Low |
| **In-Batch Robot Creation** | ⏳ Not Started | 3 days | ⚪ Low |
| **Per-User API Keys** | ⏳ Not Started | 3 days | 🟡 High |
| **Analytics Dashboard** | ⏳ Not Started | 2 weeks | ⚪ Low |
| **Multi-Robot (3+)** | ⏳ Not Started | 1 week | ⚪ Low |
| **Production Monitoring** | ⏳ Not Started | 1 week | 🟢 Medium |

---

## 🔬 Testing Status

**Unit Tests:** 17/17 passing ✅
- Batch models: 11/11
- CSV parser: 11/11
- ViewModels: 3/3
- AI/DB/UI: Existing tests

**Live Integration Tests:** Available (use `@pytest.mark.live`)

**Coverage:** ~21% (needs improvement)

**Test Commands:**
```bash
# Run all tests
python3 -m pytest tests/ -v

# Run specific test file
python3 -m pytest tests/test_batch_models.py -v

# Run with coverage
python3 -m pytest tests/ --cov=src --cov-report=html
```

---

## 🐛 Known Issues

### **Minor Issues:**
1. ⚠️ Experiments page chat uses `.clear()` (causes flicker during active conversation)
   - **Impact:** Low (only visible during auto-refresh in manual mode)
   - **Fix:** Apply ViewModels pattern (1 hour)

2. ⚠️ No global user activity visibility
   - **Impact:** Medium (multi-user confusion)
   - **Fix:** Navbar widget (45 min)

3. ⚠️ Batch experiments clutter main list
   - **Impact:** Low (cosmetic)
   - **Fix:** Collapsible groups (30 min)

### **No Critical Bugs!** ✅

---

## 📅 Timeline Estimate

**If following Option A (Complete Phase 1):**

| Week | Focus | Deliverables |
|------|-------|--------------|
| **Week 1** (Now) | UX Polish | ✅ Upgrade chat, navbar widget, collapsible batches |
| **Week 2-3** | Team Usage | 📊 Gather feedback, run real experiments |
| **Week 4-6** | Code Quality | 🧪 Type hints, tests, JSON support |
| **Week 7-8** | Advanced Features | ⏰ Overnight scheduling, cost tracking |
| **Week 9-12** | Analytics or Multi-Robot | 📈 Based on user needs |

**Total to Full Production:** ~3 months

---

## 🎓 Architecture Patterns Established

1. **ViewModels Pattern** ✅
   - Zero-flicker updates
   - Declarative UI
   - Reusable across pages
   - Documented in `docs/VIEWMODELS_ARCHITECTURE.md`

2. **Soft Delete** ✅
   - 30-day retention
   - Recovery functionality
   - Preserves research data

3. **Batch Automation** ✅
   - Background worker
   - Concurrency control
   - Smart retry logic

4. **Permission System** ✅
   - Admin vs Researcher roles
   - Creator-based permissions
   - Approval workflow

---

## 📞 Questions for Decision Making

1. **Priority:** Complete Phase 1 UX first, or jump to advanced features?
2. **Analytics:** Do you need sentiment analysis and dashboards soon?
3. **Multi-Robot:** Is 3+ robot support needed for your research?
4. **Code Quality:** Can type hints/tests happen in parallel with usage?
5. **Scheduling:** Do you need overnight batch automation immediately?

---

**Ready to proceed with the 2-hour UX polish sprint?** This will:
- ✅ Upgrade experiments chat (no flicker)
- ✅ Add navbar user tracking
- ✅ Implement collapsible batches
- 🎉 Complete Phase 1.6!
