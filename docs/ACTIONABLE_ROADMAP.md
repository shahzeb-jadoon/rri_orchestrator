# RRI Orchestrator - Actionable Implementation Roadmap

**Last Updated:** November 30, 2025  
**Current Status:** Phase 1.6 @ 85% Complete

---

## 🎯 SPRINT 1: Complete Phase 1.6 UX (2 hours) ⭐ RECOMMENDED

**Goal:** Finish Phase 1.6 with polished, flicker-free UI  
**Status:** Ready to implement NOW  
**Estimated Time:** 2 hours

### Task 1.1: Upgrade Experiments Chat (1 hour)
**File:** `src/ui/pages/experiments.py` (lines 495-540)  
**Priority:** 🔴 Critical

**Steps:**
1. Add `MessageViewModel` to `src/ui/viewmodels.py` (10 min)
   ```python
   class MessageViewModel:
       def __init__(self, msg_id, content, robot_name, ...):
           self.id = msg_id
           self.content = content
           self.robot_name = robot_name
           self.timestamp = timestamp
   ```

2. Refactor `display_messages()` function (30 min)
   - Store messages in dict: `message_vms = {}`
   - Remove `.clear()` from inside `@ui.refreshable`
   - Read from ViewModels instead of DB query

3. Update refresh logic (15 min)
   - Load messages into ViewModels
   - Call `display_messages.refresh()`

4. Test (5 min)
   - Start experiment
   - Scroll down
   - Click "Next Turn" button
   - Verify no flicker when new message appears

**Success Criteria:**
- ✅ No flicker when messages appear
- ✅ Scroll position preserved
- ✅ Messages render smoothly

---

### Task 1.2: Navbar Active Users Widget (45 min)
**File:** `src/ui/components/navbar.py`  
**Priority:** 🟡 High

**Steps:**
1. Add active users query function (15 min)
   ```python
   async def get_active_users():
       running = await ExperimentQueue.filter(
           status='running'
       ).prefetch_related('experiment__created_by')
       # Group by user...
       return user_activities
   ```

2. Add navbar widget (20 min)
   ```python
   @ui.refreshable
   def render_active_users():
       count = len(active_users)
       with ui.button(f'👥 {count} Active'):
           with ui.menu():
               for user in active_users:
                   ui.item(f'{user.name}: {user.activity}')
   ```

3. Add auto-refresh timer (5 min)
   ```python
   ui.timer(30.0, load_and_refresh_users)
   ```

4. Test (5 min)
   - Start 2 experiments from different users
   - Check navbar shows "👥 2 Active"
   - Click dropdown, verify shows both users

**Success Criteria:**
- ✅ Shows active user count
- ✅ Dropdown lists who's running what
- ✅ Updates every 30 seconds

---

### Task 1.3: Collapsible Batch Experiments (30 min)
**File:** `src/ui/pages/experiments.py` (experiments list function)  
**Priority:** 🟡 High

**Steps:**
1. Group experiments by batch (10 min)
   ```python
   batch_groups = {}  # {batch_id: [experiment, ...]}
   standalone_experiments = []
   
   for exp in experiments:
       if exp.batch_id:
           if exp.batch_id not in batch_groups:
               batch_groups[exp.batch_id] = []
           batch_groups[exp.batch_id].append(exp)
       else:
           standalone_experiments.append(exp)
   ```

2. Render with `ui.expansion()` (15 min)
   ```python
   # Render batch groups first
   for batch_id, batch_exps in batch_groups.items():
       completed = sum(1 for e in batch_exps if queue_status[e.id] == 'completed')
       total = len(batch_exps)
       
       with ui.expansion(f'📦 Batch #{batch_id}: {completed}/{total} ✓'):
           for exp in batch_exps:
               render_experiment_card(exp)
   
   # Render standalone experiments
   for exp in standalone_experiments:
       render_experiment_card(exp)
   ```

3. Test (5 min)
   - View experiments list with batch
   - Verify batch is collapsed by default
   - Click to expand, verify experiments appear

**Success Criteria:**
- ✅ Batch experiments grouped under expansion
- ✅ Shows summary: "📦 Batch #4: 8/10 ✓"
- ✅ Standalone experiments visible as normal
- ✅ Reduces visual clutter

---

### Task 1.4: Fix Name Suggestion (5 min)
**File:** `src/ui/pages/onboarding.py`  
**Priority:** ⚪ Low (UX polish)

