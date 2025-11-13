# RRI Conversation Orchestrator

A web-based platform for studying robot-robot interaction (RRI) through conversations between Large Language Models (LLMs).

## Overview

This tool enables researchers to:
- Configure multi-agent conversations between different LLMs
- Run conversations automatically or manually control each turn
- View and filter past experiments with a comprehensive history viewer
- Define custom system prompts for each participant
- Monitor conversations in real-time
- Log all interactions to a database for analysis
- Export conversation data to CSV for external analysis

## Features

### Core Functionality
- **Multi-Model Support**: Currently supports Google Gemini and OpenAI GPT models
- **Conversation Modes**:
  - **Manual Mode**: Step through conversations turn-by-turn with full control
  - **Automatic Mode**: Run entire conversations hands-free until completion
- **Turn Limits**: Set maximum turns to control API costs
- **Real-time Monitoring**: Watch conversations unfold in a chat interface
- **Stop Controls**: Pause automatic conversations at any time

### Data Management
- **History Viewer**: Browse all past experiments with detailed metadata
- **Advanced Filtering**: 
  - Filter by model combinations
  - Search by keywords in conversation content
- **CSV Export**: 
  - Export individual experiments
  - Export all experiments
  - Export filtered results
  - Timestamped filenames for easy organization
- **Data Persistence**: All conversations logged to SQLite database

### Technical
- **Modular Architecture**: Easy to add new LLM providers
- **Password Protection**: Simple authentication to protect API keys
- **Database Logging**: Complete conversation history with timestamps

## Quick Start

### Prerequisites

- Python 3.10 or higher
- API keys for the LLMs you want to use
- Conda (recommended) or pip

### Installation

1. Clone this repository:
```bash
git clone <your-repo-url>
cd rri_orchestrator
```

2. Create a conda environment:
```bash
conda create -n rri_env python=3.10
conda activate rri_env
```

3. Install dependencies:
```bash
pip install -r requirements.txt
```

4. Set up your environment variables:
```bash
cp .env.example .env
```

5. Edit `.env` and add your API keys:
   - Get Google API key from: https://makersuite.google.com/app/apikey
   - Get OpenAI API key from: https://platform.openai.com/api-keys
   - Set a secure LAB_PASSWORD

### Running the Application

```bash
streamlit run app_new.py
```

The app will open in your browser at `http://localhost:8501`

### Testing

Run the automated test suite to verify installation:
```bash
python tests/test_fixes.py
```

Expected output: `✅ ALL TESTS PASSED!`

## Usage Guide

### Starting a New Conversation

**Method 1: Automatic Mode (Recommended for long conversations)**
1. Select "💬 New Conversation" from sidebar
2. Choose "Automatic" conversation mode
3. Select Model A and Model B
4. Set max turns (e.g., 10)
5. Enter system prompts for both models
6. Click "🚀 Start New Experiment"
7. Type your initial prompt
8. Watch the conversation unfold automatically!
9. Use "⏹️ Stop" button to pause if needed

**Method 2: Manual Mode (For step-by-step control)**
1. Select "Manual" conversation mode
2. Configure models and prompts as above
3. After each exchange, click "Continue Conversation"
4. Manually control the pace of the conversation

### Viewing Past Conversations

1. Click "📚 View History" in sidebar navigation
2. Browse all your experiments
3. Use filters to find specific conversations:
   - **Model Pair Filter**: Select specific model combinations
   - **Keyword Search**: Find conversations containing specific terms
4. Click on any experiment to expand and view full details
5. Read complete conversation transcripts with timestamps

### Exporting Data

**Export All Data:**
1. Go to "📚 View History"
2. Click "📊 Export All Experiments to CSV"
3. Download button will appear
4. CSV file includes all experiments with full metadata

**Export Filtered Data:**
1. Apply filters (model pair, keywords)
2. Click "📊 Export Filtered Results to CSV"
3. Download only the experiments that match your filters

**Export Single Experiment:**
1. Expand an experiment in the history view
2. Click "📥 Export Experiment #X"
3. Download CSV for just that conversation

**CSV Format:**
- `experiment_id`: Unique identifier
- `experiment_start_time`: When experiment began
- `model_a_name`, `model_b_name`: Models used
- `turn_number`: Which turn (0 for initial, 1, 2, 3...)
- `speaker`: Who sent the message
- `timestamp`: Exact time message was sent
- `message_content`: Full message text
- `model_a_system_prompt`, `model_b_system_prompt`: System prompts used
- `max_turns`: Maximum turns configured

### Running Batch Experiments (CLI)

For systematic research with multiple prompts, use the batch experiment runner:

**Basic Usage:**
```bash
# Create a prompts file (one prompt per line)
cat > my_prompts.txt << 'EOF'
Discuss the ethical implications of AI in healthcare.
What are the trade-offs between privacy and convenience?
Should social media platforms be regulated?
EOF

# Run dry test first
python scripts/run_batch_experiments.py my_prompts.txt \
  --provider-a gemini \
  --provider-b openai \
  --model-a "gemini-2.5-pro" \
  --model-b "gpt-4o" \
  --turns 3 \
  --dry-run

# Run actual experiments
python scripts/run_batch_experiments.py my_prompts.txt \
  --provider-a gemini \
  --provider-b openai \
  --turns 3
```

