import { BrowserRouter, Link, Navigate, Route, Routes } from 'react-router-dom'
import Login from './pages/Login'
import Register from './pages/Register'
import Market from './pages/Market'
import Portfolio from './pages/Portfolio'
import History from './pages/History'

function App() {
  return (
    <BrowserRouter>
      <div style={{ background: '#111f30', padding: 8, textAlign: 'center' }}>
        Sanal bakiye — Gerçek para ve varlık yoktur — Yatırım tavsiyesi değildir. Veri kaynağı: Binance.
      </div>
      <nav style={{ display: 'flex', gap: 16, padding: 16 }}>
        <Link to="/market">Piyasa</Link>
        <Link to="/portfolio">Portföy</Link>
        <Link to="/history">Geçmiş</Link>
        <Link to="/login">Giriş</Link>
        <Link to="/register">Kayıt</Link>
      </nav>
      <main style={{ fontFamily: 'system-ui', padding: 24 }}>
        <Routes>
          <Route path="/" element={<Navigate to="/market" />} />
          <Route path="/login" element={<Login />} />
          <Route path="/register" element={<Register />} />
          <Route path="/market" element={<Market />} />
          <Route path="/portfolio" element={<Portfolio />} />
          <Route path="/history" element={<History />} />
        </Routes>
      </main>
    </BrowserRouter>
  )
}

export default App