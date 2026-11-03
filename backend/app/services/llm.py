"""Optional free-LLM phrasing (Gemini free tier or Groq free tier). Never required: rag.py works fully without it.
The model only sees already-permitted, non-flagged excerpts, and its output is discarded unless it cites nothing new."""
import httpx

from ..config import settings


def available():
    return settings.llm_provider in ("gemini", "groq") and bool(settings.llm_api_key)


def valid_citations(text, n):
    """Accept model text only if it cites at least one excerpt and every [k] marker points at a supplied excerpt."""
    import re
    marks = [int(x) for x in re.findall(r"\[(\d+)\]", text or "")]
    return bool(marks) and all(1 <= k <= n for k in marks)


def rephrase(question, excerpts):
    out = _rephrase(question, excerpts)
    return out if out and valid_citations(out, len(excerpts)) else None


def _rephrase(question, excerpts):
    if not available():
        return None
    prompt = ("Answer the question using ONLY the numbered excerpts. Cite as [n]. If they do not answer it, say so.\n\n"
              + "\n".join(f"[{i + 1}] {e}" for i, e in enumerate(excerpts)) + f"\n\nQuestion: {question}")
    try:
        if settings.llm_provider == "groq":
            r = httpx.post("https://api.groq.com/openai/v1/chat/completions", timeout=20,
                           headers={"Authorization": f"Bearer {settings.llm_api_key}"},
                           json={"model": "llama-3.1-8b-instant", "messages": [{"role": "user", "content": prompt}]})
            return r.json()["choices"][0]["message"]["content"]
        if settings.llm_provider == "gemini":
            r = httpx.post("https://generativelanguage.googleapis.com/v1beta/models/gemini-1.5-flash:generateContent", timeout=20,
                           params={"key": settings.llm_api_key}, json={"contents": [{"parts": [{"text": prompt}]}]})
            return r.json()["candidates"][0]["content"]["parts"][0]["text"]
    except Exception:
        return None
    return None