**Steps:**
1. Locate name input field with placeholder
2. Change placeholder from current value to "Justin Case"
3. Test onboarding flow

**Success Criteria:**
- ✅ Onboarding shows "Justin Case" as example name
- ✅ No functionality changes

---

## 🚀 SPRINT 2: Advanced Features (1-2 weeks)

**Goal:** Production-ready batch automation  
**Prerequisites:** Sprint 1 complete  
**Estimated Time:** 5-10 days

### Task 2.1: Overnight Scheduling (3 days)
**Priority:** 🟢 Medium  
**Value:** Run large batches while team sleeps

**Steps:**
1. Add `scheduled_start` field to ExperimentBatch model
2. Add scheduling UI to batch creation page
3. Modify BatchExecutor to respect scheduled times
4. Add email notification on completion
5. Increase overnight max_concurrent to 10

**Success Criteria:**
- ✅ Can schedule batch for specific time
- ✅ Batch starts automatically at scheduled time
- ✅ Email sent on completion

---

### Task 2.2: Adaptive Concurrency (2 days)
**Priority:** 🟢 Medium  
**Value:** Better API quota management

**Steps:**
1. Detect rate limit errors in BatchExecutor
2. Automatically reduce max_concurrent (10 → 5 → 2 → 1)
3. Exponential backoff for retries
4. Gradually increase back to normal

**Success Criteria:**
- ✅ Doesn't hit rate limits repeatedly
- ✅ Automatically adjusts concurrency
- ✅ Logs adjustments

---

### Task 2.3: Cost Tracking Dashboard (2 days)
**Priority:** 🟢 Medium  
**Value:** Budget awareness

**Steps:**
1. Add cost summary to batch progress page
2. Show per-experiment cost breakdown
3. Add total batch cost prediction
4. Create `/batches` list page with cost column

**Success Criteria:**
- ✅ Shows estimated cost before starting
- ✅ Real-time cost tracking during execution
- ✅ Final cost summary

---

### Task 2.4: Load Testing (1 day)
**Priority:** 🟢 Medium  
**Value:** Confidence in production

**Steps:**
1. Create 100-experiment test batch
2. Run 3 batches simultaneously (different users)
3. Monitor server resources (CPU, RAM, DB)
4. Verify no crashes or slowdowns

**Success Criteria:**
- ✅ Dell server handles 100+ experiments
- ✅ Multiple users can run batches concurrently
- ✅ No performance degradation

---

## 🎮 SPRINT 2.5: Advanced Experiment Controls (7 hours) ⭐ RESEARCH-CRITICAL

**Goal:** Enable researcher intervention in active experiments  
**Prerequisites:** Sprint 1 complete  
**Estimated Time:** 7 hours  
**Priority:** 🔴 CRITICAL (research methodology features)

### Task 2.5.1: Dynamic max_turns Update (2 hours)
**Priority:** 🔴 Critical  
**Value:** Extend/shorten experiments in real-time

**Steps:**
1. Add max_turns update to pause menu UI (30 min)
   ```python
   with ui.dialog() as pause_dialog:
       ui.label('Experiment Paused')
       new_max_turns = ui.number('Max Turns', value=experiment.max_turns)
       ui.button('Update & Resume', on_click=lambda: update_max_turns(new_max_turns.value))
   ```

2. Add update method to Experiment model (30 min)
   ```python
   async def update_max_turns(self, new_value: int):
       self.max_turns = new_value
       await self.save()
   ```

3. Validate new max_turns (30 min)
   - Must be >= current message count
   - Show error if trying to reduce below current progress
   - Update UI to show new max_turns immediately

4. Test edge cases (30 min)
   - Extend mid-experiment (20 → 30)
   - Reduce mid-experiment (30 → 22, current = 15)
   - Try to reduce below current (should error)

**Success Criteria:**
- ✅ Can change max_turns from pause menu
- ✅ Validates new value >= current progress
- ✅ UI updates immediately
- ✅ Experiment continues with new limit

---

### Task 2.5.2: Researcher Interjection System (3 hours)
**Priority:** 🔴 Critical  
**Value:** Test robot responses to external input

**Steps:**
1. Add database field to ChatMessage model (30 min)
   ```python
   class ChatMessage:
       # Existing fields...
       is_interjection: bool = False
       interjection_target: Optional[str] = None  # 'robot_a', 'robot_b', or 'both'
   ```

