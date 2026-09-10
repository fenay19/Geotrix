Viewed README.md:1-471

Here is the complete, raw markdown content of your updated [`README.md`](file:///e:/Geo_mapping/geotrade-ai-platform/README.md):

```markdown
# 🌐 GeoTrade AI Platform (Geotrix)

<div align="center">

[![Python](https://img.shields.io/badge/Python-3.10%20%7C%203.11-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org/)
[![PyTorch](https://img.shields.io/badge/PyTorch-CUDA%20Accelerated-EE4C2C?style=for-the-badge&logo=pytorch&logoColor=white)](https://pytorch.org/)
[![NVIDIA GPU Ready](https://img.shields.io/badge/NVIDIA-CUDA%20%2F%20Tensor%20Cores-76B900?style=for-the-badge&logo=nvidia&logoColor=white)](https://developer.nvidia.com/cuda-zone)
[![FastAPI](https://img.shields.io/badge/FastAPI-009688?style=for-the-badge&logo=fastapi&logoColor=white)](https://fastapi.tiangolo.com/)
[![React 19](https://img.shields.io/badge/React%2019-Vite%20%2B%20TypeScript-61DAFB?style=for-the-badge&logo=react&logoColor=black)](https://react.dev/)
[![Three.js](https://img.shields.io/badge/Three.js-3D%20WebGL-000000?style=for-the-badge&logo=three.js&logoColor=white)](https://threejs.org/)
[![License](https://img.shields.io/badge/License-MIT-green.svg?style=for-the-badge)](LICENSE)

**Next-Generation Geopolitical Risk Intelligence & High-Frequency Quantitative Trading Platform**

*Real-time global news NLP, dynamic stress graph propagation (GTI), deep neural sequence embeddings, and GPU-accelerated predictive ensemble models.*

[Key Features](#-key-features) • [System Architecture](#-project-architecture) • [AI/ML Engine](#-aiml--deep-learning-architecture) • [Tech Stack](#-tech-stack) • [Quickstart](#-getting-started) • [Evaluation & Benchmarks](#-evaluation--benchmarks)

---

</div>

## 📌 Executive Overview

**GeoTrade AI (Geotrix)** is an enterprise-grade quantitative intelligence engine designed to bridge the gap between global geopolitical volatility and algorithmic trading. By continuously ingesting multi-source international intelligence feeds, GeoTrade computes the real-time **Global Tension Index (GTI)**, propagates regional stress across sector supply chains, and deploys deep neural attention architectures combined with gradient-boosted ensembles to forecast asset price action and volatility shocks before traditional financial markets price them in.

```
┌─────────────────┐      ┌─────────────────────────┐      ┌───────────────────────┐
│ Live Global     │ ───► │ NLP & Vector Embeddings │ ───► │ Global Tension Index  │
│ News & Events   │      │ (HDBSCAN + Zero-Shot)   │      │ (GTI Stress Engine)   │
└─────────────────┘      └─────────────────────────┘      └──────────┬────────────┘
                                                                     │
┌─────────────────┐      ┌─────────────────────────┐                 ▼
│ Market Data     │ ───► │ PyTorch CNN-BiGRU-Attn  │ ───► ┌───────────────────────┐
│ (OHLCV + Vol)   │      │ + XGBoost/LGBM Ensemble │      │ Alpha Trading Signals │
└─────────────────┘      └─────────────────────────┘      │ & VaR Risk Shocks     │
                                                          └───────────────────────┘
```

---

## 🌟 Key Features

### 1. 🧠 Real-Time Geopolitical NLP Engine
- **Semantic Clustering & Deduplication:** Hierarchical density-based clustering (**HDBSCAN**) groups thousands of streaming multilingual news articles into discrete geopolitical incidents.
- **Zero-Shot Event Classification:** Multi-label categorization across critical geopolitical categories (Military Escalation, Sanctions, Trade Embargos, Civil Unrest, Resource Disruption).
- **FAISS Vector Indexing:** High-dimensional vector space for semantic similarity searches and historical event analogue retrieval.

### 2. 🌍 Global Tension Index (GTI) & Spillover Propagation
- **Dynamic Country Risk Scoring:** Quantifies real-time geopolitical stress (0–100) per nation by aggregating event frequency, entity sentiment, and severity weights.
- **Graph-Based Impact Propagation:** Models systemic contagion across bilateral trade dependencies, military alliances, and geographic proximity.
- **Sector Sensitivity Matrices:** Real-time correlation engine mapping regional shocks to specific commodity, currency, and equity baskets.

### 3. ⚡ Deep Learning & Quantitative Signal Pipeline
- **Hybrid Neural Sequence Architecture:** Custom **Stacked Conv1D + Deep 2-Layer BiGRU + 4-Head Multi-Head Self-Attention** neural embedder producing 32-dimensional sequence representations of market dynamics.
- **Focal Loss $(\gamma = 2)$ Optimization:** Mitigates class imbalance and sharpens model sensitivity toward rare, high-impact `SELL` and market dislocation signals.
- **Calibrated Ensemble Model:** Dual-layer inference combining PyTorch sequence embeddings, **XGBoost**, and **LightGBM** classifiers with per-asset **Platt Scaling** for calibrated probability estimation.
- **Actionable Execution Targets:** Computes direction (`BUY` / `SELL` / `HOLD`), calibrated confidence scores, dynamic stop-losses, and multi-stage take-profit horizons.

### 4. 📉 Extreme Risk & Monte Carlo Stress Testing
- **GARCH(1,1) Volatility Calibration:** Models asymmetric volatility clustering and conditional heteroskedasticity during market disruptions.
- **Shock-Scenario Simulation:** Executes 10,000+ stochastic price trajectories under calibrated geopolitical shocks.
- **Parametric & Non-Parametric Risk Metrics:** Computes 95% & 99% **Value at Risk (VaR)** and **Expected Shortfall (CVaR)**.

### 5. 🖥️ Interactive Full-Stack Visualization
- **3D WebGL Interactive Globe:** Real-time Three.js / Globe.gl visualization with dynamic country risk shaders, active conflict heatmaps, and signal propagation arcs.
- **2D Tactical Leaflet Map:** Detailed country-level intelligence drill-downs, asset correlation matrices, and historical timeline scrubbers.
- **Live WebSocket Feeds:** Sub-second latency streaming of GTI updates, breaking intelligence alerts, and newly generated trading signals.
- **Financial Candlestick Charts:** Interactive technical charts with integrated geopolitical overlay flags and execution levels.
- **AI Geopolitical Copilot:** Natural language conversational assistant for rapid scenario exploration, historical risk retrospectives, and portfolio impact queries.

---

## 🏗️ System & Pipeline Architecture

```mermaid
flowchart TD
    %% =========================================================================
    %% TIER 1: DATA INGESTION & EXTERNAL FEEDS
    %% =========================================================================
    subgraph TIER1["TIER 1 · STREAMING DATA INGESTION"]
        direction LR
        RAW_NEWS["📰 Global News Feeds<br/>(GDELT, NewsAPI, RSS)"]
        RAW_MKT["📈 Market OHLCV Data<br/>(Equities, Forex, Commodities)"]
        RAW_MACRO["🌐 Macro Indicators<br/>(Interest Rates, VIX, Oil/Gas)"]
    end

    %% =========================================================================
    %% TIER 2: DUAL-STREAM INTELLIGENCE PROCESSING
    %% =========================================================================
    subgraph TIER2["TIER 2 · AI/NLP & DEEP LEARNING FEATURE EXTRACTION"]
        direction TB

        subgraph STREAM_NLP["Stream A: Geopolitical NLP & Tension Engine"]
            direction TB
            NLP_PROC["NER & Multi-Lingual Sentiment Scorer"]
            NLP_CLUSTER["HDBSCAN Semantic Deduplication & Clustering"]
            NLP_ZERO["Zero-Shot Event Classifier (BART / DeBERTa)"]
            NLP_VEC[("FAISS High-Dimension Vector Store")]
            GTI_ENGINE["GTI Stress & Trade Contagion Graph Engine"]

            NLP_PROC --> NLP_CLUSTER --> NLP_ZERO --> NLP_VEC --> GTI_ENGINE
        end

        subgraph STREAM_DL["Stream B: PyTorch Neural Sequence Embedder (NVIDIA CUDA)"]
            direction TB
            SEQ_IN["OHLCV Tensor Window: (Batch, 30 Days, 5 Features)"]
            CONV1D["Stacked Conv1D Encoder (Kernel: 3, 64-Channels, GELU)"]
            BIGRU["2-Layer Bidirectional GRU (Hidden Dim: 128)"]
            MHA["4-Head Multi-Head Self-Attention Layer"]
            SEQ_EMBED["Projection Head → 32-Dimensional Latent Embedding"]

            SEQ_IN --> CONV1D --> BIGRU --> MHA --> SEQ_EMBED
        end
    end

    %% =========================================================================
    %% TIER 3: QUANTITATIVE ENSEMBLE & RISK SIMULATION
    %% =========================================================================
    subgraph TIER3["TIER 3 · QUANTITATIVE ENSEMBLE & RISK ENGINE"]
        direction TB
        FUSION["⚡ Feature Fusion Layer<br/>(32D Sequence Latent + GTI Stress Vector + Sector Sensitivities)"]
        
        subgraph MODELS["Alpha Prediction & Calibration"]
            direction LR
            XGB["XGBoost Classifier<br/>(SELL-Weighted F1)"]
            LGBM["LightGBM Regressor<br/>(Target Drift)"]
            PLATT["Per-Asset Platt Scaling<br/>(Probability Calibrator)"]
        end

        subgraph RISK_ENG["Volatility & Extreme Shock Modeling"]
            direction LR
            GARCH["GARCH(1,1)<br/>Volatility Forecaster"]
            MONTE_CARLO["Monte Carlo Simulator<br/>(10,000 Paths, VaR / CVaR)"]
        end

        FUSION --> XGB & LGBM
        XGB & LGBM --> PLATT
        FUSION --> GARCH --> MONTE_CARLO
    end

    %% =========================================================================
    %% TIER 4: BACKEND GATEWAY & REAL-TIME STREAMING
    %% =========================================================================
    subgraph TIER4["TIER 4 · FASTAPI BACKEND CORE & DISPATCH"]
        direction LR
        FASTAPI_CORE["⚡ FastAPI REST Gateway<br/>(Async Endpoints, OpenAPI Docs)"]
        WS_HUB["📡 Real-Time WebSocket Hub<br/>(Sub-Second Broadcast Engine)"]
        DB_STORE[("🗄️ Database Layer<br/>(SQLAlchemy + PostgreSQL / SQLite)")]
        AI_COPILOT["🤖 Geopolitical Copilot Agent<br/>(LLM Context Retrieval)"]
    end

    %% =========================================================================
    %% TIER 5: REACT 19 + THREE.JS WEB CLIENT
    %% =========================================================================
    subgraph TIER5["TIER 5 · USER INTERFACE & VISUALIZATION (REACT 19 + TS)"]
        direction LR
        UI_GLOBE["🌍 3D WebGL Globe<br/>(Three.js / React-Globe.gl)"]
        UI_MAP["🗺️ 2D Tactical Map<br/>(React-Leaflet Overlays)"]
        UI_SIGNALS["📊 Alpha Signal Feed<br/>(Entry, Target, Stop Loss)"]
        UI_CHARTS["📈 Financial Candlesticks<br/>(Technical & Shock Overlays)"]
        UI_CHAT["💬 AI Analyst Chatbot<br/>(Natural Language Queries)"]
    end

    %% =========================================================================
    %% CLEAN TIER-TO-TIER DATAFLOW
    %% =========================================================================
    RAW_NEWS --> NLP_PROC
    RAW_MKT --> SEQ_IN
    RAW_MACRO --> GTI_ENGINE

    GTI_ENGINE --> FUSION
    SEQ_EMBED --> FUSION

    PLATT --> FASTAPI_CORE
    MONTE_CARLO --> FASTAPI_CORE
    NLP_VEC -.-> AI_COPILOT

    FASTAPI_CORE --- DB_STORE
    FASTAPI_CORE --> WS_HUB
    
    WS_HUB ==>|Persistent WebSocket Stream| UI_GLOBE & UI_MAP & UI_SIGNALS & UI_CHARTS
    FASTAPI_CORE -->|REST API Requests & Responses| UI_CHAT & UI_SIGNALS

    %% =========================================================================
    %% AESTHETIC THEME & STYLING
    %% =========================================================================
    classDef default fill:#0b0f19,stroke:#1e293b,stroke-width:1px,color:#f1f5f9;
    classDef t1 fill:#1e293b,stroke:#3b82f6,stroke-width:2px,color:#f8fafc;
    classDef t2 fill:#0f172a,stroke:#06b6d4,stroke-width:2px,color:#f8fafc;
    classDef t3 fill:#0f172a,stroke:#76b900,stroke-width:2px,color:#f8fafc;
    classDef t4 fill:#0f172a,stroke:#10b981,stroke-width:2px,color:#f8fafc;
    classDef t5 fill:#0f172a,stroke:#8b5cf6,stroke-width:2px,color:#f8fafc;
    classDef highlight fill:#1e1b4b,stroke:#a855f7,stroke-width:2px,color:#ffffff;

    class RAW_NEWS,RAW_MKT,RAW_MACRO t1;
    class NLP_PROC,NLP_CLUSTER,NLP_ZERO,NLP_VEC,GTI_ENGINE,SEQ_IN,CONV1D,BIGRU,MHA,SEQ_EMBED t2;
    class FUSION highlight;
    class XGB,LGBM,PLATT,GARCH,MONTE_CARLO t3;
    class FASTAPI_CORE,WS_HUB,DB_STORE,AI_COPILOT t4;
    class UI_GLOBE,UI_MAP,UI_SIGNALS,UI_CHARTS,UI_CHAT t5;
```

---

## 📂 Repository Directory Layout

GeoTrade is structured as a decoupled, high-throughput monorepo:

```
geotrade-ai-platform/
├── backend/
│   ├── app/
│   │   ├── ai/                      # NLP pipeline, Zero-Shot classifiers & FAISS vector store
│   │   │   ├── embeddings/          # Vector indexing & similarity search
│   │   │   ├── nlp/                 # Entity extraction, sentiment & HDBSCAN clustering
│   │   │   └── reasoning/           # LLM intelligence summarization & copilot logic
│   │   ├── api/                     # FastAPI v1 REST routes & WebSocket streams
│   │   │   ├── routes/              # Auth, Signals, GTI, Markets, Simulation, Supply Chain
│   │   │   └── websocket.py         # Real-time event broadcasting router
│   │   ├── core/                    # System configuration, security, JWT & logging
│   │   ├── database/                # SQLAlchemy ORM models, migrations & market seeders
│   │   ├── ml/                      # Quantitative engines & model definitions
│   │   │   ├── impact_graph/        # Graph-based contagion & sector sensitivity matrices
│   │   │   ├── inference/           # Live ML predictor & Platt calibrator runners
│   │   │   ├── monte_carlo/         # GARCH(1,1) & stochastic shock simulation
│   │   │   ├── sequence_model.py    # PyTorch Conv1D-BiGRU-Attention architecture
│   │   │   └── vol_spike/           # Volatility spike calibration models
│   │   ├── pipelines/               # Streaming news ingestion & market data collectors
│   │   ├── repositories/            # Data access abstraction layers
│   │   ├── schemas/                 # Pydantic validation & response schemas
│   │   └── services/                # Business logic (Signals, GTI Engine, Simulation)
│   ├── tests/                       # Comprehensive PyTest unit and integration suite
│   ├── requirements.txt             # Backend dependencies & ML frameworks
│   └── pytest.ini                   # Test configuration
│
├── frontend/my-app/
│   ├── public/                      # Static assets & GeoJSON world boundary maps
│   ├── src/
│   │   ├── components/              # Modular UI components (Globe, Charts, Gauges, Terminal)
│   │   │   ├── globe/               # 3D Three.js WebGL globe & arc visualizers
│   │   │   ├── map/                 # 2D Tactical Leaflet geo-intelligence overlays
│   │   │   ├── shell/               # Navigation, command palette, status bars
│   │   │   └── ui/                  # Candlestick charts, risk badges, metric cards
│   │   ├── context/                 # WebSocket state management & authentication session
│   │   ├── hooks/                   # Custom React hooks (useGTI, useSignals, useAlerts)
│   │   ├── pages/                   # Application views (Dashboard, Globe, Markets, Supply Chain)
│   │   ├── router/                  # React Router DOM tree & protected route guards
│   │   └── styles/                  # Design tokens, glassmorphism & dark UI tokens
│   └── package.json                 # Frontend dependencies & Vite configuration
│
├── notebooks/                       # Research, backtesting & exploratory data analysis
├── scripts/                         # Training pipelines, model evaluations & batch runners
│   ├── train_ensemble.py            # Universal ensemble & sequence model training script
│   ├── evaluate_all.py              # Full out-of-sample backtesting & evaluation suite
│   └── train_asset.py               # Asset-specific calibration utilities
└── README.md                        # Documentation & setup guide
```

---

## 🧬 AI/ML & Deep Learning Architecture

```
                  ┌─────────────────────────────────────────────────────────┐
                  │                 Input Market Window (30, 5)             │
                  │                    [Open, High, Low, Close, Volume]     │
                  └────────────────────────────┬────────────────────────────┘
                                               │
                                               ▼
                  ┌─────────────────────────────────────────────────────────┐
                  │             Stacked 1D Convolutional Encoder            │
                  │   Conv1D(5→64, k=3) → BatchNorm → GELU → Dropout(0.2)   │
                  │   Conv1D(64→64, k=3) → BatchNorm → GELU → Dropout(0.2)  │
                  └────────────────────────────┬────────────────────────────┘
                                               │
                                               ▼
                  ┌─────────────────────────────────────────────────────────┐
                  │                Deep Bidirectional GRU Layer             │
                  │       2-Layer BiGRU (hidden_dim=128, bidirectional)     │
                  │               Output Dimension: (batch, 30, 256)        │
                  └────────────────────────────┬────────────────────────────┘
                                               │
                                               ▼
                  ┌─────────────────────────────────────────────────────────┐
                  │                Multi-Head Self-Attention                │
                  │              4 Heads over 256-dim feature space         │
                  │          Captures critical inflection points & shocks   │
                  └────────────────────────────┬────────────────────────────┘
                                               │
                                               ▼
                  ┌─────────────────────────────────────────────────────────┐
                  │                     Projection Head                     │
                  │             Linear(256 → 128) → GELU → Dropout          │
                  │                      Linear(128 → 32)                   │
                  └────────────────────────────┬────────────────────────────┘
                                               │
                         ┌─────────────────────┴─────────────────────┐
                         ▼                                           ▼
          ┌──────────────────────────────┐            ┌──────────────────────────────┐
          │     32-Dim Market Latent     │            │    Geopolitical Risk Context │
          │      Sequence Embedding      │            │   (GTI, Sector Delta, News)  │
          └──────────────┬───────────────┘            └──────────────┬───────────────┘
                         │                                           │
                         └─────────────────────┬─────────────────────┘
                                               │
                                               ▼
                  ┌─────────────────────────────────────────────────────────┐
                  │                Ensemble Classifier Layer                │
                  │      XGBoost Classifier + LightGBM Boosted Trees        │
                  │        Optimized with Focal Loss & Platt Calibrators    │
                  └────────────────────────────┬────────────────────────────┘
                                               │
                                               ▼
                  ┌─────────────────────────────────────────────────────────┐
                  │          Calibrated Alpha Signal & Execution Plan       │
                  │       Signal: BUY / SELL / HOLD  |  Confidence: 89.4%   │
                  │       Entry: $2,042.50 | Target: $2,085.00 | SL: $2,020 │
                  └─────────────────────────────────────────────────────────┘
```

### ⚡ NVIDIA & Hardware Acceleration
- **PyTorch CUDA Backend:** Accelerated tensor operations and matrix multiplications for the neural sequence embedder.
- **GPU Mixed Precision (`torch.cuda.amp`):** High-throughput inference for real-time news vectorization and sequence modeling.
- **FAISS GPU/CPU Vector Similarity:** Fast approximate nearest neighbor search across hundreds of thousands of geopolitical vector embeddings.

---

## 💻 Tech Stack

| Domain | Technology / Framework | Details |
| :--- | :--- | :--- |
| **Deep Learning & GPU** | `PyTorch`, `CUDA`, `FAISS` | Conv1D-BiGRU-Attention sequence embedder, GPU vector search |
| **Machine Learning** | `XGBoost`, `LightGBM`, `Scikit-learn` | Gradient boosted decision ensembles, Platt probability calibrators |
| **Time-Series & Risk** | `arch`, `NumPy`, `Pandas`, `SciPy` | GARCH(1,1) volatility modeling, Monte Carlo VaR/CVaR simulations |
| **NLP & Semantics** | `Transformers`, `HDBSCAN`, `NLTK` | Zero-shot event classification, semantic clustering, NER |
| **Backend Framework** | `FastAPI`, `Uvicorn`, `Pydantic v2` | Asynchronous REST APIs, WebSocket streaming, OpenAPI docs |
| **Database & ORM** | `SQLAlchemy 2.0`, `Alembic`, `PostgreSQL` / `SQLite` | High-concurrency ORM, schema migrations, asset time-series |
| **Frontend Core** | `React 19`, `TypeScript`, `Vite` | Modern component architecture, type safety, fast HMR |
| **3D & 2D Geo-Visualization**| `Three.js`, `React-Globe.gl`, `Leaflet` | WebGL 3D global risk shaders, tactical 2D geospatial map |
| **Financial Charting** | `Recharts`, `Custom Canvas Candlesticks` | High-density interactive financial charts, sparklines, gauges |
| **Styling & UI Tokens** | `Vanilla CSS Tokens`, `Framer Motion` | Sleek dark mode, terminal glassmorphism, responsive layouts |

---

## 🚀 Getting Started

### Prerequisites
- **Python:** `3.10` or `3.11`
- **Node.js:** `v18+` or `v20+` & `npm`
- **GPU (Optional but Recommended):** NVIDIA GPU with CUDA support for accelerated PyTorch training & inference.

---

### 1. Backend Setup

1. **Navigate to the backend directory:**
   ```bash
   cd backend
   ```

2. **Create and activate a virtual environment:**
   ```bash
   # On macOS / Linux:
   python -m venv venv
   source venv/bin/activate

   # On Windows (PowerShell):
   python -m venv venv
   .\venv\Scripts\Activate.ps1
   ```

3. **Install dependencies:**
   ```bash
   pip install -r requirements.txt
   ```

4. **Configure environment variables:**
   Create a `.env` file in the `backend/` directory (or copy `.env.example`):
   ```env
   DATABASE_URL=sqlite:///./sql_app.db
   SECRET_KEY=your-secure-jwt-signing-secret-key-32-chars-min
   ACCESS_TOKEN_EXPIRE_MINUTES=1440
   ENVIRONMENT=development
   CORS_ORIGINS=http://localhost:5173,http://127.0.0.1:5173
   ```

5. **Initialize Database & Seed Market Structure:**
   ```bash
   python -m app.database.seed_markets
   ```

6. **Start the FastAPI Backend Server:**
   ```bash
   uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
   ```
   *Interactive Swagger API documentation will be available at: `http://127.0.0.1:8000/docs`*

---

### 2. Frontend Setup

1. **Navigate to the frontend directory:**
   ```bash
   cd frontend/my-app
   ```

2. **Install Node packages:**
   ```bash
   npm install
   ```

3. **Launch the development server:**
   ```bash
   npm run dev
   ```
   *Open `http://localhost:5173` in your browser to access the GeoTrade dashboard.*

---

## 🧪 Model Training & Evaluation Suite

GeoTrade includes training scripts and evaluation suites for reproducing the ensemble models and running out-of-sample backtests.

```bash
# 1. Run environment and dependency dry-run
python train_all.py --dry-run

# 2. Train the Universal Sequence Model & Ensemble Classifiers
python train_ensemble.py

# 3. Execute comprehensive out-of-sample evaluation across all asset classes
python evaluate_all.py
```

### Running Backend Unit & Integration Tests

```bash
cd backend
pytest -v
```

---

## 📡 API & WebSocket Endpoints

| Method | Endpoint | Description |
| :--- | :--- | :--- |
| `GET` | `/api/v1/gti/current` | Retrieve live Global Tension Index, country scores & 24h delta |
| `GET` | `/api/v1/gti/history` | Historical GTI time-series across configurable lookback windows |
| `GET` | `/api/v1/signals/latest` | Latest AI-generated quant signals with targets, stop-losses & confidence |
| `POST` | `/api/v1/simulation/monte-carlo`| Execute stochastic geopolitical shock Monte Carlo simulation (VaR/CVaR) |
| `GET` | `/api/v1/supply-chain/chokepoints`| Critical trade chokepoints, geopolitical exposure & risk status |
| `POST` | `/api/v1/chat/query` | Natural language queries to the AI Geopolitical Copilot |
| `WS` | `/ws/live` | Persistent sub-second WebSocket stream for real-time market & risk updates |

---

## 🔒 Security & Engineering Best Practices

- **Zero Secret Commits:** All secrets, keys, and tokens are managed via environment variables and strictly excluded from version control via `.gitignore`. An `.env.example` template is provided for quick setup.
- **Stateless JWT Authentication:** Industry-standard OAuth2 password bearer flow with encrypted JSON Web Tokens.
- **Model Weight Hygiene:** Large model checkpoints, FAISS indexes, and simulation caches are excluded from git to ensure a clean and lightweight repository.

---

<div align="center">


</div>
```
