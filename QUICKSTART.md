# Quick Start Guide 🚀

Get the Resume Screener Agent running in 5 minutes!

## 1. Clone the Repository
```bash
git clone https://github.com/memaitri/ResumeScreenerAgent.git
cd ResumeScreenerAgent
```

## 2. Set Up Your Groq API Key

1. Go to [https://console.groq.com](https://console.groq.com)
2. Sign up for a free account (instant, no credit card required)
3. Create an API key
4. Copy `.env.example` to `.env`:
   ```bash
   cp .env.example .env  # macOS/Linux
   copy .env.example .env  # Windows
   ```
5. Edit `.env` and paste your API key:
   ```env
   GROQ_API_KEY=your_api_key_here
   ```

## 3. Start Backend

In Terminal 1:
```bash
# Install Python dependencies
pip install -r requirements.txt

# Start FastAPI server on port 8001
python -m uvicorn main:app --host 0.0.0.0 --port 8001
```

You should see:
```
INFO:     Uvicorn running on http://0.0.0.0:8001 (Press CTRL+C to quit)
INFO:     Application startup complete.
```

## 4. Start Frontend

In Terminal 2:
```bash
# Install Node dependencies (if not already done)
npm install

# Start React dev server on port 3000
npm start
```

Browser should auto-open to http://localhost:3000

## 5. Test It!

1. **Paste a job description** (example below)
2. **Upload a resume PDF** (drag & drop or click)
3. **Click "Run Screening Pipeline"**
4. **View results** with match scores and analysis

### Example Job Description
```
We're hiring a Senior Python Developer!

Requirements:
- 5+ years Python experience
- FastAPI or Django expertise
- Machine Learning background
- AWS or cloud deployment
- Docker and Kubernetes
- PostgreSQL database design

Responsibilities:
- Build scalable APIs
- Optimize performance
- Mentor junior developers
- Design ML pipelines
```

## 6. View LLM Output

Check what the AI is analyzing:
```bash
# On Windows
Get-Content raw_llm_outputs.log -Tail 50

# On macOS/Linux
tail -50 raw_llm_outputs.log
```

You should see JSON like:
```json
{
  "match_score": 85,
  "strengths": ["Python expert", "AWS experience"],
  "gaps": ["Missing ML background"],
  "recommendation": "Strong Match",
  "reasoning": "..."
}
```

## Common Issues 🔧

### "Connection refused" error
- Make sure backend is running: `python -m uvicorn main:app --host 0.0.0.0 --port 8001`
- Wait 5 seconds for server to start
- Check if port 8001 is in use: `netstat -ano | findstr :8001` (Windows)

### "Could not parse detailed analysis"
- Check your GROQ_API_KEY is correct
- Check `raw_llm_outputs.log` for actual LLM response
- Restart backend after changing `.env`

### Port 3000 or 8001 already in use
- Kill existing process or change port number

### Embedding model download fails
- Check internet connection
- Model downloads to `~/.cache/huggingface/` (~400MB)
- First run will be slower due to model download

## Architecture Overview 📊

```
Frontend (React 3000)
    ↓ (axios POST /screen)
Backend (FastAPI 8001)
    ↓
LangGraph Pipeline:
    1. Parse: Extract PDF text
    2. Score: Compute similarity with embeddings
    3. Analyze: LLM analyzes fit (Groq llama-3.1-8b-instant)
    4. Rank: Sort by match_score
    ↓
Return JSON results
```

## Next Steps 🎯

- Modify prompts in `main.py` to customize analysis
- Add more resume files to test with
- Explore the LLM output to understand scoring
- Deploy to production (Heroku, AWS, etc.)

## Deployment 🌐

See README.md for advanced setup, Docker, and production deployment.

## Support 💬

Issues? Check the GitHub Issues: https://github.com/memaitri/ResumeScreenerAgent/issues

Happy screening! 🎉
