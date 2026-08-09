# SPELLSCROLL 📜 — AI Webtoon Discovery Platform

[![License: MIT](https://img.shields.io/badge/License-MIT-purple.svg)](https://opensource.org/licenses/MIT)
[![Framework: Django](https://img.shields.io/badge/Framework-Django--5-emerald.svg)](https://www.djangoproject.com/)
[![API: FastAPI](https://img.shields.io/badge/API-FastAPI-cyan.svg)](https://fastapi.tiangolo.com/)
[![Vector DB: ChromaDB](https://img.shields.io/badge/Vector_DB-ChromaDB-blue.svg)](https://www.trychroma.com/)
[![LLM API: Cerebras](https://img.shields.io/badge/LLM_API-Cerebras-orange.svg)](https://cerebras.ai/)

**SpellScroll** is a highly personalized, AI-curated colorful webtoon discovery and tracking platform. Designed as a unified ASGI application, it mounts a **FastAPI** REST backend inside a **Django** web framework process. It leverages a stateful **LangGraph** multi-agent pipeline, **ChromaDB** local vector search, and a beautiful dark ambient ink-and-neon user interface.

---

## ✨ Core Features

*   **⚡ Unified ASGI Server**: Runs Django Channels (WebSockets) and FastAPI REST endpoints under a single async process.
*   **🤖 LangGraph Recommendation Agent**: Orchestrated multi-agent pipeline matching user tastes to a database of 300+ webtoons.
*   **🔎 Local Semantic Embedding**: Uses local HuggingFace `all-MiniLM-L6-v2` embeddings for fast similarity computations without API fees.
*   **🌀 Resilient Offline Fallback**: Works seamlessly even without external AI keys, using rules-based matching.
*   **📱 PWA & Android-First Layout**: Service Workers, app manifests, and viewport sizing for installation directly onto Android devices.

---

## 🚀 Quick Start

<details>
<summary>📋 Prerequisites</summary>

- Python 3.10+
- Node.js 16+ (for asset pipeline)
- Cerebras API key
</details>

<details>
<summary>⚙️ Installation</summary>

```bash
git clone https://github.com/MdSadman20040812/SpellScroll.git
cd SpellScroll
python -m venv venv
source venv/bin/activate  # Windows: venv\Scripts\activate
pip install -r requirements.txt
```
</details>

<details>
<summary>🔑 Configuration</summary>

Create `.env` file:
```ini
CEREBRAS_API_KEY=your_key_here
DJANGO_SECRET_KEY=your_secret_key
DEBUG=True
```
</details>

<details>
<summary>▶️ Run Server</summary>

```bash
python manage.py migrate
python manage.py runserver
```
Open `http://localhost:8000`
</details>

---

## 📄 License

Distributed under the MIT License. See `LICENSE` for more information.

---

<div align="center">
  <sub>Built with rigor. Deployed with evidence. • 2026</sub>
</div>