2. Add interjection UI to pause menu (1 hour)
   ```python
   with ui.dialog() as interjection_dialog:
       ui.label('Send Message to Robot(s)')
       message_input = ui.textarea('Your message')
       target = ui.select(['Robot A only', 'Robot B only', 'Both robots'], 
                          label='Send to:')
       ui.button('Send', on_click=lambda: send_interjection(
           message_input.value, 
           target.value
       ))
   ```

3. Implement send_interjection() logic (1 hour)
   ```python
   async def send_interjection(content: str, target: str):
       # Create ChatMessage with is_interjection=True
       # Set appropriate robot_id or both
       # Don't increment turn counter
       # Resume experiment execution
   ```

4. Update conversation display (30 min)
   - Show interjections with distinct styling (yellow border?)
   - Show badge: "👤 Researcher to Robot A"
   - Include in conversation history for LLM context

**Success Criteria:**
- ✅ Can send message to one or both robots
- ✅ Message appears in conversation with distinct styling
- ✅ Robot(s) respond to interjection
- ✅ Turn counter not incremented
- ✅ Experiment continues normally after interjection

---

### Task 2.5.3: Message Impersonation / Ghost Write (2 hours)
**Priority:** 🔴 Critical  
**Value:** Counterfactual testing, A/B testing, intervention studies

**Steps:**
1. Add database field to ChatMessage model (15 min)
   ```python
   class ChatMessage:
       # Existing fields...
       is_researcher_written: bool = False
       visible_to_other_robot: bool = True
   ```

2. Add impersonation UI to pause menu (45 min)
   ```python
   with ui.dialog() as impersonate_dialog:
       ui.label('Send Message AS Robot')
       robot_select = ui.select(['Robot A', 'Robot B'], label='Impersonate:')
       message_input = ui.textarea('Message content')
       visibility = ui.checkbox('Visible to other robot?', value=True)
       ui.button('Send', on_click=lambda: send_impersonated_message(
           robot_select.value,
           message_input.value,
           visibility.value
       ))
   ```

3. Implement send_impersonated_message() logic (45 min)
   ```python
   async def send_impersonated_message(robot: str, content: str, visible: bool):
       # Create ChatMessage with robot_id set
       # Mark is_researcher_written=True
       # Set visible_to_other_robot flag
       # Include in context for recipient robot only if visible=True
       # Resume experiment
   ```

4. Update conversation display and LLM context (15 min)
   - Show subtle indicator: "✍️ (Researcher)" in message footer
   - Filter messages by visible_to_other_robot when building context
   - Export CSV includes all fields for analysis

**Success Criteria:**
- ✅ Can send message as Robot A or Robot B
- ✅ Can control visibility to other robot
- ✅ Message appears in chat with subtle indicator
- ✅ Other robot's context respects visibility setting
- ✅ Enables counterfactual research scenarios

---

## 🧪 SPRINT 3: Code Quality (2-3 weeks)

**Goal:** Maintainable, testable codebase  
**Can run in parallel with usage**  
**Estimated Time:** 10-15 days

### Task 3.1: Type Hints (5 days)
**Priority:** 🟡 High  
**Value:** Better IDE support, fewer bugs

**Steps:**
1. Add type hints to `src/ai/*.py`
2. Add type hints to `src/database/*.py`
3. Add type hints to `src/ui/*.py`
4. Configure `mypy` in `pyproject.toml`
5. Run `mypy src/` and fix errors

**Success Criteria:**
- ✅ 80%+ functions have type hints
- ✅ `mypy src/` passes with no errors

---

### Task 3.2: Test Coverage (5 days)
**Priority:** 🟡 High  
**Value:** Confidence in changes

**Steps:**
1. Write tests for BatchExecutor
2. Write tests for queue system
3. Write tests for permissions
4. Write tests for soft delete
5. Write integration tests

**Target:** 60% coverage (from current 21%)

**Success Criteria:**
- ✅ `pytest --cov=src` shows 60%+
- ✅ All critical paths tested

---

### Task 3.3: JSON Batch Support (3 days)
**Priority:** ⚪ Low  
**Value:** More powerful than CSV

