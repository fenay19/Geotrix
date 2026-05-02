import React, { useState } from "react";
import { useUIStore } from "../../store";
import { authApi } from "../../api";
import { ShieldCheck, ArrowRight, KeyRound, AtSign, Lock } from "lucide-react";
import { toast } from "sonner";
import { motion } from "framer-motion";

export default function Auth() {
  const [isLogin, setIsLogin] = useState(true);
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);

  const { setToken, setUser, setActiveTab } = useUIStore();

  const handleAuth = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!email || !password) {
      toast.error("Please enter email and password.");
      return;
    }
    setLoading(true);
    try {
      if (isLogin) {
        const params = new URLSearchParams();
        params.append("username", email);
        params.append("password", password);
        const resp = await authApi.login(params);
        setToken(resp.data.access_token);
        const me = await authApi.getMe();
        setUser(me.data);
        toast.success("Identity verified. Access granted.");
        setActiveTab("dashboard");
      } else {
        await authApi.register({ email, password });
        toast.success("Clearance established. Please authenticate.");
        setIsLogin(true);
      }
    } catch (err: any) {
      toast.error(err.response?.data?.detail || "Authentication failed.");
    } finally {
      setLoading(false);
    }
  };

  const handleGuestBypass = async () => {
    setLoading(true);
    const guestEmail = "analyst@geotrade.ai";
    const guestPass = "geotrade2026";
    try {
      const params = new URLSearchParams();
      params.append("username", guestEmail);
      params.append("password", guestPass);
      const resp = await authApi.login(params);
      setToken(resp.data.access_token);
      const me = await authApi.getMe();
      setUser(me.data);
      toast.success("Guest analyst clearance accepted.");
      setActiveTab("dashboard");
    } catch {
      try {
        await authApi.register({ email: guestEmail, password: guestPass });
        const params = new URLSearchParams();
        params.append("username", guestEmail);
        params.append("password", guestPass);
        const resp = await authApi.login(params);
        setToken(resp.data.access_token);
        const me = await authApi.getMe();
        setUser(me.data);
        toast.success("Guest analyst clearance accepted.");
        setActiveTab("dashboard");
      } catch (e: any) {
        toast.error("Security override failed.");
      }
    } finally {
      setLoading(false);
    }
  };

  return (
    <div
      className="relative flex h-full w-full items-center justify-center overflow-hidden font-sans select-none"
      style={{ background: "#07070c" }}
    >
      {/* ── Rich Ambient Background ── */}
      <div className="pointer-events-none absolute inset-0 z-0">
        {/* Primary amber glow — large and central */}
        <div
          className="absolute"
          style={{
            top: "-10%",
            left: "50%",
            transform: "translateX(-50%)",
            width: "900px",
            height: "700px",
            background: "radial-gradient(ellipse at center, rgba(234,130,0,0.18) 0%, transparent 65%)",
            filter: "blur(40px)",
          }}
        />
        {/* Secondary deep-blue bottom glow */}
        <div
          className="absolute"
          style={{
            bottom: "-5%",
            right: "-5%",
            width: "700px",
            height: "500px",
            background: "radial-gradient(ellipse at center, rgba(59,80,200,0.14) 0%, transparent 60%)",
            filter: "blur(50px)",
          }}
        />
        {/* Subtle bottom-left accent */}
        <div
          className="absolute"
          style={{
            bottom: "10%",
            left: "-3%",
            width: "400px",
            height: "350px",
            background: "radial-gradient(ellipse at center, rgba(180,60,0,0.10) 0%, transparent 65%)",
            filter: "blur(60px)",
          }}
        />
        {/* Fine grid overlay */}
        <div
          className="absolute inset-0"
          style={{
            opacity: 0.035,
            backgroundImage:
              "linear-gradient(rgba(255,255,255,1) 1px, transparent 1px), linear-gradient(90deg, rgba(255,255,255,1) 1px, transparent 1px)",
            backgroundSize: "32px 32px",
            maskImage: "radial-gradient(ellipse 80% 70% at 50% 40%, black 30%, transparent 80%)",
            WebkitMaskImage: "radial-gradient(ellipse 80% 70% at 50% 40%, black 30%, transparent 80%)",
          }}
        />
      </div>

      {/* ── Glass Card ── */}
      <motion.div
        initial={{ opacity: 0, y: 24, scale: 0.97 }}
        animate={{ opacity: 1, y: 0, scale: 1 }}
        transition={{ duration: 0.8, ease: [0.16, 1, 0.3, 1] }}
        className="relative z-10 w-full px-6"
        style={{ maxWidth: "520px" }}
      >
        <div
          className="w-full rounded-[28px] px-12 py-12"
          style={{
            background:
              "linear-gradient(160deg, rgba(255,255,255,0.07) 0%, rgba(255,255,255,0.03) 100%)",
            backdropFilter: "blur(48px)",
            WebkitBackdropFilter: "blur(48px)",
            border: "1px solid rgba(255,255,255,0.10)",
            boxShadow:
              "0 40px 80px -20px rgba(0,0,0,0.85), 0 0 0 0.5px rgba(255,255,255,0.06) inset, 0 1px 0 rgba(255,255,255,0.12) inset",
          }}
        >
          {/* ── Logo / Icon ── */}
          <div className="mb-8 flex justify-center">
            <div
              className="relative flex h-[68px] w-[68px] items-center justify-center rounded-[18px]"
              style={{
                background:
                  "linear-gradient(145deg, rgba(234,130,0,0.22) 0%, rgba(234,130,0,0.06) 100%)",
                border: "1px solid rgba(234,130,0,0.35)",
                boxShadow: "0 8px 32px rgba(234,130,0,0.20), 0 0 0 6px rgba(234,130,0,0.06)",
              }}
            >
              <ShieldCheck className="h-7 w-7 text-amber-400" strokeWidth={1.75} />
            </div>
          </div>

          {/* ── Heading ── */}
          <div className="mb-8 text-center">
            <h1 className="mb-2 text-[28px] font-semibold tracking-[-0.5px] text-white">
              {isLogin ? "System Access" : "Create Identity"}
            </h1>
            <p className="flex items-center justify-center gap-2 font-mono text-[11px] uppercase tracking-[0.2em] text-amber-500/80">
              <span
                className="inline-block h-[7px] w-[7px] rounded-full bg-emerald-400"
                style={{
                  animation: "pulse 2s cubic-bezier(0.4,0,0.6,1) infinite",
                  boxShadow: "0 0 8px #34d399",
                }}
              />
              GeoTrade AI · Secure Terminal
            </p>
          </div>

          {/* ── Tab Switcher ── */}
          <div
            className="mb-7 flex gap-1.5 rounded-[14px] p-1.5"
            style={{
              background: "rgba(255,255,255,0.05)",
              border: "1px solid rgba(255,255,255,0.08)",
            }}
          >
            {["Sign In", "Register"].map((label) => {
              const active = (label === "Sign In") === isLogin;
              return (
                <button
                  key={label}
                  onClick={() => setIsLogin(label === "Sign In")}
                  className="flex-1 rounded-[10px] py-2.5 text-[13px] font-medium tracking-[0.02em] transition-all duration-200"
                  style={
                    active
                      ? {
                          background:
                            "linear-gradient(135deg, rgba(234,130,0,0.22) 0%, rgba(234,130,0,0.12) 100%)",
                          border: "1px solid rgba(234,130,0,0.4)",
                          color: "#f59e0b",
                        }
                      : { color: "rgba(255,255,255,0.38)", border: "1px solid transparent" }
                  }
                >
                  {label}
                </button>
              );
            })}
          </div>

          {/* ── Form ── */}
          <form onSubmit={handleAuth} className="space-y-4">
            {/* Email */}
            <FieldInput
              icon={<AtSign className="h-[18px] w-[18px]" />}
              type="email"
              placeholder="analyst@geotrade.ai"
              value={email}
              onChange={setEmail}
            />

            {/* Password */}
            <FieldInput
              icon={<Lock className="h-[18px] w-[18px]" />}
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={setPassword}
            />

            {/* Submit */}
            <button
              type="submit"
              disabled={loading}
              className="group relative mt-2 flex w-full items-center justify-center gap-2.5 overflow-hidden rounded-[14px] py-[14px] text-[13px] font-semibold uppercase tracking-[0.1em] text-black transition-all duration-300 disabled:cursor-not-allowed disabled:opacity-60"
              style={{
                background: "linear-gradient(135deg, #d97706 0%, #f59e0b 50%, #fbbf24 100%)",
                boxShadow: "0 8px 28px rgba(245,158,11,0.35), 0 2px 8px rgba(245,158,11,0.2)",
              }}
              onMouseEnter={(e) => {
                if (!loading) {
                  (e.currentTarget as HTMLButtonElement).style.boxShadow =
                    "0 12px 36px rgba(245,158,11,0.50), 0 4px 12px rgba(245,158,11,0.3)";
                  (e.currentTarget as HTMLButtonElement).style.transform = "translateY(-1px)";
                }
              }}
              onMouseLeave={(e) => {
                (e.currentTarget as HTMLButtonElement).style.boxShadow =
                  "0 8px 28px rgba(245,158,11,0.35), 0 2px 8px rgba(245,158,11,0.2)";
                (e.currentTarget as HTMLButtonElement).style.transform = "translateY(0)";
              }}
            >
              {loading ? (
                <>
                  <span className="h-4 w-4 animate-spin rounded-full border-2 border-black/20 border-t-black" />
                  Verifying…
                </>
              ) : (
                <>
                  {isLogin ? "Authorize Connection" : "Establish Clearance"}
                  <ArrowRight
                    className="h-4 w-4 transition-transform duration-200 group-hover:translate-x-1"
                    strokeWidth={2.5}
                  />
                </>
              )}
            </button>
          </form>

          {/* ── Divider ── */}
          <div className="my-6 flex items-center gap-4">
            <div className="h-px flex-1" style={{ background: "rgba(255,255,255,0.09)" }} />
            <span className="font-mono text-[10px] uppercase tracking-[0.18em] text-white/25">
              or
            </span>
            <div className="h-px flex-1" style={{ background: "rgba(255,255,255,0.09)" }} />
          </div>

          {/* ── Guest Bypass ── */}
          <button
            onClick={handleGuestBypass}
            disabled={loading}
            className="flex w-full items-center justify-center gap-2.5 rounded-[14px] py-[13px] text-[13px] font-medium text-white/55 transition-all duration-200 disabled:opacity-60"
            style={{
              background: "rgba(255,255,255,0.04)",
              border: "1px solid rgba(255,255,255,0.09)",
            }}
            onMouseEnter={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.08)";
              (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(255,255,255,0.18)";
              (e.currentTarget as HTMLButtonElement).style.color = "rgba(255,255,255,0.85)";
            }}
            onMouseLeave={(e) => {
              (e.currentTarget as HTMLButtonElement).style.background = "rgba(255,255,255,0.04)";
              (e.currentTarget as HTMLButtonElement).style.borderColor = "rgba(255,255,255,0.09)";
              (e.currentTarget as HTMLButtonElement).style.color = "rgba(255,255,255,0.55)";
            }}
          >
            <KeyRound className="h-4 w-4 text-white/35" strokeWidth={1.75} />
            Use Guest Access
          </button>

          {/* ── Footer Link ── */}
          <div className="mt-7 text-center">
            <button
              onClick={() => setIsLogin(!isLogin)}
              className="text-[12.5px] font-medium text-white/35 transition-colors duration-200 hover:text-white/70"
            >
              {isLogin
                ? "Don't have an account? Create one →"
                : "Already registered? Sign in →"}
            </button>
          </div>
        </div>
      </motion.div>

      {/* ── Footer ── */}
      <p className="pointer-events-none absolute bottom-6 z-0 w-full text-center font-mono text-[10px] uppercase tracking-[0.18em] text-white/18">
        GeoTrade AI Terminal · Encrypted Connection · Unauthorized Access Monitored
      </p>
    </div>
  );
}

