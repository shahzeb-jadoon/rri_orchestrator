# Testing Checklist for RRI Orchestrator

## Pre-Testing Setup

### 1. API Key Configuration

**Status**: ⚠️ **REQUIRED BEFORE TESTING**

Edit `.env` file and add at least one API key:

```bash
# For Google Gemini (recommended for initial testing - has free tier)
GOOGLE_API_KEY="your-actual-api-key-here"

# For OpenAI (requires payment setup)
OPENAI_API_KEY="sk-your-actual-api-key-here"

# Set a password for lab access
LAB_PASSWORD="RRI_Lab_2025_Testing"
```

**How to get API keys:**

- **Google Gemini**: https://makersuite.google.com/app/apikey
- **OpenAI**: https://platform.openai.com/api-keys

### 2. Environment Verification

Run these commands to verify setup:

```bash
# Verify conda environment is active
conda env list
# Should show '*' next to rri_env

# Verify packages installed
pip list | grep -E "streamlit|openai|google-generativeai|python-dotenv"

# Verify database test passed
python test_database.py
```

---

## Testing Procedure

### Test 1: Database Functionality

**Command**: `python test_database.py`

**Expected Output**:
```
Testing database setup...
✓ Database tables created
✓ Created experiment with ID: 1
✓ Logged 3 test messages
✓ Total experiments in database: 1
✓ Total messages for experiment 1: 3

✅ All database tests passed!
```

**Status**: ✅ PASSED

---

### Test 2: Launch Application

**Command**: `streamlit run app.py`

**Expected Behavior**:
- Terminal shows Streamlit server starting
- Browser automatically opens to http://localhost:8501
- Password login screen appears
- No errors in terminal

**Verification Steps**:
1. Check terminal for error messages
2. Verify browser opens automatically
3. Confirm password input field is visible
4. Test password authentication with password from `.env`

---

### Test 3: Authentication

**After launching app, test login:**

**Test 3a: Correct Password**
- Enter password from `.env` file
- Click "Login" button
- **Expected**: Access granted, main interface appears

**Test 3b: Incorrect Password**
- Enter wrong password
- Click "Login" button
- **Expected**: Error message "Incorrect password" appears

---

### Test 4: Experiment Configuration

**In the sidebar:**

1. Verify "Select Model A" dropdown shows available models
2. Verify "Select Model B" dropdown shows available models
3. Modify system prompts if desired
4. Click "Start New Experiment" button

**Expected Results**:
- Success message appears with experiment ID
- Chat interface becomes active in main area
- Experiment logged to database

---

### Test 5: Conversation Flow (Single LLM)

**Initial test with one API key configured:**

**If using Google Gemini:**
- Set both Model A and Model B to "Google Gemini"

**If using OpenAI:**
- Set both Model A and Model B to "OpenAI (GPT-4)"

**Test Steps**:
1. Enter test message: "Hello, please introduce yourself"
2. Click send or press Enter

**Expected Results**:
- Message appears in chat with "researcher" role
- Model A responds (with model name in chat bubble)
- Model B responds (with model name in chat bubble)
- All messages visible in chat history
- No errors in terminal

---

### Test 6: Conversation Flow (Multiple LLMs)

**Requires both API keys configured:**

**Test Steps**:
1. Set Model A to "Google Gemini"
2. Set Model B to "OpenAI (GPT-4)"
3. Start new experiment
4. Send message: "Have a conversation about AI safety"

**Expected Results**:
- Researcher message appears
- Gemini generates response
- OpenAI receives Gemini's response and generates reply
- Both responses visible in chat
- Clear attribution to each model

---

### Test 7: Database Persistence

**Command** (in new terminal, after running experiments):
```bash
sqlite3 rri_lab.db

# In SQLite prompt:
SELECT * FROM experiments;
SELECT sender_role, content FROM messages LIMIT 10;
.quit
```

**Expected Results**:
- Experiments table shows all created experiments
- Messages table contains all conversation history
- Timestamps are in ISO 8601 format
- Data is properly linked via experiment_id

---

### Test 8: Multiple Experiments

**Test Steps**:
1. Complete one full conversation
2. Click "Start New Experiment" in sidebar
3. Send different message to start new conversation
4. Verify new experiment is separate

**Expected Results**:
- New experiment gets different ID
- Old conversation history clears
- New conversation starts fresh
- Both experiments stored separately in database

---

## Troubleshooting Guide

### Issue: "Module not found" error

**Solution**:
```bash
# Verify environment is active
conda activate rri_env

# Reinstall dependencies
pip install -r requirements.txt
```

### Issue: API key not recognized

**Solution**:
- Verify `.env` file is in project root directory
- Check no spaces around `=` sign
- Verify quotes around key value
- Restart Streamlit app after editing `.env`

### Issue: "Connection refused" to LLM API

**Solution**:
- Verify API key is valid (not expired)
- Check internet connection
- For OpenAI: verify payment method is set up
- Check API provider status page

### Issue: Database locked

**Solution**:
```bash
# Close Streamlit app
# Delete database and restart
rm rri_lab.db
streamlit run app.py
```

### Issue: Gemini "history" format error

**Solution**:
- Start new experiment
- Or switch to OpenAI models temporarily

---

## Test Results Log

Date: _____________
Tester: _____________

| Test | Status | Notes |
|------|--------|-------|
| 1. Database functionality | ⬜ Pass ⬜ Fail | |
| 2. Launch application | ⬜ Pass ⬜ Fail | |
| 3. Authentication | ⬜ Pass ⬜ Fail | |
| 4. Experiment config | ⬜ Pass ⬜ Fail | |
| 5. Single LLM conversation | ⬜ Pass ⬜ Fail | |
| 6. Multi-LLM conversation | ⬜ Pass ⬜ Fail | |
| 7. Database persistence | ⬜ Pass ⬜ Fail | |
| 8. Multiple experiments | ⬜ Pass ⬜ Fail | |

---

## Next Steps After Successful Testing

1. **Document any issues encountered**
2. **Commit working state to git**:
   ```bash
   git add .
   git commit -m "Successful Stage 1 testing completed"
   ```

3. **Push to GitHub**:
   ```bash
   git remote add origin https://github.com/YOUR_USERNAME/rri_orchestrator.git
   git push -u origin main
   ```

4. **Begin Stage 2 planning**: Docker containerization and lab deployment