**Steps:**
1. Design JSON schema
   ```json
   {
     "batch_name": "AI Ethics Study",
     "experiments": [
       {
         "prompt": "...",
         "robot_a": "Socratic Bot",
         "robot_b": "Devil's Advocate",
         "max_turns": 20
       }
     ]
   }
   ```
2. Create JSON parser
3. Add JSON upload to batch creation page
4. Write tests

**Success Criteria:**
- ✅ Can upload JSON file
- ✅ Supports per-experiment robot selection
- ✅ More flexible than CSV

---

### Task 3.4: In-Batch Robot Creation (3 days)
**Priority:** ⚪ Low  
**Value:** Faster workflow

**Steps:**
1. Add "Create New Robot" button to batch creation
2. Quick robot profile form (name, provider, model, prompt)
3. Save robot on batch creation
4. Add to robot list for future use

**Success Criteria:**
- ✅ Can create robot during batch setup
- ✅ Robot saved and reusable
- ✅ Faster than pre-creating robots

---

### Task 3.5: Per-User API Keys (3 days)
**Priority:** 🟡 High  
**Value:** No shared quota limits

**Steps:**
1. Add encrypted API key fields to User model
2. Create API key management page (`/settings/api-keys`)
3. Modify LLM service to use user's keys
4. Add key validation

**Success Criteria:**
- ✅ Users can add own OpenAI/Gemini keys
- ✅ Keys encrypted at rest
- ✅ Experiments use user's keys

---

## 📊 SPRINT 4: Analytics (2 weeks) - OPTIONAL

**Goal:** Insights into conversation patterns  
**Prerequisites:** Real usage data  
**Estimated Time:** 10 days

### Task 4.1: Sentiment Analysis (5 days)
**Steps:**
1. Integrate sentiment library (TextBlob or VADER)
2. Analyze messages during save
3. Store sentiment scores in DB
4. Create sentiment visualization

---

### Task 4.2: Analytics Dashboard (5 days)
**Steps:**
1. Create `/analytics` page
2. Show metrics: total experiments, cost, tokens
3. Charts: cost over time, tokens per model
4. Per-experiment analytics view

---

## 📋 SPRINT 4.5: Robot Survey System (1 week) ⭐ RESEARCH-CRITICAL

**Goal:** Survey robots mid-experiment with optional history inclusion  
**Prerequisites:** Sprint 1 complete  
**Estimated Time:** 1 week (6 days)  
**Priority:** 🔴 CRITICAL (core research data collection)

### Day 1: Database Schema & Models (1 day)
**Priority:** 🔴 Critical

**Steps:**
1. Create RobotSurvey model (2 hours)
   ```python
   class RobotSurvey(Model):
       id = fields.IntField(pk=True)
       experiment = fields.ForeignKeyField('models.Experiment')
       created_at = fields.DatetimeField(auto_now_add=True)
       triggered_at_turn = fields.IntField()  # Turn number when survey appeared
       include_history = fields.BooleanField(default=True)  # A/B testing!
       
       # Survey content
       survey_prompt = fields.TextField()  # "On a scale of 1-5, how confident are you?"
       question_type = fields.CharField(max_length=50)  # 'likert', 'open_ended', 'multiple_choice'
       options = fields.JSONField(null=True)  # For multiple choice: ['Option A', 'Option B']
   ```

2. Create SurveyResponse model (1 hour)
   ```python
   class SurveyResponse(Model):
       id = fields.IntField(pk=True)
       survey = fields.ForeignKeyField('models.RobotSurvey')
       robot_profile = fields.ForeignKeyField('models.RobotProfile')
       response_content = fields.TextField()
       raw_llm_output = fields.TextField()  # Full LLM response for debugging
       responded_at = fields.DatetimeField(auto_now_add=True)
       processing_time_ms = fields.IntField()  # How long did LLM take?
   ```

3. Run migrations (30 min)
4. Write model tests (4 hours, rest of day)

**Success Criteria:**
- ✅ Can create RobotSurvey linked to experiment
- ✅ Can store responses from both robots
- ✅ A/B testing: include_history flag works

---

### Day 2: Survey Creation UI (1 day)
**Priority:** 🔴 Critical

