"""
Genius Ayaan — Streamlit chat agent using a local Ollama API (no cloud LLM required).
"""

from __future__ import annotations

import html
import os
from pathlib import Path

import requests
import streamlit as st

from model_router import choose_model

BASE_DIR = Path(__file__).resolve().parent
AVATAR_PATH = BASE_DIR / "assets" / "ayaan.png"
ASSISTANT_AVATAR = str(AVATAR_PATH) if AVATAR_PATH.is_file() else "🧭"

_OLLAMA_BASE_URL_ENV = os.environ.get("OLLAMA_BASE_URL", "").strip()
OLLAMA_BASE_URL_EXPLICIT = bool(_OLLAMA_BASE_URL_ENV)
OLLAMA_BASE_URL = (_OLLAMA_BASE_URL_ENV or "http://localhost:11434").rstrip("/")
DEFAULT_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2")
try:
    TEMPERATURE = float(os.environ.get("OLLAMA_TEMPERATURE", "0.35"))
except ValueError:
    TEMPERATURE = 0.35


def _ollama_options(temperature: float) -> dict:
    """Sampling options tuned for fewer hallucinations (override via env)."""
    try:
        top_p = float(os.environ.get("OLLAMA_TOP_P", "0.9"))
    except ValueError:
        top_p = 0.9
    try:
        top_k = int(os.environ.get("OLLAMA_TOP_K", "40"))
    except ValueError:
        top_k = 40
    try:
        repeat_penalty = float(os.environ.get("OLLAMA_REPEAT_PENALTY", "1.15"))
    except ValueError:
        repeat_penalty = 1.15
    opts: dict = {
        "temperature": temperature,
        "top_p": top_p,
        "top_k": top_k,
        "repeat_penalty": repeat_penalty,
    }
    nctx = os.environ.get("OLLAMA_NUM_CTX", "").strip()
    if nctx.isdigit():
        opts["num_ctx"] = int(nctx)
    return opts


SYSTEM_PROMPT = """You are Genius Ayaan, a friendly explorer-themed assistant. Your top priority is to be truthful and useful.

Rules:
- Answer from general knowledge only. Do not invent facts, names, dates, citations, URLs, or statistics. If you are unsure, say you are not sure or that the user should verify with an authoritative source.
- For math, logic, or code: reason step by step; double-check conclusions; state assumptions.
- For medical, legal, or financial topics: give general information only and say the user must consult a qualified professional for decisions.
- Do not role-play having access to the internet, files, or private data unless the user explicitly provided that text in the conversation.
- Tone: warm and concise. Plain text unless the user asks for formatting.
- If the question is ambiguous, ask one brief clarifying question or state your best interpretation explicitly."""


def ollama_chat(
    messages: list[dict],
    model: str,
    temperature: float,
) -> str:
    payload = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": _ollama_options(temperature),
    }
    r = requests.post(
        f"{OLLAMA_BASE_URL}/api/chat",
        json=payload,
        timeout=600,
    )
    r.raise_for_status()
    data = r.json()
    msg = data.get("message") or {}
    content = msg.get("content")
    if not content:
        raise RuntimeError("Unexpected Ollama response: missing message content")
    return content


def _running_on_render() -> bool:
    return os.environ.get("RENDER", "").lower() in ("true", "1", "yes")


def _ollama_url_is_loopback() -> bool:
    u = OLLAMA_BASE_URL.lower()
    return "localhost" in u or "127.0.0.1" in u


def check_ollama() -> tuple[bool, str]:
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        r.raise_for_status()
        return True, "Connected"
    except requests.RequestException as e:
        return False, str(e)


def list_ollama_models() -> list[str]:
    try:
        r = requests.get(f"{OLLAMA_BASE_URL}/api/tags", timeout=5)
        r.raise_for_status()
        data = r.json()
        names = [m.get("name", "") for m in data.get("models", []) if m.get("name")]
        return sorted(names)
    except requests.RequestException:
        return []


def render_assistant_text(text: str) -> None:
    """Assistant text must not use Streamlit's default chat markdown (it can render white-on-white)."""
    safe = html.escape(text)
    st.markdown(
        f'<div class="ayaan-assistant-body">{safe}</div>',
        unsafe_allow_html=True,
    )


