# RRI Orchestrator - Setup Instructions

## Project Structure

```
rri_orchestrator/
├── .gitignore              # Configured to ignore .env, databases, and cache
├── .env.example            # Template for API keys
├── .env                    # Environment variables (add API keys here)
├── README.md               # Project documentation
├── requirements.txt        # Python dependencies
├── app.py                  # Main Streamlit application
├── database.py             # SQLite database operations
└── llm_clients/
    ├── __init__.py         # Package marker
    ├── base.py             # Abstract base class for all LLM clients
    ├── gemini.py           # Google Gemini implementation
    └── openai.py           # OpenAI GPT implementation
```

## Git Repository Status
- Initialized with 'main' as default branch
- Initial commit completed with core files
- Ready to push to GitHub

---

## Setup Instructions

### 1. API Key Configuration

Add API keys to the `.env` file.

**Google Gemini (Free tier available)**
1. Navigate to: https://makersuite.google.com/app/apikey
2. Sign in with Google account
3. Create API Key
4. Add to `.env`: `GOOGLE_API_KEY="your-key-here"`

**OpenAI (Requires payment setup)**
1. Navigate to: https://platform.openai.com/api-keys
2. Sign in or create account
3. Add payment method
4. Create new API key
5. Add to `.env`: `OPENAI_API_KEY="sk-your-key-here"`

Note: Start with Google Gemini for testing without payment setup.

### 2. Lab Password Configuration

Edit `.env` and set:
```
LAB_PASSWORD="RRI_Lab_2025_SecureAccess"
```

Replace with a secure password for lab access.

### 3. Environment Setup

**Using Conda**
```bash
conda create -n rri_env python=3.10 -y
conda activate rri_env
pip install -r requirements.txt
```

**Using Python venv**
```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 4. Running the Application

```bash
streamlit run app.py
```

Application will be available at http://localhost:8501

### 5. GitHub Repository Setup

Create a new repository on GitHub, then:

```bash
git remote add origin https://github.com/YOUR_USERNAME/rri_orchestrator.git
git branch -M main
git push -u origin main
```

---

## Testing Requirements

Verify the following before deployment:

- [ ] `.env` file contains at least one valid API key (Gemini or OpenAI)
- [ ] `.env` file has LAB_PASSWORD configured
- [ ] Virtual environment created and activated
- [ ] Dependencies installed (verify with `pip list`)
- [ ] Application starts without errors
- [ ] Password authentication functional
- [ ] Experiment creation functional
- [ ] Message exchange between models functional
- [ ] Chat interface displays messages correctly
- [ ] `rri_lab.db` file created in project root
- [ ] No errors in terminal output

---

## Troubleshooting

### Module Not Found Errors
- Verify virtual environment is activated
- Reinstall dependencies: `pip install -r requirements.txt`

### API Key Errors
- Confirm `.env` file is in project root directory
- Verify key format: `GOOGLE_API_KEY="key-here"` (no spaces around =)
- Check quotes are present around the key value

### Gemini History Errors
- Start a new experiment using "Start New Experiment" button
- Alternative: Use OpenAI models instead

### Database Locked Errors
- Restart the application
- If persistent, delete `rri_lab.db` and restart

---

## Project Status

Stage 1 MVP features implemented:
- Modular LLM client architecture with abstract base class
- Support for Google Gemini and OpenAI GPT models
- SQLite database for conversation logging
- Streamlit web interface for experiment configuration
- Password authentication for lab access
- Version control with Git

## Future Development

Stage 2 planned features:
- CSV export functionality
- Additional conversation control mechanisms
- Docker containerization
- Lab server deployment

Stage 3 planned features:
- Self-hosted model support (Ollama)
- Multimodal input support (images/video)
- Additional LLM provider integrations (Azure, Claude, Anthropic)

---

## Command Reference

```bash
# Environment activation
source venv/bin/activate          # or: conda activate rri_env

# Run application
streamlit run app.py

# Version control
git status
git add .
git commit -m "Description of changes"
git push

# Environment deactivation
deactivate                        # or: conda deactivate
```
