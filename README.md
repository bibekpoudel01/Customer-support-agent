
# Customer Support Agent

A grounded AI customer support agent for e-commerce platforms — built to answer product questions the way a real store assistant would: **only from the store's own product data**, never from outside knowledge or guesswork.

> **Status: active development.** Core structure (ingestion, agent, guardrails, gateway) is in place. See [Roadmap](#roadmap) for what's wired up vs. still in progress.

---

## The idea

Think of a support chatbot for a platform like **Flipkart or Amazon**: a user asks *"Does this phone support fast charging?"* or *"Suggest a laptop under $700"*, and the agent answers using **only the product catalog it's been given** — currently ~50 products with full details (specs, price, stock, warranty, etc.).

If the answer isn't in the data, the agent says so instead of making something up. No hallucinated specs, no invented prices, no guessed policies.


## What it does

- Answers product questions: specs, features, compatibility, warranty, price, stock
- Recommends products based on budget, category, or use case
- Refuses to answer (clearly, not with a fabricated guess) when the catalog doesn't have the information
- Ingests product data from multiple formats (PDF, DOCX, HTML, JSON, TXT) into a searchable vector store
- Runs behind a gateway with guardrail checks before/after generation

---

## Project structure

```
Customer-support-agent/
├── DATA/                     # Product data (~50 products) used as the agent's source of truth
├── Eval/                     # Evaluation scripts/notebooks for the agent's answers
├── notebook/                 # Exploratory / prototyping notebooks
├── src/
│   ├── agent/                 # Agent / orchestration logic (query handling, response generation)
│   ├── config/                # App configuration (settings, env handling)
│   ├── gateway/                # API layer - entrypoint for user requests
│   ├── guardrails/            # Grounding / safety checks - keeps answers tied to real product data
│   ├── ingestion/
│   │   ├── chunking/
│   │   │   └── splitter.py     # Splits product docs into chunks for embedding
│   │   ├── data_loader/
│   │   │   ├── document_loader.py
│   │   │   ├── docx_parser.py
│   │   │   ├── html_parser.py
│   │   │   ├── json_parser.py
│   │   │   ├── pdf_parser.py
│   │   │   └── txt_parser.py   # Format-specific parsers for product data sources
│   │   └── vectorstore.py      # Builds/updates the vector index from parsed product data
│   ├── repo/                  # Data access layer (repository pattern over stored product data)
│   ├── schemas/               # Pydantic/data models for products, requests, responses
│   ├── services/              # Business logic services (e.g. retrieval, recommendation)
│   ├── __init__.py
│   └── app.py                  # Application entrypoint wiring gateway + agent together
├── .gitignore
├── LICENSE
├── main.py                    # Project entrypoint
├── pyproject.toml             # Project dependencies (managed with uv)
├── uv.lock
└── README.md
```

## How it works (high level)

```
Product data (DATA/)
        │
        ▼
Ingestion  →  format-specific parsers (pdf/docx/html/json/txt)
        │
        ▼
Chunking   →  splitter.py breaks content into retrievable pieces
        │
        ▼
Vector store (vectorstore.py)
        │
        ▼
User query  →  gateway  →  agent  →  retrieval over vector store
        │
        ▼
Guardrails  →  checks the answer is grounded in retrieved product data
        │
        ▼
Response to user (or an honest "I don't have that information")
```

## Tech stack

- **Python**, dependency management via **uv** (`pyproject.toml` + `uv.lock`)
- Custom ingestion pipeline for multi-format product documents (PDF, DOCX, HTML, JSON, TXT)
- Vector store–backed retrieval for semantic search over product data
- Guardrails layer to keep generation grounded in retrieved context
- API gateway as the entrypoint for user requests

## Getting started

```bash
# clone the repo
git clone https://github.com/bibekpoudel01/Customer-support-agent.git
cd Customer-support-agent

# install dependencies (uv)
uv sync

# run the app
uv run main.py
```

> Setup details (env vars, required services) are still being finalized — see [Roadmap](#roadmap).

## Roadmap

**In place**
- Project structure: ingestion, chunking, agent, guardrails, gateway, services
- Multi-format product data parsers (PDF/DOCX/HTML/JSON/TXT)
- Vector store integration for semantic retrieval

**In progress**
- End-to-end wiring from gateway → agent → guardrails → response
- Evaluation suite (`Eval/`) for answer grounding/accuracy
- Product recommendation logic in `services/`

**Planned**
- Caching layer (exact + semantic) to avoid redundant retrieval/LLM calls
- Conversation memory (short-term per session, long-term for preferences)
- Observability (latency, token usage, cache hit ratio, error rate)
- CI/CD and containerized deployment

## Contributing

The goal of this project is to be a real, working example of a **grounded** RAG-based support agent — not a demo that quietly hallucinates when the catalog runs out of answers. If you're contributing:

- Keep new logic inside the matching layer (`ingestion` for data loading, `agent` for orchestration, `guardrails` for grounding checks, `services` for business logic)
- Anything that touches how answers are generated should preserve the "only answer from retrieved data" rule
- Open an issue before large changes so effort isn't duplicated

## License

MIT — see [LICENSE](./LICENSE).