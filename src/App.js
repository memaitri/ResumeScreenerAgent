import React, { useState, useRef } from "react";
import axios from "axios";
import "./App.css";

const API_URL = process.env.REACT_APP_API_URL || "";

const BADGE_COLORS = {
  "Strong Match": { bg: "#0cffe1", color: "#0a0f1e" },
  "Good Match": { bg: "#7fff5f", color: "#0a0f1e" },
  "Partial Match": { bg: "#ffc85a", color: "#0a0f1e" },
  "Not Recommended": { bg: "#ff4f4f", color: "#fff" },
};

function ScoreRing({ score }) {
  const r = 36;
  const circ = 2 * Math.PI * r;
  const dash = (score / 100) * circ;
  const color =
    score >= 75 ? "#0cffe1" : score >= 50 ? "#7fff5f" : score >= 30 ? "#ffc85a" : "#ff4f4f";

  return (
    <svg width="90" height="90" viewBox="0 0 90 90">
      <circle cx="45" cy="45" r={r} fill="none" stroke="#1e2540" strokeWidth="8" />
      <circle
        cx="45"
        cy="45"
        r={r}
        fill="none"
        stroke={color}
        strokeWidth="8"
        strokeDasharray={`${dash} ${circ}`}
        strokeLinecap="round"
        transform="rotate(-90 45 45)"
        style={{ transition: "stroke-dasharray 1s ease" }}
      />
      <text x="45" y="49" textAnchor="middle" fill={color} fontSize="16" fontWeight="700" fontFamily="'DM Mono', monospace">
        {score}
      </text>
    </svg>
  );
}

function ResumeCard({ result, index }) {
  const [open, setOpen] = useState(false);
  const badge = BADGE_COLORS[result.recommendation] || { bg: "#888", color: "#fff" };

  return (
    <div className={`card ${open ? "card-open" : ""}`} style={{ animationDelay: `${index * 0.1}s` }}>
      <div className="card-header" onClick={() => setOpen(!open)}>
        <div className="rank-badge">#{result.rank}</div>
        <div className="card-info">
          <span className="resume-name">{result.name}</span>
          <span className="rec-badge" style={{ background: badge.bg, color: badge.color }}>
            {result.recommendation}
          </span>
        </div>
        <ScoreRing score={result.match_score} />
        <span className="chevron">{open ? "▲" : "▼"}</span>
      </div>

      {open && (
        <div className="card-body">
          <div className="sim-row">
            <span className="sim-label">Vector Similarity</span>
            <div className="sim-bar-wrap">
              <div className="sim-bar" style={{ width: `${result.similarity_score}%` }} />
            </div>
            <span className="sim-val">{result.similarity_score}%</span>
          </div>

          <p className="reasoning">{result.reasoning}</p>

          <div className="tags-section">
            <div className="tags-col">
              <h4 className="tags-title green">✓ Strengths</h4>
              {result.strengths.map((s, i) => (
                <span key={i} className="tag tag-green">{s}</span>
              ))}
            </div>
            <div className="tags-col">
              <h4 className="tags-title red">✗ Gaps</h4>
              {result.gaps.map((g, i) => (
                <span key={i} className="tag tag-red">{g}</span>
              ))}
            </div>
          </div>
        </div>
      )}
    </div>
  );
}

export default function App() {
  const [jd, setJd] = useState("");
  const [files, setFiles] = useState([]);
  const [results, setResults] = useState([]);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");
  const [stage, setStage] = useState("");
  const fileRef = useRef();

  const stages = ["Parsing PDFs...", "Embedding & Scoring...", "LLM Analysis...", "Ranking candidates..."];
  let stageIdx = 0;
  let stageTimer = null;

  const startStageLoop = () => {
    stageIdx = 0;
    setStage(stages[0]);
    stageTimer = setInterval(() => {
      stageIdx = (stageIdx + 1) % stages.length;
      setStage(stages[stageIdx]);
    }, 4000);
  };

  const stopStageLoop = () => {
    if (stageTimer) clearInterval(stageTimer);
    setStage("");
  };

  const handleSubmit = async () => {
    if (!jd.trim()) return setError("Please enter a job description.");
    if (files.length === 0) return setError("Please upload at least one resume (PDF or TXT).");
    setError("");
    setResults([]);
    setLoading(true);
    startStageLoop();

    const formData = new FormData();
    formData.append("jd", jd);
    files.forEach((f) => formData.append("resumes", f));

    try {
      const res = await axios.post(`${API_URL}/screen`, formData, {
        headers: { "Content-Type": "multipart/form-data" },
      });
      setResults(res.data.results);
    } catch (e) {
      setError(e.response?.data?.detail || "Something went wrong. Is the backend running?");
    } finally {
      setLoading(false);
      stopStageLoop();
    }
  };

  return (
    <div className="app">
      <div className="noise" />
      <header className="header">
        <div className="logo">
          <span className="logo-icon">⬡</span>
          <span className="logo-text">Resume<span className="accent">IQ</span></span>
        </div>
        <p className="tagline">Multi-Agent Resume Screener · Powered by LangGraph + Groq</p>
      </header>

      <main className="main">
        <div className="input-section">
          <div className="field">
            <label className="field-label">Job Description</label>
            <textarea
              className="textarea"
              rows={7}
              placeholder="Paste the full job description here — required skills, responsibilities, qualifications..."
              value={jd}
              onChange={(e) => setJd(e.target.value)}
            />
          </div>

          <div className="field">
            <label className="field-label">Upload Resumes</label>
            <div
              className="dropzone"
              onClick={() => fileRef.current.click()}
              onDragOver={(e) => e.preventDefault()}
              onDrop={(e) => {
                e.preventDefault();
                const dropped = Array.from(e.dataTransfer.files);
                setFiles((prev) => [...prev, ...dropped]);
              }}
            >
              <input
                ref={fileRef}
                type="file"
                multiple
                accept=".pdf,.txt"
                style={{ display: "none" }}
                onChange={(e) => setFiles(Array.from(e.target.files))}
              />
              <span className="drop-icon">📄</span>
              <span className="drop-text">
                {files.length > 0
                  ? files.map((f) => f.name).join(", ")
                  : "Drag & drop PDFs or click to browse"}
              </span>
            </div>
            {files.length > 0 && (
              <button className="clear-btn" onClick={() => setFiles([])}>✕ Clear files</button>
            )}
          </div>

          {error && <div className="error-box">⚠ {error}</div>}

          <button className="run-btn" onClick={handleSubmit} disabled={loading}>
            {loading ? (
              <span className="btn-loading">
                <span className="spinner" /> {stage}
              </span>
            ) : (
              "▶ Run Screening Pipeline"
            )}
          </button>
        </div>

        {results.length > 0 && (
          <div className="results-section">
            <div className="results-header">
              <h2 className="results-title">Screening Results</h2>
              <span className="results-count">{results.length} candidate{results.length > 1 ? "s" : ""} analyzed</span>
            </div>
            <div className="pipeline-labels">
              {["Parse", "Embed", "LLM Analyze", "Rank"].map((label, i) => (
                <React.Fragment key={label}>
                  <span className="pipe-node">{label}</span>
                  {i < 3 && <span className="pipe-arrow">→</span>}
                </React.Fragment>
              ))}
            </div>
            {results.map((r, i) => (
              <ResumeCard key={i} result={r} index={i} />
            ))}
          </div>
        )}
      </main>

      <footer className="footer">
        Built with LangChain · LangGraph · Groq · FastAPI · React
      </footer>
    </div>
  );
}
