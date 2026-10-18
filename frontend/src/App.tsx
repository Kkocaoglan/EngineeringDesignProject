import { BrowserRouter, Navigate, Route, Routes } from "react-router-dom";
import { AuthProvider } from "./context/AuthContext";
import { Navbar } from "./components/Navbar";
import { ProtectedRoute } from "./components/ProtectedRoute";
import Login from "./pages/Login";
import Register from "./pages/Register";
import Market from "./pages/Market";
import Portfolio from "./pages/Portfolio";
import History from "./pages/History";

export default function App() {
  return (
    <BrowserRouter>
      <AuthProvider>
        <div style={{ minHeight: "100vh", display: "flex", flexDirection: "column", background: "#0b1120", color: "#f8fafc" }}>
          <Navbar />
          <main style={{ flex: 1 }}>
            <Routes>
              {/* Korumalı Sayfalar (Oturum açılmadıysa /login'e yönlendirir) */}
              <Route element={<ProtectedRoute />}>
                <Route path="/" element={<Navigate to="/market" replace />} />
                <Route path="/market" element={<Market />} />
                <Route path="/portfolio" element={<Portfolio />} />
                <Route path="/history" element={<History />} />
              </Route>

              {/* Açık Rotalar */}
              <Route path="/login" element={<Login />} />
              <Route path="/register" element={<Register />} />

              {/* Bilinmeyen adresler */}
              <Route path="*" element={<Navigate to="/market" replace />} />
            </Routes>
          </main>
        </div>
      </AuthProvider>
    </BrowserRouter>
  );
}