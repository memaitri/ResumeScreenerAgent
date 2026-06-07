import os
import json
import re
from typing import TypedDict, List, Annotated
from fastapi import FastAPI, UploadFile, File, Form, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv
import PyPDF2
import io

from langchain_groq import ChatGroq
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_community.vectorstores import FAISS
from langchain_community.embeddings import HuggingFaceEmbeddings
from langchain_core.messages import HumanMessage, SystemMessage

from langgraph.graph import StateGraph, END

load_dotenv()

BASE_DIR = os.path.dirname(os.path.realpath(__file__))
RAW_LLM_OUTPUT_PATH = os.path.join(BASE_DIR, "raw_llm_outputs.log")
print(f"[MAIN] BASE_DIR={BASE_DIR}")
print(f"[MAIN] RAW_LLM_OUTPUT_PATH={RAW_LLM_OUTPUT_PATH}")

app = FastAPI(title="ResumeIQ API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ─── LLM Setup ───────────────────────────────────────────────
llm = ChatGroq(
    model="llama-3.3-70b-versatile",  # was llama-3.1-8b-instant
    temperature=0.0,
    api_key=os.getenv("GROQ_API_KEY"),
    model_kwargs={"response_format": {"type": "json_object"}}
)

embeddings = HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")

# ─── LangGraph State ─────────────────────────────────────────
class AgentState(TypedDict):
    jd_text: str
    resumes: List[dict]           # [{name, text}]
    parsed_resumes: List[dict]    # [{name, text, chunks}]
    scored_resumes: List[dict]    # + similarity_score
    analyzed_resumes: List[dict]  # + strengths, gaps, reasoning
    final_ranking: List[dict]     # final sorted output

# ─── Helper: Extract PDF text ────────────────────────────────
def extract_pdf_text(file_bytes: bytes) -> str:
    reader = PyPDF2.PdfReader(io.BytesIO(file_bytes))
    text = ""
    for page in reader.pages:
        text += page.extract_text() or ""
    return text.strip()

# ─── Node 1: Parse & Chunk ───────────────────────────────────
def node_parse(state: AgentState) -> AgentState:
    splitter = RecursiveCharacterTextSplitter(chunk_size=500, chunk_overlap=50)
    parsed = []
    for r in state["resumes"]:
        chunks = splitter.split_text(r["text"])
        parsed.append({**r, "chunks": chunks})
    return {**state, "parsed_resumes": parsed}

# ─── Node 2: Embed & Score ───────────────────────────────────
def node_score(state: AgentState) -> AgentState:
    jd = state["jd_text"]
    scored = []

    jd_embedding = embeddings.embed_query(jd)

    for resume in state["parsed_resumes"]:
        if not resume["chunks"]:
            scored.append({**resume, "similarity_score": 0.0})
            continue

        chunk_embeddings = embeddings.embed_documents(resume["chunks"])

        # Average cosine similarity
        import numpy as np
        jd_vec = np.array(jd_embedding)
        scores = []
        for ce in chunk_embeddings:
            cv = np.array(ce)
            cos_sim = float(np.dot(jd_vec, cv) / (np.linalg.norm(jd_vec) * np.linalg.norm(cv) + 1e-9))
            scores.append(cos_sim)

        avg_score = float(np.mean(scores))
        scored.append({**resume, "similarity_score": round(avg_score, 4)})

    return {**state, "scored_resumes": scored}

# ─── Node 3: LLM Analysis ────────────────────────────────────
def node_analyze(state: AgentState) -> AgentState:
    jd = state["jd_text"]
    analyzed = []

    def text_to_json(text: str, default_recommendation: str, fallback_score: int) -> dict:
        cleaned = text.replace("\ufeff", "").replace("\r\n", "\n").strip()
        cleaned = re.sub(r"```(?:json)?\s*|```", "", cleaned, flags=re.IGNORECASE).strip()
        first = cleaned.find("{")
        last = cleaned.rfind("}")
        candidate = cleaned[first:last + 1] if first != -1 and last != -1 and last > first else cleaned

        for attempt in (candidate, cleaned):
            try:
                value = json.loads(attempt)
                if isinstance(value, list) and value:
                    return value[0]
                return value
            except json.JSONDecodeError:
                continue

        def find_int(key, default):
            m = re.search(rf"{key}\s*[:=-]\s*(\d+)", cleaned, flags=re.IGNORECASE)
            return int(m.group(1)) if m else default

        def find_recommendation():
            for label in ["Strong Match", "Good Match", "Partial Match", "Not Recommended"]:
                if re.search(re.escape(label), cleaned, flags=re.IGNORECASE):
                    return label
            return default_recommendation

        def find_list(key):
            m = re.search(rf"{key}\s*[:=-]\s*(\[[^\]]*\]|(?:.*?)(?:\n\n|$))", cleaned, flags=re.IGNORECASE | re.DOTALL)
            if m:
                text_value = m.group(1).strip()
                try:
                    parsed = json.loads(text_value)
                    if isinstance(parsed, list):
                        return [str(item).strip() for item in parsed if str(item).strip()]
                except Exception:
                    lines = [line.strip(' -•*\t') for line in text_value.splitlines() if line.strip()]
                    return [line for line in lines if line]
            return []

        reasoning = ""
        m = re.search(r"reasoning\s*[:=-]\s*([\s\S]+)$", cleaned, flags=re.IGNORECASE)
        if m:
            reasoning = m.group(1).strip().strip('"')

        return {
            "match_score": find_int("match_score", fallback_score),
            "strengths": find_list("strengths") or ["Could not parse detailed analysis"],
            "gaps": find_list("gaps") or ["Could not parse detailed analysis"],
            "recommendation": find_recommendation(),
            "reasoning": reasoning or f"Automated scoring only. Similarity: {fallback_score / 100:.2f}",
        }

    for resume in state["scored_resumes"]:
        resume_text = resume["text"][:2000]  # keep within token limits

        prompt = f"""You are an expert HR analyst and technical recruiter. Your response MUST be ONLY valid JSON with no other text or markdown.

Job Description:
{jd[:1000]}  # was 1500

Candidate Resume:
{resume_text}

Respond ONLY with this exact JSON structure and nothing else:
{{
  "match_score": 75,
  "strengths": ["strength 1", "strength 2"],
  "gaps": ["gap 1"],
  "recommendation": "Strong Match",
  "reasoning": "Brief 1-2 sentence explanation."
}}

Rules:
- match_score: integer 0-100
- recommendation: exactly one of: Strong Match | Good Match | Partial Match | Not Recommended
- No markdown, no code blocks, no extra text before or after JSON
- Return ONLY the JSON object
"""

        def extract_json(text: str, default_recommendation: str, fallback_score: int) -> dict:
            cleaned = text.replace("\ufeff", "").replace("\r\n", "\n").strip()
            cleaned = re.sub(r"```(?:json)?\s*|```", "", cleaned, flags=re.IGNORECASE).strip()
            first = cleaned.find("{")
            last = cleaned.rfind("}")
            candidate = cleaned[first:last + 1] if first != -1 and last != -1 and last > first else cleaned

            for attempt in (candidate, cleaned):
                try:
                    value = json.loads(attempt)
                    if isinstance(value, list) and value:
                        return value[0]
                    return value
                except json.JSONDecodeError:
                    continue

            def find_int(key, default):
                m = re.search(rf"{key}\s*[:=-]\s*(\d+)", cleaned, flags=re.IGNORECASE)
                return int(m.group(1)) if m else default

            def find_recommendation():
                for label in ["Strong Match", "Good Match", "Partial Match", "Not Recommended"]:
                    if re.search(re.escape(label), cleaned, flags=re.IGNORECASE):
                        return label
                return default_recommendation

            def find_list(key):
                m = re.search(rf"{key}\s*[:=-]\s*(\[[^\]]*\]|(?:.*?)(?:\n\n|$))", cleaned, flags=re.IGNORECASE | re.DOTALL)
                if m:
                    text_value = m.group(1).strip()
                    try:
                        parsed = json.loads(text_value)
                        if isinstance(parsed, list):
                            return [str(item).strip() for item in parsed if str(item).strip()]
                    except Exception:
                        lines = [line.strip(' -•*\t') for line in text_value.splitlines() if line.strip()]
                        return [line for line in lines if line]
                return []

            reasoning = ""
            m = re.search(r"reasoning\s*[:=-]\s*([\s\S]+)$", cleaned, flags=re.IGNORECASE)
            if m:
                reasoning = m.group(1).strip().strip('"')

            return {
                "match_score": find_int("match_score", fallback_score),
                "strengths": find_list("strengths") or ["Could not parse detailed analysis"],
                "gaps": find_list("gaps") or ["Could not parse detailed analysis"],
                "recommendation": find_recommendation(),
                "reasoning": reasoning or f"Automated scoring only. Similarity: {fallback_score / 100:.2f}",
            }

        fallback_score = int(resume["similarity_score"] * 100)
        try:
            response = llm.invoke([HumanMessage(content=prompt)])
            raw = getattr(response, "content", str(response)).strip()
            with open(RAW_LLM_OUTPUT_PATH, "a", encoding="utf-8") as log_file:
                log_file.write(f"[RAW LLM OUTPUT for {resume['name']}]:\n{raw}\n---\n")
            if not raw:
                raise ValueError("Empty LLM response")
            analysis = extract_json(raw, default_recommendation="Partial Match", fallback_score=fallback_score)
        except Exception as e:
            print(f"[LLM Analysis Error] {type(e).__name__}: {e}")
            if 'response' in locals():
                raw_output = getattr(response, 'content', None)
                print(f"[Raw LLM output] {raw_output[:1000] if isinstance(raw_output, str) else raw_output}")
            analysis = {
                "match_score": fallback_score,
                "strengths": ["Could not parse detailed analysis"],
                "gaps": ["Could not parse detailed analysis"],
                "recommendation": "Partial Match",
                "reasoning": f"Automated scoring only. Similarity: {resume['similarity_score']:.2f}"
            }

        analyzed.append({
            **resume,
            "match_score": int(analysis.get("match_score", fallback_score)),
            "strengths": analysis.get("strengths", ["Could not parse detailed analysis"]),
            "gaps": analysis.get("gaps", ["Could not parse detailed analysis"]),
            "recommendation": analysis.get("recommendation", "Partial Match"),
            "reasoning": analysis.get("reasoning", f"Automated scoring only. Similarity: {resume['similarity_score']:.2f}"),
        })

    return {**state, "analyzed_resumes": analyzed}

# ─── Node 4: Rank ─────────────────────────────────────────────
def node_rank(state: AgentState) -> AgentState:
    ranked = sorted(
        state["analyzed_resumes"],
        key=lambda x: x.get("match_score", 0),
        reverse=True
    )
    final = []
    for i, r in enumerate(ranked):
        final.append({
            "rank": i + 1,
            "name": r["name"],
            "match_score": r.get("match_score", 0),
            "similarity_score": round(r.get("similarity_score", 0) * 100, 1),
            "recommendation": r.get("recommendation", "N/A"),
            "strengths": r.get("strengths", []),
            "gaps": r.get("gaps", []),
            "reasoning": r.get("reasoning", ""),
        })
    return {**state, "final_ranking": final}

# ─── Build LangGraph ─────────────────────────────────────────
def build_graph():
    graph = StateGraph(AgentState)
    graph.add_node("parse", node_parse)
    graph.add_node("score", node_score)
    graph.add_node("analyze", node_analyze)
    graph.add_node("rank", node_rank)

    graph.set_entry_point("parse")
    graph.add_edge("parse", "score")
    graph.add_edge("score", "analyze")
    graph.add_edge("analyze", "rank")
    graph.add_edge("rank", END)

    return graph.compile()

pipeline = build_graph()

# ─── API Endpoint ─────────────────────────────────────────────
@app.post("/screen")
async def screen_resumes(
    jd: str = Form(...),
    resumes: List[UploadFile] = File(...)
):
    if not jd.strip():
        raise HTTPException(status_code=400, detail="Job description cannot be empty.")
    if not resumes:
        raise HTTPException(status_code=400, detail="Upload at least one resume.")

    parsed_resumes = []
    for file in resumes:
        content = await file.read()
        if file.filename.endswith(".pdf"):
            text = extract_pdf_text(content)
        else:
            text = content.decode("utf-8", errors="ignore")
        parsed_resumes.append({"name": file.filename, "text": text})

    initial_state: AgentState = {
        "jd_text": jd,
        "resumes": parsed_resumes,
        "parsed_resumes": [],
        "scored_resumes": [],
        "analyzed_resumes": [],
        "final_ranking": [],
    }

    result = pipeline.invoke(initial_state)
    return {"results": result["final_ranking"]}

@app.get("/health")
def health():
    return {"status": "ok", "model": "llama-3.1-8b-instant", "pipeline": "LangGraph 4-node"}

@app.get("/debug-paths")
def debug_paths():
    return {
        "base_dir": BASE_DIR,
        "raw_llm_output_path": RAW_LLM_OUTPUT_PATH,
        "cwd": os.getcwd(),
    }