**Flip Mode (A/B Testing):**
```bash
# Run each prompt twice: A→B then B→A
python scripts/run_batch_experiments.py my_prompts.txt \
  --provider-a gemini \
  --provider-b openai \
  --turns 3 \
  --flip
```

**Available Options:**
- `prompts_file` - Path to prompts file (required, positional)
- `--provider-a`, `--provider-b` - LLM providers (`gemini` or `openai`)
- `--model-a`, `--model-b` - Specific model variants (see config/model_config.py)
- `--turns` or `--max-turns` - Maximum conversation turns (default: 5)
- `--flip` - Run experiments twice with swapped model positions
- `--dry-run` - Test without creating experiments
- `--prefix` - Experiment name prefix (default: "Batch")
- `--quiet` - Suppress progress messages

See `data/example_prompts.txt` for a sample prompt file.
```

**Flip Mode (A/B Testing):**
```bash
# Run each prompt twice: A→B then B→A
python run_batch_experiments.py my_prompts.txt \
  --provider-a gemini \
  --provider-b openai \
  --turns 3 \
  --flip
```

**Available Options:**
- `prompts_file` - Path to prompts file (required, positional)
- `--provider-a`, `--provider-b` - LLM providers (`gemini` or `openai`)
- `--model-a`, `--model-b` - Specific model variants (see model_config.py)
- `--turns` or `--max-turns` - Maximum conversation turns (default: 5)
- `--flip` - Run experiments twice with swapped model positions
- `--dry-run` - Test without creating experiments
- `--prefix` - Experiment name prefix (default: "Batch")
- `--quiet` - Suppress progress messages

See `data/example_prompts.txt` for a sample prompt file.

## Project Structure

```
rri_orchestrator/
├── app.py                     # Original Streamlit app (Stage 1)
├── app_new.py                 # Enhanced Streamlit app (recommended)
├── requirements.txt           # Python dependencies
├── .env.example              # Environment variable template
├── .env                      # Your API keys (gitignored)
├── .gitignore                # Git ignore patterns
├── README.md                 # Complete documentation (this file)
│
├── clients/                   # LLM client implementations
│   ├── __init__.py           # Package exports
│   ├── base.py               # Abstract base class
│   ├── gemini.py             # Google Gemini client
│   └── openai.py             # OpenAI client
│
├── config/                    # Configuration files
│   ├── __init__.py
│   └── model_config.py       # Model definitions (15 variants)
│
├── core/                      # Core business logic
│   ├── __init__.py
│   └── database.py           # SQLite operations with migrations
│
├── scripts/                   # CLI utilities
│   ├── run_batch_experiments.py   # Batch experiment automation
│   └── check_models.py            # Verify available models
│
├── tests/                     # Test files
│   ├── test_database.py      # Database testing utility
│   └── test_fixes.py         # Automated test suite for bug fixes
│
├── data/                      # Example data
│   └── example_prompts.txt   # Sample prompts for batch experiments
│
└── rri_lab.db                # SQLite database (gitignored, your data)
```

## Troubleshooting

### Common Issues

**AttributeError on session state**:
- Ensure you're running `app_new.py` (not the old `app.py`)
- Try restarting the Streamlit server
- Clear browser cache and reload

**Continue feature not working**:
- Run `python tests/test_fixes.py` to verify database schema
- Check that the database has the `target_model` column
- Restart the app

**API Errors**:
- Verify API keys in `.env` are correct
- Check API quota/rate limits
- Errors are logged to terminal with specific error types

**Database Issues**:
- Database automatically migrates on startup
- To reset: delete `rri_lab.db` (WARNING: loses all data)
- Backup database regularly for important experiments

## Adding New LLM Providers

To add support for a new LLM:

1. Create a new client file in `clients/` (e.g., `claude.py`)
2. Inherit from `BaseLLMClient` and implement `generate_response()`
3. Add the model configuration to `config/model_config.py`
4. Update the provider selection in `app_new.py`
5. Export the new client in `clients/__init__.py`
4. Add the API key to `.env`

## Development Roadmap

### Recent Updates ✅
- ✅ Fixed session state initialization (prevents AttributeError crashes)
- ✅ Fixed Continue conversation feature (UI now updates in real-time)
- ✅ Fixed history reconstruction (models maintain full context)
- ✅ Added target tracking for researcher interjections
- ✅ Enhanced error handling in Gemini client
- ✅ Comprehensive automated test suite

### Stage 1 ✅ Complete
- ✅ Basic conversation orchestration
- ✅ Support for Google Gemini and OpenAI
- ✅ SQLite logging
- ✅ Simple authentication
- ✅ Turn limits for cost control

### Stage 2 ✅ Complete
- ✅ Automatic conversation mode
- ✅ Manual conversation mode
- ✅ History viewer with filtering
- ✅ CSV export functionality
- ✅ Keyword search in conversations
- ✅ Researcher interjections and manual overrides
- ✅ Pause and resume controls

### Stage 3 (Future)
- [ ] Add Anthropic Claude support
- [ ] Add Meta Llama support
- [ ] Support for self-hosted models (Ollama)
- [ ] Docker containerization
- [ ] Conversation analysis tools
- [ ] Multimodal inputs (images/video)

## License

This project is for academic research use.

## Contributors

- RIT RRI Research Team

## Acknowledgments

Built following architectural guidance from the research team and incorporating best practices for modular LLM integration.
