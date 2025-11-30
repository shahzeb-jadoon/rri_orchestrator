# Batch Creation Testing Guide

## Quick Start

### 1. Access the Batch Page
Visit: https://rri.zylot.tech/batch/create

You should now see:
- Navigation bar at the top (with Home, Robots, Experiments, Create Batch links)
- "Create Experiment Batch" header
- Upload CSV File section

### 2. Upload Test CSV
Use the provided sample file: `docs/sample_batch.csv`

**Windows Path:** `C:\path\to\rri_orchestrator\docs\sample_batch.csv`

The file contains 10 AI-related prompts for testing.

### 3. What to Expect

**Step 1 - Upload:**
- Click "Choose CSV File"
- Select `sample_batch.csv`
- File uploads automatically

**Step 2 - Preview:**
After upload, you'll see:
- Summary cards showing:
  - Total Experiments: 10
  - Average Turns: 14
- Preview table with all 10 prompts
- Each row shows: row number, prompt (truncated), description, max turns

**Step 3 - Configure:**
- Enter batch name (e.g., "AI Fundamentals Test")
- Enter description (optional)
- Select Robot A from dropdown (use any existing robot)
- Select Robot B from dropdown (use a different robot)
- Adjust "Max Concurrent Experiments" slider (1-10, default: 5)
- Click "Create Batch"

**After Creation:**
- Success notification appears
- Redirects to `/experiments` page
- You should see 10 new experiments listed

## Verification

### Check Database
```bash
# Check batch was created
docker exec rri_postgres psql -U rri_user -d rri_orchestrator -c \
  "SELECT id, name, total_experiments, status FROM experiment_batches;"

# Check experiments were created
docker exec rri_postgres psql -U rri_user -d rri_orchestrator -c \
  "SELECT id, name, batch_id, batch_index FROM experiments WHERE batch_id IS NOT NULL ORDER BY batch_index;"

# Check queue entries were created
docker exec rri_postgres psql -U rri_user -d rri_orchestrator -c \
  "SELECT id, experiment_id, batch_id, status, priority FROM experiment_queue ORDER BY added_at;"
```

Expected results:
- 1 batch record
- 10 experiment records (with batch_id set)
- 10 queue entries (linked to batch)

## Sample CSV Format

### With Header (Recommended)
```csv
prompt,description,max_turns
What is AI?,Basic question,10
Explain ML,Machine learning intro,15
```

### Simple Format (Prompts Only)
```
What is AI?
Explain ML
How do robots work?
```

## Common Issues

### Issue: "No valid experiments found in CSV"
**Cause:** Empty file or all rows have errors
**Fix:** Ensure CSV has at least one row with a prompt

### Issue: "Please log in to create batches"
**Cause:** User not authenticated or not in database
**Fix:** Visit https://rri.zylot.tech/onboarding first

### Issue: No robot profiles available
**Cause:** No robots created yet
**Fix:** Visit https://rri.zylot.tech/robots and create at least 2 robots

### Issue: Experiments don't appear after batch creation
**Cause:** Database connection issue or experiments page not refreshing
**Fix:** Manually refresh the page or check database directly

## Next Steps

After successful batch creation:
1. View experiments on `/experiments` page
2. Check that all 10 experiments appear with batch name
3. Verify each experiment has correct prompt and settings
4. Wait for Phase 1.6 Day 4-5 (BatchExecutor) to run experiments automatically

## File Locations (Windows)

- Sample CSV: `docs\sample_batch.csv`
- Batch page code: `src\ui\pages\batch.py`
- CSV parser: `src\batch\csv_parser.py`
- Parser tests: `tests\test_csv_parser.py`
