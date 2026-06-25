# GeoTrade AI Platform (Geotrix)

[![Aesthetic Design](https://img.shields.io/badge/Design-Premium%20Dark-06b6d4.svg?style=flat-square)](#)
[![Python Version](https://img.shields.io/badge/Python-3.10%20%7C%203.11-blue.svg?style=flat-square)](#)
[![FastAPI](https://img.shields.io/badge/Backend-FastAPI-009688.svg?style=flat-square)](#)
[![React](https://img.shields.io/badge/Frontend-React%20%2F%20Vite%20%2F%20TS-61dafb.svg?style=flat-square)](#)

GeoTrade is an advanced geopolitical risk intelligence and quantitative trading signal platform. It monitors live global news and events, calculates the **Global Tension Index (GTI)** in real time, and uses machine learning models to generate actionable trading signals for commodities, equities, forex, and indices before markets react.

---

## 🌟 Key Features

*   **Real-time Geopolitical NLP Pipeline:** Monitors international news feeds, extracts named entities, performs sentiment analysis, and groups events using HDBSCAN and Zero-Shot Classifiers.
*   **Global Tension Index (GTI):** Computes live geopolitical stress levels globally and per country using weighted impact propagation.
*   **AI-Powered Trading Signals:** Generates trading signals (BUY/SELL/HOLD) with confidence levels, entry points, stop-losses, and targets using ML ensembles (CNN-BiGRU-Attention & XGBoost).
*   **Monte Carlo & Volatility Forecasting:** Simulates asset prices and evaluates risk metrics (Value at Risk, Expected Shortfall) under geopolitical shock scenarios.
*   **Interactive Visualizations:**
    *   **3D WebGL Globe:** Interactive country mesh colored by real-time risk scores with signal arcs between high-tension zones.
    *   **2D Leaflet Map:** Deep country profiles, historical timeline scrubs, and local asset correlation views.
    *   **Live Dashboard Tickers:** Pinned assets, charts, sparklines, and WebSocket-driven updates.
*   **AI Analyst Chatbot:** Natural language exploration of geopolitical signals and trading scenarios.

---

## 🏗️ Project Architecture

The project is structured as a decoupled monorepo:

```
geotrade-ai-platform/
├── backend/
│   ├── app/
│   │   ├── ai/                # NLP (Zero-shot, HDBSCAN), Embeddings, Reasoning
│   │   ├── api/               # FastAPI endpoints & WebSocket router
│   │   ├── core/              # Constants, configuration, and logging
│   │   ├── database/          # Models, seeds, and SQL database migrations
│   │   ├── ml/                # Volatility spike calibration, Impact Graphs, Backtesting
│   │   ├── models/            # SQLAlchemy database models
│   │   ├── pipelines/         # News and market ingestion pipelines
│   │   ├── repositories/      # Database access layers
│   │   ├── services/          # Business logic (Signal, GTI, Simulation)
│   │   └── utils/             # Helper classes, API clients, date formatting
│   ├── tests/                 # Comprehensive PyTest suite
│   └── requirements.txt       # Backend dependencies
│
└── frontend/my-app/
    ├── public/                # Static assets (GeoJSON boundary data)
    ├── src/
    │   ├── components/        # Reusable UI components (Chart, Gauge, Badges)
    │   ├── context/           # Session context and persistent WebSockets
    │   ├── hooks/             # Custom React hooks (useGTI, useSignals, useAlerts)
    │   ├── pages/             # App views (Dashboard, Map, Markets, Chat, Auth)
    │   ├── router/            # React Router tree & Authentication guards
    │   ├── styles/            # CSS Custom Property design tokens
    │   └── utils/             # Format and helper utilities
    └── package.json           # Frontend dependencies
```

---

## 💻 Tech Stack

### Backend & Machine Learning
*   **Framework:** FastAPI, Uvicorn
*   **Database ORM:** SQLAlchemy, Alembic, PostgreSQL / SQLite
*   **Deep Learning & NLP:** PyTorch, FAISS (vector search), Transformers
*   **Machine Learning:** XGBoost, Scikit-learn, Pandas, NumPy, Joblib
*   **Data Ingestion:** yFinance, News APIs

### Frontend
*   **Core:** React 19, TypeScript, Vite
*   **Styling:** Vanilla CSS Custom Properties (Sleek Dark Mode design system tokens)
*   **Mapping:** Leaflet, React-Leaflet
*   **Charts:** Recharts
*   **3D Graphics:** Three.js, React-Globe.gl
*   **Animations:** Framer Motion

---

## 🚀 Getting Started

### Prerequisites
*   Python 3.10 or 3.11
*   Node.js (v18+) & npm

---

### Backend Setup

1.  **Navigate to the backend directory:**
    ```bash
    cd backend
    ```

2.  **Create and activate a virtual environment:**
    ```bash
    python -m venv venv
    
    # On Windows (PowerShell):
    .\venv\Scripts\Activate.ps1
    
    # On macOS/Linux:
    source venv/bin/activate
    ```

3.  **Install dependencies:**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure environment variables:**
    Create a `.env` file in the `backend/` directory:
    ```env
    DATABASE_URL=sqlite:///./app_sql.db  # Or postgresql://user:password@localhost/geotrade
    SECRET_KEY=your-jwt-signing-secret
    ACCESS_TOKEN_EXPIRE_MINUTES=1440
    ```

5.  **Initialize Database & Seed Data:**
    Run the migrations and seed market structure:
    ```bash
    python -m app.database.seed_markets
    ```

6.  **Start the Backend Server:**
    ```bash
    uvicorn app.main:app --reload
    ```
    The Swagger API documentation will be available at `http://127.0.0.1:8000/docs`.

---

### Frontend Setup

1.  **Navigate to the frontend workspace:**
    ```bash
    cd frontend/my-app
    ```

2.  **Install node packages:**
    ```bash
    npm install
    ```

3.  **Run the development server:**
    ```bash
    npm run dev
    ```
    Open `http://localhost:5173` in your browser to view the application.

---

## 🧪 Running Tests

A comprehensive unit and integration test suite is located in `backend/tests`.

To execute tests, navigate to the `backend/` directory and run:
```bash
pytest
```

---

## 🔒 Security & Best Practices

*   **Token Authentication:** JSON Web Tokens (JWT) are signed and verified for all secure endpoints.
*   **Data Scrubber:** Compilation caches (`__pycache__` / `.pyc`), local simulation output text, and large binary machine learning weights (`*.pkl`, `*.index`) are strictly ignored via git to keep the repository optimized.
