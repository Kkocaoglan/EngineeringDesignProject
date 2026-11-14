import { Link, Navigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useLanguage } from "../context/languageContextDef";

export default function Landing() {
  const { user, loading } = useAuth();
  const { lang } = useLanguage();
  const en = lang === "en";

  if (loading) {
    return (
      <div style={{ textAlign: "center", padding: "60px 20px", color: "#94a3b8", fontSize: "15px" }}>
        {en ? "Loading..." : "Yükleniyor..."}
      </div>
    );
  }

  if (user) {
    return <Navigate to="/market" replace />;
  }

  return (
    <section className="landing-page">
      <div className="landing-hero">
        <div className="landing-badge">
          <span className="landing-badge-dot" />
          {en
            ? "LIVE MARKET SIMULATOR · BINANCE DATA STREAM"
            : "CANLI PİYASA SİMÜLATÖRÜ · BİNANCE VERİ AKIŞI"}
        </div>

        {en ? (
          <h1 className="landing-title">
            Build your strategy first,<br />
            explore the market <span>risk-free.</span>
          </h1>
        ) : (
          <h1 className="landing-title">
            Önce stratejini kur,<br />
            <span>risksiz işlemle</span> piyasayı keşfet.
          </h1>
        )}

        {en ? (
          <p className="landing-subtitle">
            Trade with <strong>10,000 USDT</strong> virtual balance using real-time crypto
            exchange prices. Manage your portfolio, analyze candlestick charts, and track your
            trade history without risking real capital.
          </p>
        ) : (
          <p className="landing-subtitle">
            Gerçek zamanlı kripto borsa fiyatlarıyla <strong>10.000 USDT</strong> sanal bakiye
            üzerinden alım-satım yapın. Gerçek para riske atmadan portföyünüzü yönetin,
            mum grafiklerini inceleyin ve işlem geçmişinizi takip edin.
          </p>
        )}

        <div className="landing-actions">
          <Link to="/register" className="landing-btn-primary">
            {en ? "Get Started" : "Hemen Başla"}
          </Link>
        </div>

        <div className="landing-stats">
          <div className="landing-stat-item">
            <span className="landing-stat-value">10,000 USDT</span>
            <span className="landing-stat-label">
              {en ? "Starting Virtual Balance" : "Başlangıç Sanal Bakiye"}
            </span>
          </div>
          <div className="landing-stat-item">
            <span className="landing-stat-value">{en ? "5 Pairs" : "5 Parite"}</span>
            <span className="landing-stat-label">
              {en ? "BTC, ETH, BNB, SOL, XRP Live Feed" : "BTC, ETH, BNB, SOL, XRP Canlı Akış"}
            </span>
          </div>
          <div className="landing-stat-item">
            <span className="landing-stat-value">%0.1</span>
            <span className="landing-stat-label">
              {en ? "Realistic Exchange Fee & Spread" : "Gerçekçi Borsa Komisyonu & Spread"}
            </span>
          </div>
        </div>
      </div>
    </section>
  );
}
