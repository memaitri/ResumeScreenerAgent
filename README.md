# Resume Screener Agent 🤖

A multi-agent resume screening system powered by **LangGraph**, **Groq LLM**, and **FastAPI** that automatically analyzes and ranks resumes against job descriptions.


**<img width="1132" height="730" alt="RESUME_TEST" src="https://github.com/user-attachments/assets/2fa506b8-a42e-4cd1-b7fc-2a7691cf7444" />
**

<img width="1138" height="602" alt="RESUME_OUTPUT" src="https://github.com/user-attachments/assets/4af89e6a-54dc-43a5-ab72-68139f6fe8a4" />


## Features ✨

- **Intelligent Resume Parsing**: Extracts and chunks resume text for detailed analysis
- **Vector Embeddings**: Uses HuggingFace embeddings (all-MiniLM-L6-v2) for semantic similarity scoring
- **LLM-Powered Analysis**: Groq's llama-3.1-8b-instant model with JSON output for structured analysis
- **Multi-Agent Pipeline**: LangGraph state machine with 4 specialized nodes
- **Real-time Feedback**: React frontend with visual scoring rings and expandable result cards
- **Logging Infrastructure**: Raw LLM output logging for debugging and validation

## Architecture 🏗️

### Backend (FastAPI + Python)
```
Resume Input
    ↓
Parse Node → Extract text, chunk into 500-char segments
    ↓
Score Node → Compute cosine similarity (HuggingFace embeddings)
    ↓
Analyze Node → LLM analysis (Groq with JSON mode)
    ↓
Rank Node → Sort by match_score, format final output
    ↓
JSON Results
```

### Frontend (React)
- Job description input
- Drag-and-drop PDF resume upload
- Real-time screening results with:
  - Match score (0-100) with color-coded ring
  - Recommendation (Strong Match, Good Match, Partial Match, Not Recommended)
  - Strengths and gaps analysis
  - Detailed reasoning

## Tech Stack 🛠️

**Backend:**
- FastAPI (HTTP API server)
- LangGraph (multi-agent orchestration)
- LangChain (LLM framework)
- Groq (LLM provider)
- HuggingFace Transformers (embeddings)
- PyPDF2 (PDF parsing)
- FAISS (vector similarity)

**Frontend:**
- React 18
- Axios (HTTP client)
- CSS Grid/Flexbox

## Setup & Installation 📦

### Prerequisites
- Python 3.11+
- Node.js 16+
- Groq API key (free tier available)

### Backend Setup

1. **Install Python dependencies:**
```bash
pip install -r requirements.txt
```

2. **Create `.env` file:**
```env
GROQ_API_KEY=your_groq_api_key_here
```

3. **Start FastAPI server:**
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8001
```

Backend will be available at `http://localhost:8001`

### Frontend Setup

1. **Install Node dependencies:**
```bash
npm install
```

2. **Start React development server:**
```bash
npm start
```

Frontend will open at `http://localhost:3000` (or `3001` if 3000 is busy)

## Usage 🚀

1. Open http://localhost:3000 in your browser
2. Paste a job description in the textarea
3. Upload one or more resume PDFs
4. Click "Run Screening Pipeline"
5. View detailed analysis results with match scores and recommendations

## API Endpoint

**POST** `/screen`

**Request:**
```json
{
  "jd": "Job description text...",
  "resumes": [binary PDF files]
}
```

**Response:**
```json
{
  "results": [
    {
      "rank": 1,
      "name": "resume.pdf",
      "match_score": 85,
      "similarity_score": 82.5,
      "recommendation": "Strong Match",
      "strengths": ["Python experience", "FastAPI expertise"],
      "gaps": ["Missing cloud deployment"],
      "reasoning": "Candidate has strong Python background..."
    }
  ]
}
```

## Configuration 🔧

### LLM Settings (main.py)
- **Model**: llama-3.1-8b-instant
- **Temperature**: 0.0 (deterministic)
- **JSON Mode**: Enabled for structured output
- **Prompt**: Explicitly requires JSON format with no markdown

### Embeddings
- **Model**: all-MiniLM-L6-v2
- **Dimensions**: 384
- **Similarity**: Cosine distance

### Text Chunking
- **Chunk Size**: 500 characters
- **Overlap**: 0

## Project Structure 📁

```
Resume Screener Agent/
├── main.py                 # FastAPI backend + LangGraph pipeline
├── package.json            # React app configuration
├── requirements.txt        # Python dependencies
├── .gitignore             # Git ignore rules
├── public/
│   └── index.html         # React HTML entry point
├── src/
│   ├── App.js             # Main React component
│   ├── App.css            # Styling
│   └── index.js           # React entry point
└── raw_llm_outputs.log    # LLM output logging (generated)
```

## Debugging 🐛

### View Raw LLM Output
Check `raw_llm_outputs.log` to see the actual LLM responses:
```bash
cat raw_llm_outputs.log
```

### Backend Logs
```bash
python -m uvicorn main:app --host 0.0.0.0 --port 8001 --log-level debug
```

### Frontend Logs
Open browser DevTools (F12) and check Console tab

## Key Implementation Details 🔑

### JSON Mode Enforcement
The backend uses 3-layer enforcement to ensure LLM outputs valid JSON:
1. **Model Config**: `model_kwargs={"response_format": {"type": "json_object"}}`
2. **Temperature**: Set to 0.0 for deterministic output
3. **Prompt Engineering**: Explicit "ONLY valid JSON" requirement with example

### Error Handling
- Fallback JSON extraction via regex if LLM output is malformed
- Graceful degradation with default values
- All errors logged for debugging

### Performance Optimizations
- Text chunking reduces embedding computation
- Vector similarity precomputed before LLM analysis
- Async-ready FastAPI for concurrent requests

## Known Limitations ⚠️

- Requires PDF files (TXT supported with minor code changes)
- LLM analysis limited to context window
- No resume deduplication
- Single-threaded screening (FastAPI can handle async)

## Future Enhancements 🌟

- [ ] Candidate ranking comparison view
- [ ] Resume parsing improvement (better table extraction)
- [ ] Bulk resume upload with batch processing
- [ ] Dashboard with analytics
- [ ] Support for multiple file formats
- [ ] Cache results for faster re-screening
- [ ] Export results to CSV/PDF

## Troubleshooting 🔧

### "Could not parse detailed analysis" error
- Check `raw_llm_outputs.log` for LLM response format
- Verify GROQ_API_KEY is correct
- Ensure Groq API is working (test via `groq-cli`)

### Port 8000/8001 already in use
```bash
lsof -i :8001  # macOS/Linux
netstat -ano | findstr :8001  # Windows
```

### Embedding model download fails
- Check internet connection
- Model will download to `~/.cache/huggingface/` on first run

## License 📄

MIT License - feel free to use this for commercial projects

## Author 👤

**Maitri Movaliya**
- GitHub: [@memaitri](https://github.com/memaitri)
- Project: Resume Screener Agent

---

**Made with ❤️ using LangGraph, Groq, and React**
