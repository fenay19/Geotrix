import axios from "axios";

// Default base URL matching the frontend .env
const API_URL = import.meta.env.VITE_API_URL || "http://localhost:8000/api/v1";

const apiClient = axios.create({
  baseURL: API_URL,
  withCredentials: true, // Needed for HTTP-only JWT cookies
});

// Request interceptor to attach Bearer fallback token if present in localStorage
apiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("geotrade_token");
  if (token) {
    config.headers.Authorization = `Bearer ${token}`;
  }
  return config;
});

export default apiClient;

// --- Authentication ---
export const authApi = {
  register: (payload: any) => apiClient.post("/auth/register", payload),
  login: (formData: URLSearchParams) =>
    apiClient.post("/auth/login", formData, {
      headers: { "Content-Type": "application/x-www-form-urlencoded" },
    }),
  logout: () => apiClient.post("/auth/logout"),
  getMe: () => apiClient.get("/auth/me"),
};

// --- GTI & Geopolitical Risk ---
export const riskApi = {
  getLatestGti: () => apiClient.get("/risk/gti"),
  getGtiHistory: (limit = 30) => apiClient.get("/risk/gti/history", { params: { limit } }),
  getCountries: () => apiClient.get("/risk/countries"),
  getHighRiskCountries: (minScore = 60.0) =>
    apiClient.get("/risk/countries/high-risk", { params: { min_score: minScore } }),
  getGlobeData: () => apiClient.get("/risk/globe"),
  refreshGti: () => apiClient.post("/risk/gti/refresh"),
  syncGlobalRisk: (includeAiSummary = true) =>
    apiClient.post("/risk/sync", null, { params: { include_ai_summary: includeAiSummary } }),
};

// --- Events ---
export const eventsApi = {
  getEvents: (skip = 0, limit = 100) => apiClient.get("/events/", { params: { skip, limit } }),
  getEvent: (eventId: number) => apiClient.get(`/events/${eventId}`),
  getHighSeverity: (minSeverity = 7) =>
    apiClient.get("/events/high-severity", { params: { min_severity: minSeverity } }),
  getEventsByType: (type: string) => apiClient.get(`/events/type/${type}`),
  getEventsByCountry: (countryId: number) => apiClient.get(`/events/country/${countryId}`),
  getTopRisksByCountry: (countryId: number, limit = 5) =>
    apiClient.get(`/events/top-risks/${countryId}`, { params: { limit } }),
  createEvent: (payload: any) => apiClient.post("/events/", payload),
  updateEvent: (eventId: number, payload: any) => apiClient.put(`/events/${eventId}`, payload),
  deleteEvent: (eventId: number) => apiClient.delete(`/events/${eventId}`),
};

// --- Supply Chain ---
export const supplyChainApi = {
  getNodes: () => apiClient.get("/supply-chain/nodes"),
  getLinks: () => apiClient.get("/supply-chain/links"),
  getGraph: (params: any) => apiClient.get("/supply-chain/graph", { params }),
  getNodeDetails: (nodeId: number) => apiClient.get(`/supply-chain/node/${nodeId}`),
  getCriticalPaths: () => apiClient.get("/supply-chain/critical-paths"),
  runSimulation: (params: any) => apiClient.post("/supply-chain/simulate", params),
  getSimulationLogs: (simulationId: string) =>
    apiClient.get(`/supply-chain/simulation/${simulationId}/logs`),
};

// --- Signals ---
export const signalsApi = {
  getSignals: (skip = 0, limit = 100) => apiClient.get("/signals/", { params: { skip, limit } }),
  getLatestSignal: (marketId: number) => apiClient.get(`/signals/market/${marketId}/latest`),
  getSignalsByMarket: (marketId: number) => apiClient.get(`/signals/market/${marketId}`),
  getSignal: (signalId: number) => apiClient.get(`/signals/${signalId}`),
  generateSignal: (marketId: number) => apiClient.post(`/signals/generate/${marketId}`),
  getWithMarket: (skip = 0, limit = 100) =>
    apiClient.get("/signals/with-market", { params: { skip, limit } }),
  getByClass: (assetClass: string) =>
    apiClient.get(`/signals/by-class/${assetClass}`),
};

// --- Extended Market API ---
export const marketApi = {
  getMarkets: () => apiClient.get("/market/"),
  getGlobalAssets: (limit = 5) => apiClient.get("/market/global", { params: { limit } }),
  getLocalAssets: (countryId: number, limit = 3) =>
    apiClient.get(`/market/local/${countryId}`, { params: { limit } }),
  getMarketDetails: (symbol: string) => apiClient.get(`/market/${symbol}`),
  syncMarketData: (historyDays = 30) =>
    apiClient.post("/market/sync", null, { params: { history_days: historyDays } }),
  getByClass: (assetClass: string) =>
    apiClient.get(`/market/by-class/${assetClass}`),
  getAllWithSignals: () => apiClient.get("/market/all-with-signals"),
};

// --- Forecast API ---
export const forecastApi = {
  getForecast: (symbol: string, horizonDays = 7) =>
    apiClient.get(`/forecast/${symbol}`, { params: { horizon_days: horizonDays } }),
  getMonteCarloForecast: (marketId: number, horizon = 30, nSims = 10000) =>
    apiClient.get(`/forecast/mc/${marketId}`, { params: { horizon, n_sims: nSims } }),
  compareForecasts: (symbol: string, horizonDays = 30) =>
    apiClient.get(`/forecast/mc/compare/${symbol}`, { params: { horizon_days: horizonDays } }),
};

// --- AI Chat ---
export const chatApi = {
  getSessions: (userId?: number) =>
    apiClient.get("/chat/sessions", { params: userId ? { user_id: userId } : {} }),
  createSession: (userId: number) =>
    apiClient.post("/chat/sessions", { user_id: userId, title: "New Session" }),
  deleteSession: (sessionId: number) =>
    apiClient.delete(`/chat/sessions/${sessionId}`),
  getMessages: (sessionId: number) =>
    apiClient.get(`/chat/sessions/${sessionId}/messages`),
  askAi: (sessionId: number, message: string) =>
    apiClient.post(`/chat/sessions/${sessionId}/ask`, { message }),
};

// --- Sandbox (Simulations/Scenarios) ---
export const sandboxApi = {
  getSimulations: () => apiClient.get("/simulation/"),
  runScenario: (payload: any) => apiClient.post("/simulation/run", payload),
};

// --- News ---
export const newsApi = {
  getLatestNews: (limit = 10) => apiClient.get("/news/", { params: { limit } }),
  getMarketNews: (category = "general") => apiClient.get("/news/market", { params: { category } }),
  getGeopoliticalNews: () => apiClient.get("/news/geopolitical"),
  getTopStocksNews: (symbols?: string) =>
    apiClient.get("/news/top-stocks", { params: symbols ? { symbols } : {} }),
  getCompanyNews: (symbol: string, fromDate: string, toDate: string) =>
    apiClient.get(`/news/company/${symbol}`, { params: { from_date: fromDate, to_date: toDate } }),
  syncEvents: () => apiClient.post("/news/sync-events"),
};
