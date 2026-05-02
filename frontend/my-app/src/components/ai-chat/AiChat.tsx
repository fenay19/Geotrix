import { useState, useEffect, useRef } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { useQuery, useMutation, useQueryClient } from "@tanstack/react-query";
import { chatApi, riskApi } from "../../api";
import { useUIStore } from "../../store";
import { MessageSquare, Plus, Trash2, Send, Bot, User, Loader2 } from "lucide-react";
import { toast } from "sonner";
import ReactMarkdown from "react-markdown";

const SUGGESTED_PROMPTS = [
  "What's driving gold prices right now?",
  "Analyze Middle East risk impact on oil markets",
  "Which markets are most exposed to US-China tensions?",
  "Compare LMT vs RTX signal strength",
  "What does a high GTI mean for my portfolio?",
  "Summarize the top 3 active geopolitical risks",
];

export default function AiChat() {
  const { user, activeChatSessionId, setActiveChatSessionId } = useUIStore();
  const [input, setInput] = useState("");
  const [isTyping, setIsTyping] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const textareaRef = useRef<HTMLTextAreaElement>(null);
  const qc = useQueryClient();

  // Fetch sessions
  const { data: sessionsData } = useQuery({
    queryKey: ["chat-sessions", user?.id],
    queryFn: () => chatApi.getSessions(user?.id),
    enabled: !!user,
  });
  const sessions: any[] = sessionsData?.data || [];

  // Fetch messages for active session
  const { data: messagesData } = useQuery({
    queryKey: ["chat-messages", activeChatSessionId],
    queryFn: () => chatApi.getMessages(activeChatSessionId!),
    enabled: !!activeChatSessionId,
    refetchInterval: false,
  });
  const messages: any[] = messagesData?.data || [];

  // GTI context for sidebar
  const { data: gtiData } = useQuery({
    queryKey: ["gti-chat"],
    queryFn: () => riskApi.getLatestGti(),
    refetchInterval: 60000,
  });
  const gti = gtiData?.data;

  // Create session
  const createSessionMutation = useMutation({
    mutationFn: () => chatApi.createSession(user?.id || 0),
    onSuccess: (res) => {
      qc.invalidateQueries({ queryKey: ["chat-sessions"] });
      setActiveChatSessionId(res.data.id);
    },
    onError: () => toast.error("Failed to create session."),
  });

  // Delete session
  const deleteSessionMutation = useMutation({
    mutationFn: (id: number) => chatApi.deleteSession(id),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["chat-sessions"] });
      setActiveChatSessionId(null);
    },
    onError: () => toast.error("Failed to delete session."),
  });

  // Send message
  const askMutation = useMutation({
    mutationFn: (msg: string) => chatApi.askAi(activeChatSessionId!, msg),
    onMutate: () => setIsTyping(true),
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ["chat-messages", activeChatSessionId] });
      setIsTyping(false);
    },
    onError: () => {
      setIsTyping(false);
      toast.error("AI response failed. Please try again.");
    },
  });

  const handleSend = (msg?: string) => {
    const text = (msg || input).trim();
    if (!text || !activeChatSessionId || askMutation.isPending) return;
    setInput("");
    // Optimistically invalidate to show user msg quickly
    askMutation.mutate(text);
  };

  const handleKeyDown = (e: React.KeyboardEvent) => {
    if ((e.ctrlKey || e.metaKey) && e.key === "Enter") {
      e.preventDefault();
      handleSend();
    }
  };

  // Auto-scroll to bottom
  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  }, [messages, isTyping]);

  // Auto-resize textarea
  useEffect(() => {
    if (textareaRef.current) {
      textareaRef.current.style.height = "auto";
      textareaRef.current.style.height = Math.min(textareaRef.current.scrollHeight, 120) + "px";
    }
  }, [input]);

  const gtiColor = !gti ? "var(--text-muted)"
    : gti.current_score >= 80 ? "var(--sell)"
      : gti.current_score >= 60 ? "var(--risk-high)"
        : gti.current_score >= 35 ? "var(--hold)"
          : "var(--buy)";

  return (
    <div className="flex h-full overflow-hidden" style={{ backgroundColor: "var(--bg-primary)" }}>

      {/* ── Sessions Sidebar ──────────────────────────────────────────────── */}
      <motion.div
        initial={{ x: -40, opacity: 0 }}
        animate={{ x: 0, opacity: 1 }}
        transition={{ duration: 0.3, ease: [0.16, 1, 0.3, 1] }}
        className="flex flex-col border-r shrink-0"
        style={{
          width: 280,
          borderColor: "var(--border)",
          backgroundColor: "var(--bg-secondary)",
        }}
      >
        {/* Sidebar header */}
        <div className="flex items-center justify-between px-4 py-3 border-b"
          style={{ borderColor: "var(--border)" }}>
          <div className="flex items-center gap-2">
            <MessageSquare size={14} style={{ color: "var(--amber)" }} />
            <span className="section-label" style={{ color: "var(--amber)" }}>
              AI ANALYST SESSIONS
            </span>
          </div>
          <motion.button
            whileTap={{ scale: 0.92 }}
            onClick={() => createSessionMutation.mutate()}
            disabled={createSessionMutation.isPending || !user}
            className="flex items-center gap-1 px-2 py-1 rounded cursor-pointer transition-all"
            style={{
              background: "var(--amber-glow)",
              border: "1px solid var(--amber-border)",
              color: "var(--amber)",
              fontFamily: "'Space Mono', monospace",
              fontSize: "9px",
              letterSpacing: "0.06em",
            }}
          >
            <Plus size={10} />
            NEW
          </motion.button>
        </div>

        {/* Session list */}
        <div className="flex-1 overflow-y-auto py-2">
          {sessions.length === 0 ? (
            <div className="flex flex-col items-center justify-center h-32 gap-2">
              <MessageSquare size={20} style={{ color: "var(--text-ghost)" }} />
              <span className="section-label">NO SESSIONS</span>
            </div>
          ) : (
            <motion.div className="space-y-1 px-2">
              {sessions.map((s: any, i: number) => {
                const active = s.id === activeChatSessionId;
                return (
                  <motion.div
                    key={s.id}
                    initial={{ opacity: 0, x: -10 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: i * 0.04 }}
                    onClick={() => setActiveChatSessionId(s.id)}
                    className="flex items-center justify-between px-3 py-2.5 rounded cursor-pointer group transition-all"
                    style={{
                      backgroundColor: active ? "var(--amber-glow)" : "transparent",
                      border: active ? "1px solid var(--amber-border)" : "1px solid transparent",
                    }}
                  >
                    <div className="flex flex-col min-w-0">
                      <span style={{
                        fontFamily: "'Space Mono', monospace",
                        fontSize: "10px",
                        color: active ? "var(--amber)" : "var(--text-secondary)",
                        fontWeight: active ? 700 : 400,
                      }}>
                        Session #{s.id}
                      </span>
                      <span className="section-label mt-0.5">
                        {new Date(s.created_at).toLocaleDateString("en-US", { month: "short", day: "numeric" })}
                      </span>
                    </div>
                    <motion.button
                      initial={{ opacity: 0 }}
                      whileHover={{ opacity: 1 }}
                      className="opacity-0 group-hover:opacity-100 p-1 rounded cursor-pointer"
                      style={{ color: "var(--sell)" }}
                      onClick={(e) => {
                        e.stopPropagation();
                        deleteSessionMutation.mutate(s.id);
                      }}
                    >
                      <Trash2 size={11} />
                    </motion.button>
                  </motion.div>
                );
              })}
            </motion.div>
          )}
        </div>

        {/* Context badges */}
        <div className="border-t p-4 space-y-2" style={{ borderColor: "var(--border)" }}>
          <span className="section-label">LIVE CONTEXT</span>
          {gti && (
            <div className="flex items-center justify-between">
              <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "10px", color: "var(--text-muted)" }}>
                GTI Score
              </span>
              <span style={{
                fontFamily: "'Space Mono', monospace",
                fontSize: "11px",
                fontWeight: 700,
                color: gtiColor,
              }}>
                {Math.round(gti.current_score)} · {gti.severity_category}
              </span>
            </div>
          )}
          <div className="flex items-center justify-between">
            <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "10px", color: "var(--text-muted)" }}>
              RAG Events
            </span>
            <span style={{ fontFamily: "'Space Mono', monospace", fontSize: "10px", color: "var(--violet)" }}>
              ● INDEXED
            </span>
          </div>
        </div>
      </motion.div>

      {/* ── Chat Window ───────────────────────────────────────────────────── */}
      <div className="flex-1 flex flex-col overflow-hidden">
        {/* Chat header */}
        <div className="flex items-center gap-3 px-6 py-3 border-b shrink-0"
          style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-secondary)" }}>
          <div className="w-8 h-8 rounded flex items-center justify-center"
            style={{ background: "var(--violet-dim)", border: "1px solid var(--violet-border)" }}>
            <Bot size={16} style={{ color: "var(--violet)" }} />
          </div>
          <div>
            <div style={{ fontFamily: "'Syne', sans-serif", fontSize: "14px", fontWeight: 700, color: "var(--text-primary)" }}>
              GeoTrade AI Analyst
            </div>
            <div className="section-label">Powered by RAG + Live GTI Context</div>
          </div>
        </div>

        {/* Messages */}
        <div className="flex-1 overflow-y-auto px-6 py-4 space-y-4">
          {!activeChatSessionId ? (
            /* No session selected */
            <div className="flex flex-col items-center justify-center h-full gap-6">
              <div className="flex flex-col items-center gap-3">
                <div className="w-16 h-16 rounded flex items-center justify-center"
                  style={{ background: "var(--violet-dim)", border: "1px solid var(--violet-border)" }}>
                  <Bot size={28} style={{ color: "var(--violet)" }} />
                </div>
                <div style={{ fontFamily: "'Syne', sans-serif", fontSize: "18px", fontWeight: 700, color: "var(--text-primary)" }}>
                  Select or create a session
                </div>
                <p style={{ fontFamily: "Inter, sans-serif", fontSize: "13px", color: "var(--text-muted)", textAlign: "center", maxWidth: 320 }}>
                  Ask the AI analyst about geopolitical risks, asset signals, and market impacts.
                </p>
              </div>
              <div className="grid grid-cols-2 gap-2" style={{ maxWidth: 480 }}>
                {SUGGESTED_PROMPTS.slice(0, 4).map((p) => (
                  <motion.button
                    key={p}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={async () => {
                      const res = await chatApi.createSession(user?.id || 0);
                      const newId = res.data.id;
                      qc.invalidateQueries({ queryKey: ["chat-sessions"] });
                      setActiveChatSessionId(newId);
                      setTimeout(() => askMutation.mutate(p), 300);
                    }}
                    className="px-3 py-2.5 text-left rounded cursor-pointer transition-all"
                    style={{
                      background: "var(--bg-card)",
                      border: "1px solid var(--border)",
                      fontFamily: "Inter, sans-serif",
                      fontSize: "11px",
                      color: "var(--text-secondary)",
                      lineHeight: 1.4,
                    }}
                  >
                    {p}
                  </motion.button>
                ))}
              </div>
            </div>
          ) : messages.length === 0 && !isTyping ? (
            /* Empty session — show suggested prompts */
            <div className="flex flex-col items-center justify-center h-full gap-4">
              <p className="section-label">Try asking:</p>
              <div className="grid grid-cols-2 gap-2" style={{ maxWidth: 480 }}>
                {SUGGESTED_PROMPTS.map((p) => (
                  <motion.button
                    key={p}
                    whileHover={{ scale: 1.02 }}
                    whileTap={{ scale: 0.98 }}
                    onClick={() => handleSend(p)}
                    className="px-3 py-2.5 text-left rounded cursor-pointer"
                    style={{
                      background: "var(--bg-card)",
                      border: "1px solid var(--border)",
                      fontFamily: "Inter, sans-serif",
                      fontSize: "11px",
                      color: "var(--text-secondary)",
                      lineHeight: 1.4,
                    }}
                  >
                    {p}
                  </motion.button>
                ))}
              </div>
            </div>
          ) : (
            /* Messages */
            <>
              <AnimatePresence initial={false}>
                {messages.map((msg: any, i: number) => {
                  const isUser = msg.role === "user";
                  return (
                    <motion.div
                      key={msg.id || i}
                      initial={{ opacity: 0, y: 16 }}
                      animate={{ opacity: 1, y: 0 }}
                      transition={{ duration: 0.25, ease: [0.16, 1, 0.3, 1] }}
                      className={`flex gap-3 ${isUser ? "flex-row-reverse" : "flex-row"}`}
                    >
                      {/* Avatar */}
                      <div
                        className="w-7 h-7 rounded shrink-0 flex items-center justify-center mt-0.5"
                        style={{
                          background: isUser ? "var(--amber-glow)" : "var(--violet-dim)",
                          border: `1px solid ${isUser ? "var(--amber-border)" : "var(--violet-border)"}`,
                        }}
                      >
                        {isUser
                          ? <User size={13} style={{ color: "var(--amber)" }} />
                          : <Bot size={13} style={{ color: "var(--violet)" }} />
                        }
                      </div>

                      {/* Bubble */}
                      <div
                        className="rounded px-4 py-3 max-w-[70%]"
                        style={{
                          background: isUser ? "var(--amber-glow)" : "var(--bg-card)",
                          border: `1px solid ${isUser ? "var(--amber-border)" : "var(--border)"}`,
                          fontFamily: "Inter, sans-serif",
                          fontSize: "13px",
                          lineHeight: 1.65,
                          color: "var(--text-primary)",
                        }}
                      >
                        {isUser ? (
                          <p>{msg.content}</p>
                        ) : (
                          <div className="prose prose-sm" style={{ maxWidth: "none" }}>
                            <ReactMarkdown
                              components={{
                                p: ({ children }) => <p style={{ marginBottom: 8, color: "var(--text-primary)" }}>{children}</p>,
                                strong: ({ children }) => <strong style={{ color: "var(--amber)", fontWeight: 700 }}>{children}</strong>,
                                ul: ({ children }) => <ul style={{ paddingLeft: 16, marginBottom: 8 }}>{children}</ul>,
                                li: ({ children }) => <li style={{ color: "var(--text-secondary)", marginBottom: 2 }}>{children}</li>,
                                code: ({ children }) => <code style={{ background: "var(--bg-void)", color: "var(--buy)", padding: "2px 4px", fontFamily: "'Space Mono', monospace", fontSize: "11px" }}>{children}</code>,
                              }}
                            >
                              {msg.content}
                            </ReactMarkdown>
                          </div>
                        )}
                      </div>
                    </motion.div>
                  );
                })}
              </AnimatePresence>

              {/* Typing indicator */}
              {isTyping && (
                <motion.div
                  initial={{ opacity: 0, y: 10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="flex gap-3"
                >
                  <div className="w-7 h-7 rounded shrink-0 flex items-center justify-center"
                    style={{ background: "var(--violet-dim)", border: "1px solid var(--violet-border)" }}>
                    <Bot size={13} style={{ color: "var(--violet)" }} />
                  </div>
                  <div className="flex items-center gap-1.5 px-4 py-3 rounded"
                    style={{ background: "var(--bg-card)", border: "1px solid var(--border)" }}>
                    {[0, 0.15, 0.3].map((delay) => (
                      <motion.div
                        key={delay}
                        animate={{ y: [0, -4, 0] }}
                        transition={{ duration: 0.6, repeat: Infinity, delay, ease: "easeInOut" }}
                        className="w-1.5 h-1.5 rounded-full"
                        style={{ backgroundColor: "var(--violet)" }}
                      />
                    ))}
                  </div>
                </motion.div>
              )}
              <div ref={messagesEndRef} />
            </>
          )}
        </div>

        {/* Input bar */}
        {activeChatSessionId && (
          <div className="px-6 py-4 border-t shrink-0"
            style={{ borderColor: "var(--border)", backgroundColor: "var(--bg-secondary)" }}>
            <div className="flex gap-3 items-end">
              <textarea
                ref={textareaRef}
                value={input}
                onChange={(e) => setInput(e.target.value)}
                onKeyDown={handleKeyDown}
                placeholder="Ask about markets, geopolitical risks, signals... (Ctrl+Enter to send)"
                rows={1}
                className="war-input flex-1 resize-none"
                style={{
                  minHeight: 40,
                  maxHeight: 120,
                  paddingTop: 10,
                  paddingBottom: 10,
                  lineHeight: 1.5,
                }}
              />
              <motion.button
                whileTap={{ scale: 0.92 }}
                onClick={() => handleSend()}
                disabled={!input.trim() || askMutation.isPending}
                className="btn-amber shrink-0 h-10"
                style={{
                  opacity: !input.trim() || askMutation.isPending ? 0.4 : 1,
                }}
              >
                {askMutation.isPending
                  ? <Loader2 size={14} className="animate-spin" />
                  : <Send size={14} />
                }
              </motion.button>
            </div>
            <p className="section-label mt-2">Ctrl+Enter to send · AI responses use live GTI + RAG context</p>
          </div>
        )}
      </div>
    </div>
  );
}