**Steps:**
1. Add "Survey Robot" button to pause menu (1 hour)
2. Create survey builder dialog (3 hours)
   ```python
   with ui.dialog() as survey_dialog:
       ui.label('Survey Robots')
       
       survey_type = ui.select(['Likert Scale', 'Open-Ended', 'Multiple Choice'],
                               label='Question Type')
       
       question_input = ui.textarea('Survey Question',
           placeholder='On a scale of 1-5, how confident are you?')
       
       # Dynamic options based on type
       @ui.refreshable
       def render_options():
           if survey_type.value == 'Multiple Choice':
               ui.label('Options (one per line)')
               options_input = ui.textarea()
       
       include_history = ui.checkbox('Include conversation history?', value=True)
       ui.label('⚠️ Unchecking = A/B test (robot forgets conversation)')
       
       target_robots = ui.select(['Robot A only', 'Robot B only', 'Both robots'],
                                 value='Both robots')
       
       ui.button('Send Survey', on_click=lambda: send_survey(...))
   ```

3. Add survey templates dropdown (2 hours)
   - "Confidence check (1-5)"
   - "Emotional state assessment"
   - "Next action prediction"
   - "Custom..."

4. Test UI flows (2 hours)

**Success Criteria:**
- ✅ Can create survey from pause menu
- ✅ Templates speed up common surveys
- ✅ Clear A/B testing option (history on/off)
- ✅ Can target one or both robots

---

### Day 3: Survey Execution Logic (1 day)
**Priority:** 🔴 Critical

**Steps:**
1. Implement send_survey() function (3 hours)
   ```python
   async def send_survey(experiment_id: int, survey_data: dict):
       # Create RobotSurvey record
       survey = await RobotSurvey.create(
           experiment_id=experiment_id,
           triggered_at_turn=current_turn,
           survey_prompt=survey_data['question'],
           include_history=survey_data['include_history'],
           ...
       )
       
       # For each target robot:
       for robot in target_robots:
           # Build context (with or without history!)
           if survey.include_history:
               context = await build_conversation_history(experiment_id, robot.id)
           else:
               context = []  # Fresh slate!
           
           # Add survey question
           context.append({
               'role': 'user',
               'content': survey.survey_prompt
           })
           
           # Call LLM
           start_time = time.time()
           response = await llm_service.send_message(context, robot.model_config)
           processing_time = (time.time() - start_time) * 1000
           
           # Save response
           await SurveyResponse.create(
               survey=survey,
               robot_profile=robot,
               response_content=response,
               processing_time_ms=processing_time
           )
   ```

2. Update experiment execution to pause for surveys (2 hours)
3. Add survey results notification (1 hour)
4. Test survey execution (2 hours)

**Success Criteria:**
- ✅ Survey pauses experiment
- ✅ LLM receives survey question (with/without history)
- ✅ Responses saved to database
- ✅ Experiment resumes after survey

---

### Day 4: Survey History & Results UI (1 day)
**Priority:** 🔴 Critical

**Steps:**
1. Add "Survey History" tab to experiment page (2 hours)
   ```python
   with ui.tab_panel(surveys_tab):
       surveys = await RobotSurvey.filter(experiment_id=exp.id).prefetch_related('responses')
       
       for survey in surveys:
           with ui.card():
               ui.label(f'Turn {survey.triggered_at_turn}')
               ui.label(f'Question: {survey.survey_prompt}')
               ui.label(f'History: {"✓ Included" if survey.include_history else "✗ Forgotten"}')
               
               # Responses
               for response in survey.responses:
                   with ui.expansion(f'{response.robot_profile.name}'):
                       ui.label(response.response_content)
                       ui.label(f'Processing time: {response.processing_time_ms}ms')
   ```

2. Add survey export to CSV (2 hours)
   - Include in experiment export
   - Separate "surveys.csv" file
   - Columns: experiment_id, turn, question, robot, response, include_history, processing_time

3. Add inline survey results in pause menu (2 hours)
   - Show responses immediately after survey completes
   - "View All Surveys" button

4. Test UI (2 hours)

**Success Criteria:**
- ✅ Can view all surveys for experiment
- ✅ Can export survey data to CSV
- ✅ Can see results immediately after survey

---

### Day 5: Survey Analytics & Comparison (1 day)
**Priority:** 🟡 High

