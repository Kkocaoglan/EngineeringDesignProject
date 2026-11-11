import type { FC } from "react";
import { Link, useLocation, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useLanguage } from "../context/languageContextDef";
import { useReplayMode } from "../hooks/useLiveStream";
import Decimal from "decimal.js";

function formatCash(val?: string) {
  if (!val) return "—";
  try {
    return new Decimal(val).toFixed(2);
  } catch {
    return val;
  }
}

export const Navbar: FC = () => {
  const { user, logout } = useAuth();
  const { lang, setLang } = useLanguage();
  const isReplay = useReplayMode();
  const navigate = useNavigate();
  const location = useLocation();
  const en = lang === "en";

  const handleLogout = async () => {
    await logout();
    navigate("/");
  };

  const navLinkStyle = (path: string) => {
    const active = location.pathname === path;
    return {
      color: active ? "#38bdf8" : "#cbd5e1",
      background: active ? "rgba(56, 189, 248, 0.12)" : "transparent",
      border: active ? "1px solid rgba(56, 189, 248, 0.25)" : "1px solid transparent",
      textDecoration: "none",
      fontWeight: active ? 600 : 500,
      fontSize: "15px",
      padding: "7px 16px",
      borderRadius: "8px",
      transition: "all 0.15s ease",
      letterSpacing: "-0.01em",
    } as const;
  };

  return (
    <header style={{ background: "#111827", borderBottom: "1px solid #1e293b" }}>
      {/* REPLAY modu sabit turuncu uyarı bandı (Rehber 2.10) */}
      {isReplay && (
        <div
          role="status"
          data-testid="replay-banner"
          style={{
            background: "#ea580c",
            color: "#ffffff",
            padding: "8px 12px",
            textAlign: "center",
            fontSize: "13px",
            fontWeight: 600,
            borderBottom: "1px solid #c2410c",
          }}
        >
          {en ? "REPLAY — recorded data, not live." : "REPLAY — kayıtlı veri, canlı değil."}
        </div>
      )}

      {/* Sabit uyarı bandı (Rehber Şartı) */}
      <div
        style={{
          background: "#080d18",
          color: "#94a3b8",
          padding: "7px 14px",
          textAlign: "center",
          fontSize: "12.5px",
          borderBottom: "1px solid #1e293b",
          letterSpacing: "0.01em",
        }}
      >
        {en
          ? "Virtual balance — No real money or assets — Not investment advice. Data source: Binance."
          : "Sanal bakiye — Gerçek para ve varlık yoktur — Yatırım tavsiyesi değildir. Veri kaynağı: Binance."}
      </div>

      <nav
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "12px 24px",
          color: "#f8fafc",
          maxWidth: "1240px",
          margin: "0 auto",
          flexWrap: "wrap",
          gap: "12px",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "28px" }}>
          <Link
            to={user ? "/market" : "/"}
            style={{
              textDecoration: "none",
              color: "#f8fafc",
              fontWeight: 700,
              fontSize: "18px",
              display: "flex",
              alignItems: "center",
              gap: "10px",
              letterSpacing: "-0.02em",
            }}
          >
            <span
              style={{
                background: "linear-gradient(135deg, #38bdf8, #0284c7)",
                color: "#0b1120",
                padding: "4px 9px",
                borderRadius: "8px",
                fontSize: "13px",
                fontWeight: 800,
                letterSpacing: "0.02em",
              }}
            >
              SP
            </span>
            {en ? "Virtual Portfolio" : "Sanal Portföy"}
          </Link>

          {user && (
            <div style={{ display: "flex", gap: "6px", alignItems: "center" }}>
              <Link to="/market" style={navLinkStyle("/market")}>
                {en ? "Markets" : "Piyasa"}
              </Link>
              <Link to="/portfolio" style={navLinkStyle("/portfolio")}>
                {en ? "Portfolio" : "Portföy"}
              </Link>
              <Link to="/history" style={navLinkStyle("/history")}>
                {en ? "History" : "Geçmiş"}
              </Link>
            </div>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "12px" }}>
          {/* Dil Seçici (TR | EN) */}
          <div
            style={{
              display: "inline-flex",
              alignItems: "center",
              background: "#0f172a",
              border: "1px solid #24324a",
              borderRadius: "999px",
              padding: "2px",
            }}
          >
            <button
              type="button"
              onClick={() => setLang("tr")}
              style={{
                border: "none",
                background: !en ? "#1e293b" : "transparent",
                color: !en ? "#38bdf8" : "#64748b",
                fontWeight: 700,
                fontSize: "12px",
                padding: "4px 10px",
                borderRadius: "999px",
                cursor: "pointer",
              }}
            >
              TR
            </button>
            <button
              type="button"
              onClick={() => setLang("en")}
              style={{
                border: "none",
                background: en ? "#1e293b" : "transparent",
                color: en ? "#38bdf8" : "#64748b",
                fontWeight: 700,
                fontSize: "12px",
                padding: "4px 10px",
                borderRadius: "999px",
                cursor: "pointer",
              }}
            >
              EN
            </button>
          </div>

          {user ? (
            <>
              <div
                style={{
                  display: "flex",
                  alignItems: "center",
                  gap: "10px",
                  background: "#0f172a",
                  border: "1px solid #24324a",
                  padding: "6px 12px",
                  borderRadius: "8px",
                  fontSize: "13.5px",
                }}
              >
                <span style={{ color: "#94a3b8" }}>{user.email}</span>
                <span style={{ color: "#334155" }}>|</span>
                <strong style={{ color: "#38bdf8", fontVariantNumeric: "tabular-nums" }}>
                  {formatCash(user.cash)} USDT
                </strong>
              </div>
              <button
                onClick={handleLogout}
                style={{
                  background: "#1e293b",
                  color: "#e2e8f0",
                  border: "1px solid #334155",
                  padding: "7px 14px",
                  borderRadius: "8px",
                  cursor: "pointer",
                  fontSize: "13.5px",
                  fontWeight: 500,
                }}
              >
                {en ? "Log Out" : "Çıkış Yap"}
              </button>
            </>
          ) : (
            <div style={{ display: "flex", gap: "10px", alignItems: "center" }}>
              <Link
                to="/login"
                style={{
                  color: "#f8fafc",
                  background: "transparent",
                  border: "1px solid #475569",
                  textDecoration: "none",
                  padding: "8px 20px",
                  borderRadius: "999px",
                  fontSize: "14px",
                  fontWeight: 600,
                  letterSpacing: "-0.01em",
                }}
              >
                {en ? "Log In" : "Giriş Yap"}
              </Link>
              <Link
                to="/register"
                style={{
                  background: "linear-gradient(135deg, #00c6ff 0%, #0072ff 100%)",
                  color: "#ffffff",
                  textDecoration: "none",
                  padding: "8px 22px",
                  borderRadius: "999px",
                  fontWeight: 700,
                  fontSize: "14px",
                  letterSpacing: "-0.01em",
                  boxShadow: "0 4px 14px rgba(0, 140, 255, 0.35)",
                }}
              >
                {en ? "Sign Up" : "Kayıt Ol"}
              </Link>
            </div>
          )}
        </div>
      </nav>
    </header>
  );
};
