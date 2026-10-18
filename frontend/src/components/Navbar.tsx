import type { FC } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
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
  const navigate = useNavigate();

  const handleLogout = async () => {
    await logout();
    navigate("/login");
  };

  return (
    <header style={{ background: "#151e30", borderBottom: "1px solid #293449" }}>
      {/* Sabit uyarı bandı (Rehber Şartı) */}
      <div
        style={{
          background: "#080e1a",
          color: "#94a3b8",
          padding: "6px 12px",
          textAlign: "center",
          fontSize: "12px",
          borderBottom: "1px solid #1e293b",
        }}
      >
        Sanal bakiye — Gerçek para ve varlık yoktur — Yatırım tavsiyesi değildir. Veri kaynağı: Binance.
      </div>

      <nav
        style={{
          display: "flex",
          justifyContent: "space-between",
          alignItems: "center",
          padding: "12px 24px",
          color: "#f8fafc",
          maxWidth: "1200px",
          margin: "0 auto",
        }}
      >
        <div style={{ display: "flex", alignItems: "center", gap: "24px" }}>
          <Link
            to={user ? "/market" : "/login"}
            style={{
              textDecoration: "none",
              color: "#38bdf8",
              fontWeight: "bold",
              fontSize: "18px",
              display: "flex",
              alignItems: "center",
              gap: "8px",
            }}
          >
            <span
              style={{
                background: "#38bdf8",
                color: "#0b1120",
                padding: "2px 8px",
                borderRadius: "6px",
                fontSize: "14px",
              }}
            >
              SP
            </span>
            Sanal Portföy
          </Link>

          {user && (
            <div style={{ display: "flex", gap: "16px" }}>
              <Link
                to="/market"
                style={{ color: "#e2e8f0", textDecoration: "none", fontWeight: 500 }}
              >
                Piyasa
              </Link>
              <Link
                to="/portfolio"
                style={{ color: "#e2e8f0", textDecoration: "none", fontWeight: 500 }}
              >
                Portföy
              </Link>
              <Link
                to="/history"
                style={{ color: "#e2e8f0", textDecoration: "none", fontWeight: 500 }}
              >
                Geçmiş
              </Link>
            </div>
          )}
        </div>

        <div style={{ display: "flex", alignItems: "center", gap: "16px" }}>
          {user ? (
            <>
              <div style={{ textAlign: "right", fontSize: "13px" }}>
                <span style={{ color: "#94a3b8", marginRight: "8px" }}>{user.email}</span>
                <strong style={{ color: "#38bdf8" }}>{formatCash(user.cash)} USDT</strong>
              </div>
              <button
                onClick={handleLogout}
                style={{
                  background: "#293449",
                  color: "#f8fafc",
                  border: "none",
                  padding: "6px 12px",
                  borderRadius: "6px",
                  cursor: "pointer",
                  fontSize: "13px",
                }}
              >
                Çıkış Yap
              </button>
            </>
          ) : (
            <div style={{ display: "flex", gap: "12px" }}>
              <Link
                to="/login"
                style={{
                  color: "#38bdf8",
                  textDecoration: "none",
                  padding: "6px 12px",
                  fontSize: "14px",
                }}
              >
                Giriş Yap
              </Link>
              <Link
                to="/register"
                style={{
                  background: "#38bdf8",
                  color: "#0b1120",
                  textDecoration: "none",
                  padding: "6px 14px",
                  borderRadius: "6px",
                  fontWeight: "bold",
                  fontSize: "14px",
                }}
              >
                Kayıt Ol
              </Link>
            </div>
          )}
        </div>
      </nav>
    </header>
  );
};