**Steps:**
1. Create survey comparison view (3 hours)
   ```python
   # Compare responses with/without history
   with ui.card():
       ui.label('A/B Test: History Impact')
       
       with_history_surveys = await RobotSurvey.filter(include_history=True)
       without_history_surveys = await RobotSurvey.filter(include_history=False)
       
       # Show side-by-side comparison
       with ui.row():
           with ui.column():
               ui.label('With History')
               for survey in with_history_surveys:
                   render_survey_summary(survey)
           
           with ui.column():
               ui.label('Without History (Fresh)')
               for survey in without_history_surveys:
                   render_survey_summary(survey)
   ```

2. Add Likert scale visualization (2 hours)
   - Bar chart for 1-5 responses
   - Average score display
   - Compare Robot A vs Robot B

3. Add keyword extraction for open-ended (2 hours)
   - Simple word frequency
   - Highlight common themes

4. Test analytics (1 hour)

**Success Criteria:**
- ✅ Can compare surveys with/without history
- ✅ Likert scale responses visualized
- ✅ Open-ended responses summarized

---

### Day 6: Batch Survey Support (1 day)
**Priority:** 🟡 High

**Steps:**
1. Add "Survey All Experiments" to batch progress page (3 hours)
   ```python
   async def batch_survey(batch_id: int, survey_data: dict):
       experiments = await Experiment.filter(batch_id=batch_id)
       
       for exp in experiments:
           # Pause experiment if running
           # Send survey
           # Resume experiment
   ```

2. Add batch survey results aggregation (3 hours)
   - Show survey responses across all experiments in batch
   - Average Likert scores
   - Common themes in open-ended

3. Test batch surveys (2 hours)

**Success Criteria:**
- ✅ Can survey all experiments in batch
- ✅ Aggregated results viewable
- ✅ Individual experiment results still accessible

---

## 🤖 SPRINT 5: Multi-Robot (1 week) - OPTIONAL

**Goal:** 3+ robots in one conversation  
**Prerequisites:** User demand  
**Estimated Time:** 5-7 days

### Task 5.1: Database Redesign (3 days)
**Steps:**
1. Create RobotParticipant junction table
2. Update Experiment model
3. Update ChatMessage model
4. Write migration

---

### Task 5.2: Multi-Robot UI (2-3 days)
**Steps:**
1. Multi-robot selection interface
2. Turn order configuration
3. Update chat view for 3+ participants

---

## 🏭 SPRINT 6: Production Hardening (1 week) - OPTIONAL

**Goal:** Enterprise reliability  
**Estimated Time:** 5-7 days

### Task 6.1: Monitoring (2 days)
**Steps:**
1. Add Prometheus metrics
2. Create Grafana dashboards
3. Set up alerts

---

### Task 6.2: Automated Backups (2 days)
**Steps:**
1. Daily PostgreSQL backups
2. S3 upload
3. Backup verification

---

## 📅 Recommended Timeline

```
┌─────────────────────────────────────────────────────────┐
│ WEEK 1: Sprint 1 (UX Polish)                     ✅ NOW │
├─────────────────────────────────────────────────────────┤
│ Day 1: Upgrade experiments chat          (1 hour)       │
│ Day 1: Navbar active users widget         (45 min)      │
│ Day 1: Collapsible batch experiments      (30 min)      │
│ Day 1: Fix name suggestion                (5 min)       │
│ Day 1: Testing & polish                   (30 min)      │
│ 🎉 Phase 1.6 COMPLETE!                                  │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ WEEK 2: Sprint 2.5 (Advanced Controls)    🔴 CRITICAL   │
├─────────────────────────────────────────────────────────┤
│ Day 1: Dynamic max_turns update           (2 hours)     │
│ Day 2: Researcher interjection system     (3 hours)     │
│ Day 3: Message impersonation              (2 hours)     │
│ Day 4-7: Testing with real experiments                  │
│ 🔬 Research methodology features complete!              │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ WEEK 3-4: Sprint 4.5 (Robot Surveys)      🔴 CRITICAL   │
├─────────────────────────────────────────────────────────┤
│ Day 1: Database schema & models           (1 day)       │
│ Day 2: Survey creation UI                 (1 day)       │
│ Day 3: Survey execution logic             (1 day)       │
│ Day 4: Survey history & results UI        (1 day)       │
│ Day 5: Survey analytics & comparison      (1 day)       │
│ Day 6: Batch survey support               (1 day)       │
│ Week 2: Testing & A/B experiments                       │
│ 📊 Core research data collection complete!              │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ WEEK 5-6: Sprint 2 (Advanced Features)    🚀 OPTIONAL   │
├─────────────────────────────────────────────────────────┤
│ Day 1-3: Overnight scheduling                            │
│ Day 4-5: Adaptive concurrency                            │
│ Day 6-7: Cost tracking                                   │
│ Day 8: Load testing                                      │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ WEEK 7-9: Sprint 3 (Code Quality)         🧪 ASYNC      │
├─────────────────────────────────────────────────────────┤
│ Week 1: Type hints + Tests                              │
│ Week 2: JSON support + Per-user API keys                │
│ Week 3: Refactoring + Documentation                      │
└─────────────────────────────────────────────────────────┘

┌─────────────────────────────────────────────────────────┐
│ WEEK 10+: Sprint 4/5/6 (Optional)         📈 LATER      │
├─────────────────────────────────────────────────────────┤
│ Based on user needs:                                     │
│ - Analytics dashboard (if needed)                        │
│ - Multi-robot support (if needed)                        │
│ - Production monitoring (if scaling)                     │
└─────────────────────────────────────────────────────────┘
```

