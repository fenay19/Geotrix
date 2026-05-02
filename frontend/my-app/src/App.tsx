import { useEffect, useState } from "react";
import { QueryClient, QueryClientProvider } from "@tanstack/react-query";
import { Toaster } from "sonner";
import { AnimatePresence, motion } from "framer-motion";
import { useUIStore } from "./store";
import { authApi } from "./api";

// View Components
import Auth from "./components/auth/Auth";
import TopNav from "./components/layout/Navigation";
import Dashboard from "./components/dashboard/Dashboard";
import Map from "./components/map/Map";
import Markets from "./components/markets/Markets";
import Signals from "./components/signals/Signals";
import Operations from "./components/operations/Operations";
import AiChat from "./components/ai-chat/AiChat";

// Initialize Query Client with graceful error handling
const queryClient = new QueryClient({
  defaultOptions: {
    queries: {
      refetchOnWindowFocus: false,
      retry: (failureCount, error: any) => {
        // Don't retry on 401/403/404
        const status = error?.response?.status;
        if (status === 401 || status === 403 || status === 404) return false;
        return failureCount < 1;
      },
    },
  },
});

const pageVariants = {
  initial: { opacity: 0, y: 8 },
  animate: { opacity: 1, y: 0, transition: { duration: 0.2, ease: "easeOut" as const } },
  exit:    { opacity: 0, y: -4, transition: { duration: 0.12 } },
};

function MainApp() {
  const { token, user, setUser, logout, activeTab } = useUIStore();
  const [wsConnected, setWsConnected] = useState(false);
  const [lastWsEvent, setLastWsEvent] = useState<any>(null);

  useEffect(() => {
    if (token && !user) {
      authApi.getMe()
        .then((res) => setUser(res.data))
        .catch(() => logout());
    }
  }, [token, user, setUser, logout]);

  useEffect(() => {
    if (!token) return;
    const getWsUrl = () => {
      const protocol = window.location.protocol === "https:" ? "wss:" : "ws:";
      const host = window.location.hostname || "localhost";
      return `${protocol}//${host}:8000/api/v1/ws/live-risk`;
    };
    let ws: WebSocket;
    let reconnectTimeout: any;
    const connectWs = () => {
      ws = new WebSocket(getWsUrl());
      ws.onopen  = () => setWsConnected(true);
      ws.onmessage = (event) => {
        try {
          if (event.data === "pong") return;
          setLastWsEvent(JSON.parse(event.data));
        } catch {}
      };
      ws.onclose = () => {
        setWsConnected(false);
        reconnectTimeout = setTimeout(connectWs, 3000);
      };
      ws.onerror = () => ws.close();
    };
    connectWs();
    const pingInterval = setInterval(() => {
      if (ws && ws.readyState === WebSocket.OPEN) ws.send("ping");
    }, 10000);
    return () => {
      clearInterval(pingInterval);
      clearTimeout(reconnectTimeout);
      if (ws) { ws.onclose = null; ws.close(); }
    };
  }, [token]);

  if (!token) return <Auth />;

  const renderView = () => {
    switch (activeTab) {
      case "dashboard":  return <Dashboard key="dashboard" lastWsEvent={lastWsEvent} />;
      case "map":        return <Map key="map" />;
      case "markets":    return <Markets key="markets" />;
      case "signals":    return <Signals key="signals" />;
      case "operations": return <Operations key="operations" />;
      case "ai-chat":    return <AiChat key="ai-chat" />;
      default:           return <Dashboard key="dashboard" lastWsEvent={lastWsEvent} />;
    }
  };

  return (
    <div className="flex flex-col h-screen w-screen overflow-hidden" style={{ backgroundColor: "var(--bg-void)" }}>
      {/* Top Navigation Bar */}
      <TopNav wsConnected={wsConnected} />

      {/* Page content */}
      <div className="flex-1 overflow-hidden relative">
        <AnimatePresence mode="wait">
          <motion.div
            key={activeTab}
            variants={pageVariants}
            initial="initial"
            animate="animate"
            exit="exit"
            className="h-full w-full"
          >
            {renderView()}
          </motion.div>
        </AnimatePresence>
      </div>
    </div>
  );
}

export default function App() {
  return (
    <QueryClientProvider client={queryClient}>
      <MainApp />
      <Toaster
        position="bottom-right"
        theme="dark"
        toastOptions={{
          style: {
            background: "var(--bg-surface)",
            border: "1px solid var(--amber-border)",
            color: "var(--text-primary)",
            fontFamily: "'Space Mono', monospace",
            fontSize: "11px",
          },
        }}
      />
    </QueryClientProvider>
  );
}
