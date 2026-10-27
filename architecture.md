# 🏛️ GetMeHired — System Architecture & Engineering Design

This document provides a comprehensive technical overview of the architecture, design principles, data flow, and multi-agent coordination powering **GetMeHired**.

---

## 📐 1. System Architecture Overview

GetMeHired is designed as a **local-first, autonomous multi-agent co-pilot**. It decouples background ingestion and scraping from inference, persistence, and UI presentation.

```mermaid
flowchart TD
    subgraph DataSourcing ["1. Ingestion & Sourcing Subsystem"]
        S1["LinkedIn Jobs Scraper"] --> AGG["Aggregator & Deduplicator"]
        S2["Naukri (India) Scraper"] --> AGG
        S3["Indeed & Glassdoor Scraper"] --> AGG
        S4["Deep JD Fetcher<br/>(Playwright / curl_cffi)"] --> AGG
    end

    subgraph PreProcessing ["2. Experience & Seniority Guard"]
        AGG --> EXP["Experience Requirement Evaluator"]
        EXP -- "> 3 Years or Senior/Lead Signals" --> DISQ["Auto-Disqualification<br/>(Score Capped < 25)"]
        EXP -- "0-3 Years (In Target Scope)" --> STAGE["Eligible Opportunity Queue"]
    end

    subgraph MultiAgentCore ["3. Multi-Agent Intelligence Core"]
        STAGE --> A1["Agent 1: ATS Match & Keyword Gap Scorer"]
        A1 --> SLM["Local Ollama SLM (qwen3.5:4b)"]
        SLM -. "Timeout / Cold Fallback" .-> DET["Deterministic Overlap Heuristics"]
        STAGE --> A2["Agent 2: Decision Maker & Referral Finder"]
        STAGE --> A3["Agent 3: Multi-Channel Outreach Generator"]
    end

    subgraph StorageLayer ["4. Persistence & CRM State"]
        DISQ --> DB[("SQLite Database<br/>(getmehired.db)")]
        A1 --> DB
        A2 --> DB
        A3 --> DB
    end

    subgraph PresentationDelivery ["5. Delivery & Interaction"]
        DB --> API["FastAPI REST API (Uvicorn)"]
        API --> UI["React 18 Glassmorphic Dashboard"]
        A1 -- "Fit Score >= Threshold (e.g. 75%)" --> NTFY["iPhone Push Dispatcher<br/>(ntfy.sh Webhook)"]
    end
```

---

## 🧩 2. Core Architectural Principles