/* ── Reusable Field Input ── */
function FieldInput({
  icon,
  type,
  placeholder,
  value,
  onChange,
}: {
  icon: React.ReactNode;
  type: string;
  placeholder: string;
  value: string;
  onChange: (v: string) => void;
}) {
  return (
    <div
      className="group flex h-[54px] items-center gap-3 rounded-[14px] px-4 transition-all duration-200"
      style={{
        background: "rgba(255,255,255,0.05)",
        border: "1px solid rgba(255,255,255,0.09)",
      }}
      onFocusCapture={(e) => {
        (e.currentTarget as HTMLDivElement).style.background = "rgba(255,255,255,0.08)";
        (e.currentTarget as HTMLDivElement).style.borderColor = "rgba(234,130,0,0.55)";
        (e.currentTarget as HTMLDivElement).style.boxShadow = "0 0 0 3px rgba(234,130,0,0.08)";
      }}
      onBlurCapture={(e) => {
        (e.currentTarget as HTMLDivElement).style.background = "rgba(255,255,255,0.05)";
        (e.currentTarget as HTMLDivElement).style.borderColor = "rgba(255,255,255,0.09)";
        (e.currentTarget as HTMLDivElement).style.boxShadow = "none";
      }}
    >
      <span className="text-white/30 transition-colors duration-200 group-focus-within:text-amber-400">
        {icon}
      </span>
      <input
        type={type}
        required
        value={value}
        onChange={(e) => onChange(e.target.value)}
        placeholder={placeholder}
        className="flex-1 bg-transparent text-[14px] outline-none placeholder-white/25"
        style={{ color: "rgba(255,255,255,0.88)" }}
      />
    </div>
  );
}