def apply_theme_css() -> None:
    st.markdown(
        """
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@400;600;700&display=swap');
        html, body {
            font-family: 'Nunito', sans-serif;
        }
        .block-container { padding-top: 1.5rem; max-width: 960px; }
        h1 { color: #1e5c3a !important; letter-spacing: 0.02em; }
        .stApp {
            font-family: 'Nunito', sans-serif;
            background: linear-gradient(180deg, #f6f3e8 0%, #e8f0e4 45%, #d4e8d0 100%);
            color-scheme: light;
            color: #1a1a1a;
            --text-color: #1a1a1a;
            --text-color-secondary: #3d3d3d;
        }
        /* Intro blurb (Streamlit markdown) */
        [data-testid="stMain"] .stMarkdown {
            color: #2d4a2f !important;
        }
        /* Chat: override Streamlit theme vars that can leave assistant text white */
        [data-testid="stMain"] [data-testid="stChatMessage"] {
            --text-color: #1a1a1a !important;
            --text-color-secondary: #3d3d3d !important;
        }
        [data-testid="stMain"] [data-testid="stChatMessage"] *:not(img):not(svg) {
            color: #1a1a1a !important;
            -webkit-text-fill-color: #1a1a1a !important;
        }
        /* Assistant content: HTML block (not st.markdown) so color is always readable */
        .ayaan-assistant-body {
            color: #1a1a1a !important;
            -webkit-text-fill-color: #1a1a1a !important;
            background: rgba(255, 255, 255, 0.88) !important;
            border-radius: 12px;
            padding: 0.75rem 1rem;
            border: 1px solid #a8bfa0;
            white-space: pre-wrap;
            line-height: 1.6;
            box-shadow: 0 1px 3px rgba(27, 67, 50, 0.12);
        }
        /* Chat input: Streamlit can use a dark field + our dark text → black-on-black */
        [data-testid="stChatInput"] textarea,
        .stChatInput textarea {
            background-color: #f7faf5 !important;
            color: #1a1a1a !important;
            -webkit-text-fill-color: #1a1a1a !important;
            caret-color: #1a1a1a !important;
            border: 1px solid #7a9e72 !important;
            border-radius: 10px !important;
        }
        [data-testid="stChatInput"] textarea::placeholder,
        .stChatInput textarea::placeholder {
            color: #5c6d5a !important;
            opacity: 1 !important;
        }
        [data-testid="stChatInput"],
        .stChatInput {
            --text-color: #1a1a1a !important;
        }
        [data-testid="stSidebar"] {
            background: linear-gradient(180deg, #2d6a4f 0%, #1b4332 100%);
            color: #fefae0;
        }
        [data-testid="stSidebar"] .stMarkdown { color: #fefae0 !important; }
        [data-testid="stSidebar"] p, [data-testid="stSidebar"] span, [data-testid="stSidebar"] label {
            color: #fefae0 !important;
        }
        div[data-testid="stVerticalBlockBorderWrapper"] {
            border-left: 4px solid #bc6c25;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def main() -> None:
    st.set_page_config(
        page_title="Genius Ayaan",
        page_icon="🧭",
        layout="wide",
        initial_sidebar_state="expanded",
    )
    apply_theme_css()

    if "messages" not in st.session_state:
        st.session_state.messages = []

    with st.sidebar:
        st.image(str(AVATAR_PATH), use_container_width=True)
        st.markdown("### Genius Ayaan")
        st.caption(
            "Explorer of ideas — models and routing are set via environment (Ollama URL + router)."
        )
        ok, status = check_ollama()
        if ok:
            st.success("Ollama is reachable.")
        else:
            st.error("Cannot reach Ollama.")
            if not OLLAMA_BASE_URL_EXPLICIT:
                st.caption(
                    "**`OLLAMA_BASE_URL` is not set** in the environment — using default "
                    "`http://localhost:11434` (only works when Ollama runs on the same machine/process)."
                )
            st.caption(f"**Trying:** `{OLLAMA_BASE_URL}`")
            st.caption(status)
            if _running_on_render() and (
                not OLLAMA_BASE_URL_EXPLICIT or _ollama_url_is_loopback()
            ):
                st.warning(
                    "**Render:** Dashboard → this **Web Service** → **Environment** → add "
                    "**`OLLAMA_BASE_URL`** = your Ollama base URL (e.g. `http://vps-ip:11434` or "
                    "`https://ollama.example.com`). Save, then **redeploy** or restart. "
                    "`localhost` here is the container, not your laptop."
                )
            st.markdown(
                "**Local:** `docker compose up -d --build` or `ollama serve` on your machine. "
                "**Hosted:** run Ollama on a reachable host and `ollama pull` your model there."
            )

        installed = list_ollama_models() if ok else []
        if installed:
            st.caption(f"**{len(installed)}** model(s) available on this Ollama server.")
            with st.expander("Installed models"):
                for name in installed:
                    st.text(name)
        elif ok:
            st.warning("No models reported by Ollama yet.")
            st.caption(
                "Self‑hosted Docker: ensure `ollama-pull` finished. "
                "Render: pull models on your Ollama host, or set OLLAMA_BASE_URL to a ready server."
            )

        if ok:
            with st.expander("How routing works"):
                st.markdown(
                    "Each question is classified (code / math / creative / reasoning / general). "
                    "The app picks a model from **OLLAMA_ROUTER_MODELS** or **MODEL_CODE**, "
                    "**MODEL_MATH**, etc. Configure these in the host environment (e.g. Render env)."
                )
            with st.expander("Accuracy tips"):
                st.markdown(
                    "Local LLMs can still be wrong. For better results: use a **larger** model "
                    "(e.g. `llama3.3` or 70B-class if your hardware allows), keep "
                    "**OLLAMA_TEMPERATURE** low (default is now **0.35**), and set "
                    "**OLLAMA_ROUTER_MODELS** so each role maps to the strongest model you have. "
                    "Optional: **OLLAMA_TOP_P**, **OLLAMA_TOP_K**, **OLLAMA_REPEAT_PENALTY**, **OLLAMA_NUM_CTX**."
                )
        if st.button("Clear conversation"):
            st.session_state.messages = []
            st.rerun()

    st.title("Genius Ayaan")
    st.markdown(
        "Ask anything — **Ayaan** routes your question to the best configured Ollama model."
    )

    for m in st.session_state.messages:
        with st.chat_message(m["role"], avatar="🧑‍🦱" if m["role"] == "user" else ASSISTANT_AVATAR):
            if m["role"] == "assistant":
                render_assistant_text(m["content"])
                meta = m.get("meta") or {}
                if meta.get("model"):
                    st.caption(f"Model `{meta.get('model')}` — {meta.get('route', '')}")
            else:
                st.markdown(m["content"])

    prompt = st.chat_input("Where should we explore today?")
    if not prompt:
        return

    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user", avatar="🧑‍🦱"):
        st.markdown(prompt)

    with st.chat_message("assistant", avatar=ASSISTANT_AVATAR):
        if not ok:
            st.error(
                "Ollama is not available. Fix **OLLAMA_BASE_URL** / your stack (see sidebar), then try again."
            )
            return
        reply = ""
        model = DEFAULT_MODEL
        route_reason = "auto"
        with st.spinner("Ayaan is charting an answer…"):
            try:
                model, route_reason = choose_model(
                    prompt,
                    installed if ok else [],
                    DEFAULT_MODEL,
                )
                api_messages = [{"role": "system", "content": SYSTEM_PROMPT}]
                for turn in st.session_state.messages:
                    api_messages.append({"role": turn["role"], "content": turn["content"]})
                reply = ollama_chat(api_messages, model=model, temperature=TEMPERATURE)
            except requests.exceptions.HTTPError as e:
                detail = ""
                try:
                    detail = e.response.text[:500]
                except Exception:
                    pass
                reply = (
                    f"Ollama returned an error (HTTP {e.response.status_code if e.response else '?' }). "
                    f"Have you run `ollama pull` for `{model}`? {detail}"
                )
                st.error("Request failed — see message below.")
            except requests.RequestException as e:
                reply = f"Network error talking to Ollama: {e}"
                st.error("Could not complete the request.")
            except Exception as e:
                reply = f"Unexpected error: {e}"
                st.error("Something went wrong while calling Ollama.")

        if reply:
            render_assistant_text(reply)
            st.caption(f"Model `{model}` — {route_reason}")
            st.session_state.messages.append(
                {
                    "role": "assistant",
                    "content": reply,
                    "meta": {"model": model, "route": route_reason},
                }
            )


if __name__ == "__main__":
    main()
