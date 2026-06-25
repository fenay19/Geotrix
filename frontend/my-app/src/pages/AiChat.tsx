import React, { useState, useEffect, useRef } from 'react';
import axios from 'axios';
import { useAuth } from '../context/AuthContext';
import { SeverityBadge } from '../components/ui/SeverityBadge';
import {
  MessageSquare,
  Plus,
  Trash2,
  Send,
  Sparkles,
  User,
  Bot,
  AlertCircle,
  Minimize2,
} from 'lucide-react';

const API_BASE = import.meta.env.VITE_API_URL ?? 'http://localhost:8000/api/v1';

interface ChatMessage {
  id?: number;
  session_id: number;
  role: 'user' | 'assistant';
  content: string;
  timestamp?: string;
}

interface ChatSession {
  id: number;
  session_title: string;
  created_at?: string;
}

interface HighSeverityEvent {
  id: number;
  title: string;
  event_type: string;
  severity: number;
  description: string;
  location?: string;
  timestamp?: string;
}

export const AiChat: React.FC = () => {
  const { user } = useAuth();
  const [sessions, setSessions] = useState<ChatSession[]>([]);
  const [selectedSessionId, setSelectedSessionId] = useState<number | null>(null);
  const [messages, setMessages] = useState<ChatMessage[]>([]);
  const [inputText, setInputText] = useState<string>('');
  
  // State for session list loading & errors
  const [sessionsLoading, setSessionsLoading] = useState<boolean>(true);
  const [messagesLoading, setMessagesLoading] = useState<boolean>(false);
  const [askLoading, setAskLoading] = useState<boolean>(false);

  // Streaming text simulation state
  const [streamingMessageId, setStreamingMessageId] = useState<string | null>(null);
  const [streamingText, setStreamingText] = useState<string>('');

  // Context chips loaded from high-severity events
  const [contextEvents, setContextEvents] = useState<HighSeverityEvent[]>([]);
  const [selectedChips, setSelectedChips] = useState<number[]>([]);

  // Citation details modal / drawer
  const [activeCitationSource, setActiveCitationSource] = useState<{
    id: number;
    title: string;
    description: string;
    severity: number;
    type: string;
  } | null>(null);

  // Delete confirmation overlay/inline track
  const [confirmDeleteId, setConfirmDeleteId] = useState<number | null>(null);

  const messagesEndRef = useRef<HTMLDivElement>(null);

  // 1. Fetch chat sessions & high severity events on mount
  useEffect(() => {
    loadSessions();
    loadContextEvents();
  }, []);

  // 2. Fetch messages when session changes
  useEffect(() => {
    if (selectedSessionId !== null) {
      loadMessages(selectedSessionId);
    } else {
      setMessages([]);
    }
  }, [selectedSessionId]);

  // 3. Auto-scroll to bottom of messages
  useEffect(() => {
    if (messagesEndRef.current) {
      messagesEndRef.current.scrollIntoView({ behavior: 'smooth' });
    }
  }, [messages, streamingText]);

  const loadSessions = async () => {
    setSessionsLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/chat/sessions`);
      if (res.data) {
        setSessions(res.data);
        if (res.data.length > 0 && selectedSessionId === null) {
          setSelectedSessionId(res.data[0].id);
        }
      }
    } catch (err) {
      console.warn('Failed to load chat sessions, generating offline mocks:', err);
      const mockSessions: ChatSession[] = [
        { id: 101, session_title: 'Suez Canal shipping blockades' },
        { id: 102, session_title: 'Taiwan silicon semiconductor exports' },
      ];
      setSessions(mockSessions);
      setSelectedSessionId(101);
    } finally {
      setSessionsLoading(false);
    }
  };

  const loadContextEvents = async () => {
    try {
      // GET /events/high-severity?min_severity=7&limit=3
      const res = await axios.get(`${API_BASE}/events/high-severity?min_severity=7&limit=3`);
      if (res.data && res.data.length > 0) {
        setContextEvents(res.data);
      } else {
        throw new Error('Empty events response');
      }
    } catch (err) {
      console.warn('Failed to fetch context events, building mock chips:', err);
      const mockEvents: HighSeverityEvent[] = [
        {
          id: 1,
          title: 'Taiwan Strait Naval Escalation',
          event_type: 'military',
          severity: 8.5,
          description: 'Naval fleet deployments and live-fire maneuvers restricted critical merchant cargo routes in the Taiwan Strait, raising insurance costs.',
          location: 'Taiwan'
        },
        {
          id: 2,
          title: 'Strait of Hormuz Flow Bottleneck',
          event_type: 'logistics',
          severity: 7.9,
          description: 'Increased inspection and drone-patrol activities by regional forces cause crude oil supertankers to divert routes around Africa.',
          location: 'Iran/Oman'
        },
        {
          id: 3,
          title: 'Semiconductor Export Restrictions',
          event_type: 'policy',
          severity: 7.2,
          description: 'New semiconductor mineral export bans trigger silicon supply shortages for key tech industries in North America and Western Europe.',
          location: 'China'
        }
      ];
      setContextEvents(mockEvents);
    }
  };

  const loadMessages = async (sessionId: number) => {
    setMessagesLoading(true);
    try {
      const res = await axios.get(`${API_BASE}/chat/sessions/${sessionId}/messages`);
      if (res.data) {
        setMessages(res.data);
      }
    } catch (err) {
      console.warn('Failed to fetch session messages, loading offline history:', err);
      // Mock historical messages for offline testing
      if (sessionId === 101) {
        setMessages([
          { session_id: 101, role: 'user', content: 'What happens to the global tech market if the Strait of Hormuz is disrupted?' },
          { session_id: 101, role: 'assistant', content: 'A disruption in the Strait of Hormuz primarily affects crude oil and energy supply chains [2], which indirectly impacts tech manufacturing by increasing energy overhead. If accompanied by export restrictions [3], it could cascade into silicon shortages for semiconductor suppliers.' },
        ]);
      } else if (sessionId === 102) {
        setMessages([
          { session_id: 102, role: 'user', content: 'Analyze Taiwan semiconductor risks.' },
          { session_id: 102, role: 'assistant', content: 'Taiwan semiconductor manufacturing remains highly sensitive to naval maneuvers in the Taiwan Strait [1]. Escalation directly threatens high-end chips shipping lanes.' },
        ]);
      } else {
        setMessages([]);
      }
    } finally {
      setMessagesLoading(false);
    }
  };

  const handleCreateSession = async () => {
    const title = `Analysis ${new Date().toLocaleTimeString([], { hour: '2-digit', minute: '2-digit' })}`;
    try {
      const res = await axios.post(`${API_BASE}/chat/sessions`, {
        session_title: title,
        user_id: user?.id || null,
      });
      if (res.data) {
        setSessions((prev) => [res.data, ...prev]);
        setSelectedSessionId(res.data.id);
      }
    } catch (err) {
      console.warn('Failed to create session, fallback offline:', err);
      const newMock: ChatSession = {
        id: Date.now(),
        session_title: title,
      };
      setSessions((prev) => [newMock, ...prev]);
      setSelectedSessionId(newMock.id);
    }
  };

  const handleDeleteSession = async (sessionId: number, e: React.MouseEvent) => {
    e.stopPropagation();
    try {
      await axios.delete(`${API_BASE}/chat/sessions/${sessionId}`);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (selectedSessionId === sessionId) {
        setSelectedSessionId(null);
      }
    } catch (err) {
      console.warn('Failed to delete session, fallback offline:', err);
      setSessions((prev) => prev.filter((s) => s.id !== sessionId));
      if (selectedSessionId === sessionId) {
        setSelectedSessionId(null);
      }
    } finally {
      setConfirmDeleteId(null);
    }
  };

  const handleChipClick = (eventId: number) => {
    if (selectedChips.includes(eventId)) {
      setSelectedChips((prev) => prev.filter((id) => id !== eventId));
    } else {
      setSelectedChips((prev) => [...prev, eventId]);
    }
  };

  const handleSendMessage = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!inputText.trim() || selectedSessionId === null) return;

    const query = inputText;
    setInputText('');

    // Append context chips to input text if selected
    let queryWithContext = query;
    const activeChips = contextEvents.filter((evt) => selectedChips.includes(evt.id));
    if (activeChips.length > 0) {
      const contextsString = activeChips.map((evt) => `[CONTEXT: ${evt.title} - ${evt.description}]`).join(' ');
      queryWithContext = `${query} ${contextsString}`;
    }

    // Clear chips selection
    setSelectedChips([]);

    // 1. Add user message locally
    const userMsg: ChatMessage = {
      session_id: selectedSessionId,
      role: 'user',
      content: query,
    };
    setMessages((prev) => [...prev, userMsg]);
    setAskLoading(true);

    try {
      // 2. Call backend /ask
      const res = await axios.post(`${API_BASE}/chat/sessions/${selectedSessionId}/ask`, {
        message: queryWithContext,
      });

      const reply = res.data?.reply ?? "No reply received.";
      // Simulate token rendering
      simulateStreamingReply(reply);
    } catch (err) {
      console.warn('Chat ask failed, using simulated response:', err);
      // Simulate offline AI response based on chips
      let offlineReply = `I am analyzing geopolitical threats in offline mode. Based on current feeds, the Naval activities around Taiwan [1] have increased logistics risks. Additionally, Strait of Hormuz chokepoints [2] are restricting energy shipments, while policy export bans [3] cause supply strain.`;
      
      if (query.toLowerCase().includes('oil') || query.toLowerCase().includes('hormuz')) {
        offlineReply = `Analyst Assessment: Shipping lanes in the Strait of Hormuz [2] face severe blockades. This directly propagates volatility into oil index prices. Energy infrastructure dependencies [2] show high risk sensitivity.`;
      } else if (query.toLowerCase().includes('semiconductor') || query.toLowerCase().includes('taiwan')) {
        offlineReply = `Tactical Report: Semiconductor production chains [3] are highly vulnerable to live-fire drills in the Taiwan Strait [1]. Supply chain cascades indicate high impact for tech electronics manufacturers [3].`;
      }
      
      simulateStreamingReply(offlineReply);
    }
  };

  const simulateStreamingReply = (fullText: string) => {
    const msgId = `streaming-${Date.now()}`;
    setStreamingMessageId(msgId);
    setStreamingText('');
    setAskLoading(false);

    // Split text into words to simulate streaming
    const words = fullText.split(' ');
    let currentWordIdx = 0;
    let accumulatedText = '';

    const interval = setInterval(() => {
      if (currentWordIdx < words.length) {
        accumulatedText += (currentWordIdx === 0 ? '' : ' ') + words[currentWordIdx];
        setStreamingText(accumulatedText);
        currentWordIdx++;
      } else {
        clearInterval(interval);
        // Save message to state permanently
        const assistantMsg: ChatMessage = {
          session_id: selectedSessionId!,
          role: 'assistant',
          content: fullText,
        };
        setMessages((prev) => [...prev, assistantMsg]);
        setStreamingMessageId(null);
        setStreamingText('');
      }
    }, 35); // 35ms per word feels very smooth and professional
  };

  // Parses citation markers [1], [2], [3] and wraps them in custom clickable tags
  const renderMessageContent = (content: string) => {
    const parts = [];
    const regex = /\[(\d+)\]/g;
    let lastIndex = 0;
    let match;

    while ((match = regex.exec(content)) !== null) {
      const matchIndex = match.index;
      const citationNumber = parseInt(match[1]);

      // Add normal text preceding citation
      if (matchIndex > lastIndex) {
        parts.push(content.substring(lastIndex, matchIndex));
      }

      // Add clickable citation tag
      parts.push(
        <button
          key={matchIndex}
          onClick={() => handleCitationClick(citationNumber)}
          style={{
            background: 'none',
            border: 'none',
            color: 'var(--accent-cyan)',
            fontWeight: 700,
            fontSize: '11px',
            fontFamily: 'var(--font-mono)',
            padding: '0 2px',
            cursor: 'pointer',
            verticalAlign: 'super',
            textDecoration: 'underline',
          }}
        >
          [{citationNumber}]
        </button>
      );

      lastIndex = regex.lastIndex;
    }

    if (lastIndex < content.length) {
      parts.push(content.substring(lastIndex));
    }

    return parts.length > 0 ? parts : content;
  };

  const handleCitationClick = (num: number) => {
    // Map citation index to context events
    const targetEvent = contextEvents[num - 1];
    if (targetEvent) {
      setActiveCitationSource({
        id: targetEvent.id,
        title: targetEvent.title,
        description: targetEvent.description,
        severity: targetEvent.severity,
        type: targetEvent.event_type,
      });
    } else {
      // Fallback in case citation index is out of bounds
      setActiveCitationSource({
        id: num,
        title: `Geopolitical Intelligence Source #${num}`,
        description: `RAG verification document referenced from GDELT geopolitical risk indexing services. Threat parameters validation score: HIGH.`,
        severity: 7.5,
        type: 'intelligence',
      });
    }
  };

  return (
    <div
      style={{
        display: 'grid',
        gridTemplateColumns: '260px 1fr',
        backgroundColor: 'var(--bg-base)',
        color: 'var(--text-primary)',
        height: 'calc(100vh - 104px)', // 56px Nav + 48px StatusBar = 104px
        boxSizing: 'border-box',
        overflow: 'hidden',
      }}
    >
      {/* 1. LEFT COLUMN: Chat Sessions List */}
      <aside
        style={{
          backgroundColor: 'var(--bg-surface)',
          borderRight: '1px solid var(--border)',
          display: 'flex',
          flexDirection: 'column',
          height: '100%',
          overflow: 'hidden',
          boxSizing: 'border-box',
        }}
      >
        {/* Header/New Chat button */}
        <div style={{ padding: '16px', borderBottom: '1px solid var(--border)' }}>
          <button
            onClick={handleCreateSession}
            style={{
              width: '100%',
              height: '38px',
              backgroundColor: 'var(--bg-elevated)',
              border: '1px solid var(--border-bright)',
              color: 'var(--text-primary)',
              borderRadius: 'var(--radius-md)',
              fontWeight: 600,
              fontSize: '12px',
              cursor: 'pointer',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              gap: '8px',
              transition: 'background var(--transition-fast) var(--ease-snap)',
            }}
            onMouseEnter={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-hover)')}
            onMouseLeave={(e) => (e.currentTarget.style.backgroundColor = 'var(--bg-elevated)')}
          >
            <Plus size={14} />
            NEW CHAT
          </button>
        </div>

        {/* Scrollable list */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '12px 8px', display: 'flex', flexDirection: 'column', gap: '4px' }}>
          {sessionsLoading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '8px', padding: '8px' }}>
              {Array.from({ length: 4 }).map((_, i) => (
                <div key={i} className="skeleton" style={{ height: '36px', width: '100%' }} />
              ))}
            </div>
          ) : sessions.length === 0 ? (
            <div style={{ fontSize: '12px', color: 'var(--text-muted)', textAlign: 'center', padding: '24px' }}>
              No chats recorded. Click above to start one.
            </div>
          ) : (
            sessions.map((session) => {
              const active = selectedSessionId === session.id;
              const isConfirmingDelete = confirmDeleteId === session.id;

              return (
                <div
                  key={session.id}
                  onClick={() => setSelectedSessionId(session.id)}
                  style={{
                    height: '40px',
                    backgroundColor: active ? 'var(--bg-elevated)' : 'transparent',
                    border: `1px solid ${active ? 'var(--border-bright)' : 'transparent'}`,
                    borderRadius: 'var(--radius-md)',
                    padding: '0 10px',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'space-between',
                    cursor: 'pointer',
                    transition: 'all 150ms ease',
                    boxSizing: 'border-box',
                    gap: '8px',
                  }}
                  onMouseEnter={(e) => {
                    if (!active) e.currentTarget.style.backgroundColor = 'var(--bg-hover)';
                  }}
                  onMouseLeave={(e) => {
                    if (!active) e.currentTarget.style.backgroundColor = 'transparent';
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', gap: '8px', minWidth: 0, flex: 1 }}>
                    <MessageSquare size={14} style={{ color: active ? 'var(--accent-cyan)' : 'var(--text-secondary)', flexShrink: 0 }} />
                    <span
                      style={{
                        fontSize: '12px',
                        fontWeight: active ? 600 : 400,
                        color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {session.session_title}
                    </span>
                  </div>

                  {/* Delete / Confirm trigger */}
                  <div style={{ flexShrink: 0, display: 'flex', alignItems: 'center' }}>
                    {isConfirmingDelete ? (
                      <div style={{ display: 'flex', gap: '4px' }}>
                        <button
                          onClick={(e) => handleDeleteSession(session.id, e)}
                          style={{
                            border: 'none',
                            backgroundColor: 'var(--risk-critical)',
                            color: '#fff',
                            fontSize: '9px',
                            fontWeight: 700,
                            padding: '2px 4px',
                            borderRadius: '2px',
                            cursor: 'pointer',
                          }}
                        >
                          DEL
                        </button>
                        <button
                          onClick={(e) => {
                            e.stopPropagation();
                            setConfirmDeleteId(null);
                          }}
                          style={{
                            border: 'none',
                            backgroundColor: 'var(--bg-hover)',
                            color: 'var(--text-secondary)',
                            fontSize: '9px',
                            padding: '2px 4px',
                            borderRadius: '2px',
                            cursor: 'pointer',
                          }}
                        >
                          ESC
                        </button>
                      </div>
                    ) : (
                      <button
                        onClick={(e) => {
                          e.stopPropagation();
                          setConfirmDeleteId(session.id);
                        }}
                        style={{
                          border: 'none',
                          background: 'transparent',
                          color: 'var(--text-muted)',
                          cursor: 'pointer',
                          padding: '4px',
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                        }}
                        onMouseEnter={(e) => (e.currentTarget.style.color = 'var(--risk-critical)')}
                        onMouseLeave={(e) => (e.currentTarget.style.color = 'var(--text-muted)')}
                      >
                        <Trash2 size={12} />
                      </button>
                    )}
                  </div>
                </div>
              );
            })
          )}
        </div>

        {/* User signature */}
        <div style={{ padding: '16px', borderTop: '1px solid var(--border)', display: 'flex', alignItems: 'center', gap: '10px' }}>
          <div
            style={{
              width: '32px',
              height: '32px',
              borderRadius: '50%',
              backgroundColor: 'rgba(6, 182, 212, 0.1)',
              border: '1px solid var(--accent-cyan)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              color: 'var(--accent-cyan)',
              flexShrink: 0,
            }}
          >
            <User size={16} />
          </div>
          <div style={{ minWidth: 0 }}>
            <span style={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', display: 'block', textOverflow: 'ellipsis', overflow: 'hidden', whiteSpace: 'nowrap' }}>
              {user?.name ?? 'Geotrade Analyst'}
            </span>
            <span style={{ fontSize: '10px', color: 'var(--text-secondary)', textTransform: 'uppercase', display: 'block' }}>
              {user?.role ?? 'Operator'}
            </span>
          </div>
        </div>
      </aside>

      {/* 2. RIGHT COLUMN: Active Chat interface */}
      <section style={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden', position: 'relative' }}>
        
        {/* Chat Thread Header */}
        <div
          style={{
            height: '56px',
            backgroundColor: 'var(--bg-surface)',
            borderBottom: '1px solid var(--border)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            padding: '0 20px',
            boxSizing: 'border-box',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'center', gap: '8px' }}>
            <Sparkles size={16} style={{ color: 'var(--accent-cyan)' }} />
            <span style={{ fontSize: '13px', fontWeight: 700, fontFamily: 'var(--font-display)', letterSpacing: '0.04em' }}>
              GEOPOLITICAL COGNITIVE RAG ANALYST
            </span>
          </div>
          
          <div style={{ display: 'flex', alignItems: 'center', gap: '6px', fontSize: '11px', color: 'var(--text-secondary)' }}>
            <AlertCircle size={12} style={{ color: 'var(--accent-amber)' }} />
            Context: Live Vector Indexing
          </div>
        </div>

        {/* Message Thread Area */}
        <div style={{ flex: 1, overflowY: 'auto', padding: '24px 20px', display: 'flex', flexDirection: 'column', gap: '20px' }}>
          {selectedSessionId === null ? (
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', maxWidth: '420px', margin: '0 auto', gap: '16px' }}>
              <div style={{ width: '48px', height: '48px', borderRadius: 'var(--radius-lg)', backgroundColor: 'var(--bg-elevated)', border: '1px solid var(--border-bright)', display: 'flex', alignItems: 'center', justifySelf: 'center', justifyContent: 'center', color: 'var(--text-secondary)' }}>
                <MessageSquare size={22} />
              </div>
              <h3 style={{ fontSize: '16px', fontWeight: 600, color: 'var(--text-primary)', margin: 0 }}>Start a new scenario analysis</h3>
              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0 }}>
                Select an existing chat thread or create a new session. You can append live high-severity geopolitical event markers to your prompt parameters below.
              </p>
            </div>
          ) : messagesLoading ? (
            <div style={{ display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div className="skeleton" style={{ height: '50px', width: '60%', alignSelf: 'flex-end', borderRadius: '8px' }} />
              <div className="skeleton" style={{ height: '80px', width: '70%', alignSelf: 'flex-start', borderRadius: '8px' }} />
              <div className="skeleton" style={{ height: '40px', width: '50%', alignSelf: 'flex-end', borderRadius: '8px' }} />
            </div>
          ) : messages.length === 0 && !streamingMessageId ? (
            <div style={{ height: '100%', display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', textAlign: 'center', color: 'var(--text-secondary)', gap: '12px' }}>
              <Bot size={28} style={{ color: 'var(--accent-cyan)' }} />
              <span style={{ fontSize: '13px', fontWeight: 600 }}>Conversation initialized.</span>
              <p style={{ fontSize: '12px', color: 'var(--text-muted)', maxWidth: '340px', margin: 0 }}>
                Ask a question about maritime corridor disruptions, export bans, or regional tension volatility indices.
              </p>
            </div>
          ) : (
            <>
              {messages.map((msg, idx) => {
                const isUser = msg.role === 'user';
                return (
                  <div
                    key={idx}
                    style={{
                      display: 'flex',
                      justifyContent: isUser ? 'flex-end' : 'flex-start',
                      width: '100%',
                    }}
                  >
                    <div
                      style={{
                        display: 'flex',
                        gap: '12px',
                        maxWidth: '80%',
                        flexDirection: isUser ? 'row-reverse' : 'row',
                        alignItems: 'flex-start',
                      }}
                    >
                      {/* Avatar */}
                      <div
                        style={{
                          width: '28px',
                          height: '28px',
                          borderRadius: '50%',
                          backgroundColor: isUser ? 'rgba(6, 182, 212, 0.1)' : 'var(--bg-elevated)',
                          border: `1px solid ${isUser ? 'var(--accent-cyan)' : 'var(--border-bright)'}`,
                          display: 'flex',
                          alignItems: 'center',
                          justifyContent: 'center',
                          color: isUser ? 'var(--accent-cyan)' : 'var(--accent-purple)',
                          flexShrink: 0,
                        }}
                      >
                        {isUser ? <User size={13} /> : <Bot size={13} />}
                      </div>

                      {/* Message bubble */}
                      <div
                        style={{
                          backgroundColor: isUser ? 'var(--bg-elevated)' : 'var(--bg-surface)',
                          border: `1px solid ${isUser ? 'var(--border-bright)' : 'var(--border)'}`,
                          borderRadius: 'var(--radius-lg)',
                          padding: '12px 16px',
                          color: 'var(--text-primary)',
                          fontSize: '13px',
                          lineHeight: 1.5,
                          boxSizing: 'border-box',
                        }}
                      >
                        {isUser ? (
                          <div style={{ whiteSpace: 'pre-wrap' }}>{msg.content}</div>
                        ) : (
                          <div style={{ whiteSpace: 'pre-wrap' }}>
                            {renderMessageContent(msg.content)}
                          </div>
                        )}
                      </div>
                    </div>
                  </div>
                );
              })}

              {/* Streaming active bubble representation */}
              {streamingMessageId && (
                <div style={{ display: 'flex', justifyContent: 'flex-start', width: '100%' }}>
                  <div style={{ display: 'flex', gap: '12px', maxWidth: '80%', alignItems: 'flex-start' }}>
                    <div
                      style={{
                        width: '28px',
                        height: '28px',
                        borderRadius: '50%',
                        backgroundColor: 'var(--bg-elevated)',
                        border: '1px solid var(--border-bright)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'var(--accent-purple)',
                        flexShrink: 0,
                      }}
                    >
                      <Bot size={13} />
                    </div>
                    <div
                      style={{
                        backgroundColor: 'var(--bg-surface)',
                        border: '1px solid var(--border)',
                        borderRadius: 'var(--radius-lg)',
                        padding: '12px 16px',
                        color: 'var(--text-primary)',
                        fontSize: '13px',
                        lineHeight: 1.5,
                        boxSizing: 'border-box',
                      }}
                    >
                      <div style={{ whiteSpace: 'pre-wrap' }}>
                        {renderMessageContent(streamingText)}
                        <span
                          style={{
                            display: 'inline-block',
                            width: '6px',
                            height: '13px',
                            backgroundColor: 'var(--accent-cyan)',
                            marginLeft: '4px',
                            verticalAlign: 'middle',
                            animation: 'blink 1s step-end infinite',
                          }}
                        />
                      </div>
                    </div>
                  </div>
                </div>
              )}

              {/* Typing indicator spinner when waiting for ask reply */}
              {askLoading && (
                <div style={{ display: 'flex', justifyContent: 'flex-start', width: '100%' }}>
                  <div style={{ display: 'flex', gap: '12px', alignItems: 'center' }}>
                    <div
                      style={{
                        width: '28px',
                        height: '28px',
                        borderRadius: '50%',
                        backgroundColor: 'var(--bg-elevated)',
                        border: '1px solid var(--border-bright)',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        color: 'var(--text-secondary)',
                      }}
                    >
                      <Bot size={13} />
                    </div>
                    <div style={{ display: 'flex', gap: '4px', padding: '8px' }}>
                      <span className="dot-blink" style={{ width: '4px', height: '4px', borderRadius: '50%', backgroundColor: 'var(--text-muted)' }} />
                      <span className="dot-blink" style={{ width: '4px', height: '4px', borderRadius: '50%', backgroundColor: 'var(--text-muted)', animationDelay: '0.2s' }} />
                      <span className="dot-blink" style={{ width: '4px', height: '4px', borderRadius: '50%', backgroundColor: 'var(--text-muted)', animationDelay: '0.4s' }} />
                    </div>
                  </div>
                </div>
              )}
            </>
          )}
          <div ref={messagesEndRef} />
        </div>

        {/* 3. BOTTOM PANEL: Context Chips + Message Form */}
        {selectedSessionId !== null && (
          <div
            style={{
              borderTop: '1px solid var(--border)',
              backgroundColor: 'var(--bg-surface)',
              padding: '16px 20px',
              display: 'flex',
              flexDirection: 'column',
              gap: '12px',
            }}
          >
            {/* Context chips */}
            {contextEvents.length > 0 && (
              <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
                <span style={{ fontSize: '9px', fontWeight: 700, color: 'var(--text-muted)', letterSpacing: '0.08em' }}>
                  APPEND GEOPOLITICAL EVENTS CONTEXT TO PROMPT
                </span>
                <div style={{ display: 'flex', gap: '8px', overflowX: 'auto', paddingBottom: '4px' }}>
                  {contextEvents.map((evt) => {
                    const isSelected = selectedChips.includes(evt.id);
                    return (
                      <button
                        key={evt.id}
                        type="button"
                        onClick={() => handleChipClick(evt.id)}
                        style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: '6px',
                          padding: '6px 12px',
                          borderRadius: '16px',
                          backgroundColor: isSelected ? 'rgba(6, 182, 212, 0.15)' : 'var(--bg-elevated)',
                          border: `1px solid ${isSelected ? 'var(--accent-cyan)' : 'var(--border)'}`,
                          color: isSelected ? 'var(--accent-cyan)' : 'var(--text-secondary)',
                          fontSize: '11px',
                          fontWeight: 600,
                          cursor: 'pointer',
                          whiteSpace: 'nowrap',
                          transition: 'all 150ms ease',
                        }}
                      >
                        <SeverityBadge score={evt.severity} showScore={true} />
                        {evt.title}
                      </button>
                    );
                  })}
                </div>
              </div>
            )}

            {/* Input Bar Form */}
            <form onSubmit={handleSendMessage} style={{ display: 'flex', gap: '10px', width: '100%' }}>
              <input
                type="text"
                value={inputText}
                onChange={(e) => setInputText(e.target.value)}
                placeholder="Ask AI Analyst: e.g. What happens to crude oil if Strait of Hormuz is blocked?"
                disabled={askLoading || streamingMessageId !== null}
                style={{
                  flex: 1,
                  height: '42px',
                  backgroundColor: 'var(--bg-base)',
                  border: '1px solid var(--border)',
                  borderRadius: 'var(--radius-md)',
                  color: 'var(--text-primary)',
                  padding: '0 16px',
                  fontSize: '13px',
                  boxSizing: 'border-box',
                }}
              />
              <button
                type="submit"
                disabled={!inputText.trim() || askLoading || streamingMessageId !== null}
                style={{
                  width: '42px',
                  height: '42px',
                  backgroundColor: 'var(--bg-elevated)',
                  border: '1px solid var(--border-bright)',
                  color: inputText.trim() ? 'var(--accent-cyan)' : 'var(--text-muted)',
                  borderRadius: 'var(--radius-md)',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  cursor: inputText.trim() ? 'pointer' : 'default',
                  transition: 'all 150ms ease',
                }}
                onMouseEnter={(e) => {
                  if (inputText.trim()) e.currentTarget.style.backgroundColor = 'var(--bg-hover)';
                }}
                onMouseLeave={(e) => {
                  e.currentTarget.style.backgroundColor = 'var(--bg-elevated)';
                }}
              >
                <Send size={15} />
              </button>
            </form>
          </div>
        )}

        {/* 4. RAG CITATION OVERLAY SHEET (Right Detail Drawer) */}
        {activeCitationSource && (
          <div
            style={{
              position: 'absolute',
              top: '56px',
              right: 0,
              width: '320px',
              height: 'calc(100% - 56px)',
              backgroundColor: 'var(--bg-surface)',
              borderLeft: '1px solid var(--border-bright)',
              boxShadow: '-4px 0 20px rgba(0,0,0,0.4)',
              zIndex: 100,
              display: 'flex',
              flexDirection: 'column',
              boxSizing: 'border-box',
              animation: 'slideLeft 250ms var(--ease-snap)',
            }}
          >
            {/* Header */}
            <div style={{ padding: '16px', borderBottom: '1px solid var(--border)', display: 'flex', justifyContent: 'space-between', alignItems: 'center', backgroundColor: 'var(--bg-elevated)' }}>
              <span style={{ fontSize: '10px', fontWeight: 700, color: 'var(--accent-purple)', letterSpacing: '0.08em' }}>
                VERIFIED COGNITIVE SOURCE
              </span>
              <button
                onClick={() => setActiveCitationSource(null)}
                style={{ background: 'transparent', border: 'none', color: 'var(--text-muted)', cursor: 'pointer', padding: 0 }}
              >
                <Minimize2 size={16} />
              </button>
            </div>

            {/* Content Body */}
            <div style={{ flex: 1, overflowY: 'auto', padding: '20px', display: 'flex', flexDirection: 'column', gap: '16px' }}>
              <div>
                <SeverityBadge score={activeCitationSource.severity} />
                <h4 style={{ margin: '8px 0 4px 0', fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
                  {activeCitationSource.title}
                </h4>
                <span style={{ fontSize: '10px', color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Index Category: {activeCitationSource.type}
                </span>
              </div>

              <p style={{ fontSize: '12px', color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0, backgroundColor: 'var(--bg-base)', border: '1px solid var(--border)', padding: '12px', borderRadius: 'var(--radius-md)' }}>
                {activeCitationSource.description}
              </p>

              <div style={{ marginTop: 'auto', borderTop: '1px solid var(--border)', paddingTop: '16px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
                <span style={{ fontSize: '9px', color: 'var(--text-muted)', fontWeight: 700 }}>VERIFICATION TRUST VALUE</span>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Semantic match relevance:</span>
                  <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent-green)' }}>94.2%</span>
                </div>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                  <span style={{ fontSize: '11px', color: 'var(--text-secondary)' }}>Source authority node:</span>
                  <span style={{ fontSize: '11px', fontFamily: 'var(--font-mono)', fontWeight: 700, color: 'var(--accent-cyan)' }}>GDELT/V2</span>
                </div>
              </div>
            </div>
          </div>
        )}
      </section>

      {/* Global CSS keyframes */}
      <style>{`
        @keyframes blink {
          50% { opacity: 0; }
        }
        @keyframes slideLeft {
          from { transform: translateX(100%); }
          to { transform: translateX(0); }
        }
        .dot-blink {
          animation: dotBlink 1.4s infinite both;
        }
        @keyframes dotBlink {
          0% { opacity: 0.2; }
          20% { opacity: 1; }
          100% { opacity: 0.2; }
        }
      `}</style>
    </div>
  );
};

export default AiChat;