### 2.1 Local-First & Zero Cloud Leakage
- **$0 API Bills**: All reasoning, scoring, and text generation execute locally via [Ollama](https://ollama.ai) (`qwen3.5:4b`, `llama3.2`, etc.).
- **Data Privacy**: Resumes, contact records, application history, and notes never leave the user's local machine.
- **Offline Resilience**: Built-in deterministic heuristic engines ensure that even if the local LLM is offline or busy, the search and matching pipelines continue running.

### 2.2 Micro-Call LLM Design (SLM Optimization)
Small language models (3B–7B parameters) frequently degrade, hallucinate, or drop JSON formatting when overloaded with monolithic prompts. 

GetMeHired solves this through **isolated micro-prompts**:
1. **Call 1 (Scoring)**: Evaluates quantitative alignment (0–100) and rationale.
2. **Call 2 (Tailored Bullets)**: Generates resume bullets customized to the company's tech stack.
3. **Call 3 (ATS Keyword Gaps)**: Compares required keywords against the candidate's skills.

If any micro-call fails or times out, the system seamlessly falls back to pre-computed deterministic text generation without failing the pipeline.

### 2.3 Strict Seniority & Experience Guard
Job boards frequently mislabel positions (e.g., categorizing an "Associate" role that secretly requires 5+ years of experience). 

The `extract_experience_requirement()` engine runs multi-pass regex across job titles and full JD descriptions:
- **Senior Role Patterns**: Detects `senior`, `lead`, `principal`, `staff`, `architect`, `mentoring other engineers`, etc.
- **Experience Ranges**: Extracts unicode numeric ranges (`3-6 years`, `4+ years`, `5–8 yrs`).
- **Disqualification Logic**: Automatically marks out-of-scope roles as `is_disqualified = True`, penalizing fit scores by 60–70 points so they never trigger push notifications.

---

## 🔄 3. Multi-Agent Pipeline Workflow

```
[Trigger: APScheduler (every 30 mins) or 1-Click UI]
    │
    ▼
1. Sourcing Phase (aggregator.py)
   ├── Query LinkedIn, Naukri, Indeed, Glassdoor with target roles & locations
   ├── Normalize job titles, companies, and locations
   └── Hash-based deduplication (company + title + URL)
    │
    ▼
2. Filtering Phase (deep_jd_fetcher.py & job_matcher.py)
   ├── Fetch full job description if truncated (Playwright / HTTP fallback)
   ├── Run Seniority & Experience Guard
   └── Queue eligible jobs for evaluation
    │
    ▼
3. Multi-Profile Round-Robin LLM Enrichment (pipeline.py)
   ├── Iterates through configured candidate profiles
   ├── Enforces 45-minute autonomous window guard
   ├── Executes micro-agents (Job Matcher, Contact Finder, Outreach Generator)
   └── Commits enriched opportunities to SQLite
    │
    ▼
4. Alert & Delivery Phase (notifier.py)
   ├── Checks if match_score >= auto_notify_threshold (default: 75%)
   └── Dispatches immediate push notification to candidate's mobile device via ntfy.sh
```

---

## 🗄️ 4. Database Schema & Persistence

GetMeHired uses a relational SQLite database (`data/getmehired.db`) managed via `backend/database.py`:

```mermaid
erDiagram
    JOBS {
        string id PK
        string title
        string company
        string location
        string source
        string job_url
        string description
        string salary
        integer match_score
        string match_rationale
        text matching_skills
        text missing_skills
        text tailored_bullets
        string experience_required
        integer is_disqualified
        string candidate_id
        string status
        string created_at
    }

    CONTACTS {
        string id PK
        string job_id FK
        string company
        string name
        string role
        string contact_type
        string profile_url
        string linkedin_search_url
        string google_dork_url
        integer confidence_score
    }

    OUTREACH_MESSAGES {
        string id PK
        string job_id FK
        string contact_id FK
        string message_type
        string subject
        text content
        string status
    }

    APPLICATIONS {
        string id PK
        string company
        string role
        string job_url
        string status
        string date_applied
        text notes
        string candidate_id
    }

    CONVERSATIONS {
        string id PK
        string application_id FK
        string company
        string person_name
        string person_role
        string profile_url
        string status
        string follow_up_due_date
        string candidate_id
    }

    JOBS ||--o{ CONTACTS : "has"
    JOBS ||--o{ OUTREACH_MESSAGES : "generates"
    APPLICATIONS ||--o{ CONVERSATIONS : "tracks"
```

---

## ⚙️ 5. Configuration & State Management

GetMeHired enforces a zero-inline-code policy. State and configuration are read through a 3-tier hierarchy:

1. **Environment Variables (`.env`)**: Highest precedence. Used for server, scheduler, and default profile settings.
2. **Persisted Settings (`data/settings.json`)**: User-editable runtime state modified via the React dashboard settings tab.
3. **Code Defaults (`backend/config.py`)**: Safe fallback values if no configuration exists.

All candidate profile definitions, stage banners, blacklisted companies, and notification targets are stored in `data/settings.json`, ensuring the codebase remains 100% agnostic to any specific candidate.

---

## 🛡️ 6. Error Handling & Reliability

- **Ollama Offline**: If Ollama is not running, `ollama_client.py` gracefully fails health checks, triggering deterministic keyword overlap calculations and standard achievement bullet generation.
- **Scraper Rate Limiting**: Scrapers incorporate random jitter delays, exponential backoffs, and user-agent rotation to prevent IP bans.
- **Process Protection**: The autonomous loop runs inside a 45-minute strict timeout cap (`max_duration_seconds = 45 * 60`), preventing hung child threads from consuming system resources.
- **Git Shielding**: Sensitive files (`.env`, `*.db`, personal resumes `*.pdf`) are strictly excluded in `.gitignore` to prevent credential and personal data exposure.
