# RRI Conversation Orchestrator

A web-based platform for studying robot-robot interaction (RRI) through conversations between Large Language Models (LLMs).

## Overview

This tool enables researchers to:
- Configure multi-agent conversations between different LLMs
- Define custom system prompts for each participant
- Monitor conversations in real-time
- Log all interactions to a database for analysis
- Export conversation data for research

## Features

- **Multi-Model Support**: Currently supports Google Gemini and OpenAI GPT models
- **Modular Architecture**: Easy to add new LLM providers
- **Real-time Monitoring**: Watch conversations unfold in a chat interface
- **Data Persistence**: All conversations logged to SQLite database
- **Password Protection**: Simple authentication to protect API keys

## Quick Start

### Prerequisites

- Python 3.10 or higher
- API keys for the LLMs you want to use

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
streamlit run app.py
```

The app will open in your browser at `http://localhost:8501`

## Project Structure

```
rri_orchestrator/
├── app.py                  # Main Streamlit application
├── database.py             # Database operations
├── llm_clients/            # LLM client implementations
│   ├── __init__.py
│   ├── base.py            # Abstract base class
│   ├── gemini.py          # Google Gemini client
│   └── openai.py          # OpenAI client
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variable template
└── README.md              # This file
```

## Usage

1. **Start New Experiment**: Use the sidebar to select models and define system prompts
2. **Begin Conversation**: Type a message to start the interaction between models
3. **Monitor**: Watch as models respond to each other in turn
4. **Data**: All messages are automatically saved to `rri_lab.db`

## Adding New LLM Providers

To add support for a new LLM:

1. Create a new client file in `llm_clients/` (e.g., `claude.py`)
2. Inherit from `BaseLLMClient` and implement `generate_response()`
3. Add the client to the factory function in `app.py`
4. Add the API key to `.env`

## Development Roadmap

### Stage 1 (Current)
- ✅ Basic conversation orchestration
- ✅ Support for Google Gemini and OpenAI
- ✅ SQLite logging
- ✅ Simple authentication

### Stage 2 (Planned)
- [ ] Docker containerization
- [ ] Deployment on lab server
- [ ] Export to CSV functionality
- [ ] Conversation analysis tools

### Stage 3 (Future)
- [ ] Support for self-hosted models (Ollama)
- [ ] Multimodal inputs (images/video)
- [ ] Advanced conversation control
- [ ] Multiple simultaneous participants

## License

This project is for academic research use.

## Contributors

- RIT RRI Research Team

## Acknowledgments

Built following architectural guidance from the research team and incorporating best practices for modular LLM integration.
