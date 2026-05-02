import { useEffect, useState } from "react";
import { eventsApi, signalsApi } from "../../api";
import { AlertCircle, TrendingUp, ShieldAlert, Cpu, Layers } from "lucide-react";
import { useQuery } from "@tanstack/react-query";

interface RightRailProps {
  lastWsEvent: any;
}

export default function RightRail({ lastWsEvent }: RightRailProps) {
  const [feedItems, setFeedItems] = useState<any[]>([]);

  // Query events
  const { data: events } = useQuery({
    queryKey: ["right-rail-events"],
    queryFn: () => eventsApi.getEvents(0, 15),
    refetchInterval: 15000,
  });

  // Query signals
  const { data: signals } = useQuery({
    queryKey: ["right-rail-signals"],
    queryFn: () => signalsApi.getSignals(0, 5),
    refetchInterval: 20000,
  });

  // Merge feeds and format
  useEffect(() => {
    const list: any[] = [];

    // Add events
    if (events?.data) {
      events.data.forEach((ev: any) => {
        list.push({
          id: `ev-${ev.id}`,
          type: "event",
          timestamp: new Date(ev.timestamp),
          severity: ev.severity,
          title: ev.title,
          category: ev.event_type,
          tag: "EVENT",
        });
      });
    }

    // Add signals
    if (signals?.data) {
      signals.data.forEach((sig: any) => {
        list.push({
          id: `sig-${sig.id}`,
          type: "signal",
          timestamp: new Date(sig.created_at || sig.generated_time || Date.now()),
          severity: sig.signal_type === "SELL" ? 8 : sig.signal_type === "BUY" ? 6 : 4,
          title: `New Trade Signal: ${sig.signal_type} ${sig.market?.symbol || "ASSET"}`,
          category: `Conf: ${Math.round((sig.confidence || 0) * 100)}%`,
          tag: "SIGNAL",
        });
      });
    }

    // Sort by timestamp desc
    list.sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime());
    setFeedItems(list.slice(0, 25));
  }, [events, signals]);

  // Inject WebSocket events in real-time
  useEffect(() => {
    if (!lastWsEvent) return;

    const formattedWs: any = {
      id: `ws-${Date.now()}-${Math.random()}`,
      timestamp: new Date(),
    };

    if (lastWsEvent.type === "gti_update") {
      formattedWs.type = "gti";
      formattedWs.severity = lastWsEvent.score >= 60 ? 8 : lastWsEvent.score >= 35 ? 6 : 4;
      formattedWs.title = `GTI Recalculated: ${lastWsEvent.score}`;
      formattedWs.category = "System Update";
      formattedWs.tag = "GTI ALERT";
    } else if (lastWsEvent.type === "risk_update") {
      formattedWs.type = "risk";
      formattedWs.severity = 7;
      formattedWs.title = lastWsEvent.summary || "Global threat risk models updated.";
      formattedWs.category = "System Update";
      formattedWs.tag = "RISK RE-EVAL";
    } else {
      return;
    }

    setFeedItems((prev) => [formattedWs, ...prev].slice(0, 25));
  }, [lastWsEvent]);

  // Helper for colors
  const getSeverityColor = (sev: number) => {
    if (sev >= 8) return "text-risk-critical border-risk-critical/30 bg-risk-critical/5";
    if (sev >= 6) return "text-risk-high border-risk-high/30 bg-risk-high/5";
    if (sev >= 4) return "text-risk-medium border-risk-medium/30 bg-risk-medium/5";
    return "text-risk-low border-risk-low/30 bg-risk-low/5";
  };

  const getTagIcon = (tag: string) => {
    switch (tag) {
      case "EVENT": return <ShieldAlert className="w-3.5 h-3.5 text-accent-secondary" />;
      case "SIGNAL": return <TrendingUp className="w-3.5 h-3.5 text-risk-low" />;
      case "GTI ALERT": return <AlertCircle className="w-3.5 h-3.5 text-risk-critical" />;
      default: return <Cpu className="w-3.5 h-3.5 text-accent-primary" />;
    }
  };

  return (
    <div className="flex flex-col w-80 h-full border-l border-border-primary bg-bg-secondary select-none">
      <div className="flex items-center gap-2 px-5 py-4 border-b border-border-primary text-text-primary">
        <Layers className="w-4 h-4 text-accent-primary" />
        <span className="font-mono text-xs font-bold tracking-widest">INTELLIGENCE RAIL</span>
      </div>

      <div className="flex-1 overflow-y-auto p-4 space-y-3">
        {feedItems.length === 0 ? (
          <div className="text-center py-10 font-mono text-[10px] text-text-muted uppercase">
            Awaiting feeds...
          </div>
        ) : (
          feedItems.map((item) => (
            <div
              key={item.id}
              className={`p-3 border rounded text-[11px] font-mono transition-all hover:border-accent-primary/40 ${getSeverityColor(
                item.severity
              )}`}
            >
              {/* Header */}
              <div className="flex items-center justify-between mb-1.5 border-b border-border-primary/50 pb-1">
                <div className="flex items-center gap-1.5">
                  {getTagIcon(item.tag)}
                  <span className="font-bold tracking-wider uppercase text-[9px]">{item.tag}</span>
                </div>
                <span className="text-[9px] text-text-muted tabular-nums">
                  {item.timestamp.toLocaleTimeString()}
                </span>
              </div>

              {/* Title & Desc */}
              <div className="text-text-primary font-sans text-xs leading-normal font-medium mb-1">
                {item.title}
              </div>
              <div className="flex items-center justify-between text-[9px] text-text-muted">
                <span className="uppercase">{item.category}</span>
                <span>SEV: {item.severity}</span>
              </div>
            </div>
          ))
        )}
      </div>
    </div>
  );
}