**KEY INSIGHT:** Research-critical features (Sprint 2.5 + 4.5) are now prioritized BEFORE production infrastructure (Sprint 2). This gets you to a research-ready platform in ~3 weeks instead of 3+ months.

---

## 🎯 Success Metrics

**Phase 1.6 Complete When:**
- ✅ All pages use ViewModels (no flicker)
- ✅ Batch automation fully functional
- ✅ Multi-user permissions working
- ✅ Navbar shows active users
- ✅ Batch experiments are collapsible
- ✅ Name suggestion shows "Justin Case"
- ✅ Tests passing (20+ tests)
- ✅ Documentation updated

**Research-Ready Platform Complete When:**
- ✅ Sprint 1 complete (Phase 1.6)
- ✅ Sprint 2.5 complete (Advanced controls)
- ✅ Sprint 4.5 complete (Robot surveys)
- ✅ A/B testing validated (survey with/without history)
- ✅ Interjection system tested with real experiments
- ✅ Impersonation system tested for counterfactuals

**Ready for Production When:**
- ✅ Overnight scheduling works
- ✅ Adaptive concurrency implemented
- ✅ Cost tracking functional
- ✅ Load tested with 100+ experiments
- ✅ Type hints on critical paths
- ✅ 60%+ test coverage
- ✅ User guide written

---

## 🚦 Decision Points

**After Sprint 1 (Week 1):**
- ✅ Phase 1.6 complete - system is usable!
- ➡️ Proceed immediately to Sprint 2.5 (research-critical)
- ❌ Skip "wait and see" - you know what research needs

**After Sprint 2.5 (Week 2):**
- ✅ Advanced controls complete
- ✅ Test interjection/impersonation with small experiments
- ➡️ Proceed to Sprint 4.5 (robot surveys)

**After Sprint 4.5 (Week 3-4):**
- ✅ Research-ready platform complete! 🎉
- ✅ Run pilot studies with surveys and interventions
- ❓ Now decide: Production features (Sprint 2) or Code quality (Sprint 3)?
- ❓ Is overnight scheduling needed?
- ❓ Are API quotas a problem?

**After Sprint 2 (Week 5-6) - OPTIONAL:**
- ❓ Do we need analytics dashboard?
- ❓ Is multi-robot (3+) a requirement?
- ❓ Should we focus on monitoring?

---

## ✅ Quick Start: What to Do RIGHT NOW

1. **Read `docs/PROJECT_STATUS.md`** (comprehensive overview)
2. **Read `docs/VIEWMODELS_QUICKSTART.md`** (pattern reference)
3. **Review new research features:** Sprint 2.5 and Sprint 4.5
4. **Decide:** Start with Sprint 1 (2 hours) to complete Phase 1.6
5. **Then:** Proceed to Sprint 2.5 (7 hours) for research controls
6. **Finally:** Implement Sprint 4.5 (1 week) for robot surveys

**My strong recommendation:**
1. Complete Sprint 1 (2 hours) - Finish Phase 1.6 UX ✅
2. Complete Sprint 2.5 (7 hours) - Add research controls 🔬
3. Complete Sprint 4.5 (1 week) - Add robot surveys 📊
4. **Then you're research-ready in ~3 weeks!**

Say "implement Sprint 1" to start!
