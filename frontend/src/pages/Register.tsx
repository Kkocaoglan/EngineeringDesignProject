import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { ApiError } from "../api/client";

export default function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const { register, login } = useAuth();
  const navigate = useNavigate();

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (password.length < 8) {
      setError("Şifre en az 8 karakter olmalıdır.");
      return;
    }

    if (password !== confirmPassword) {
      setError("Şifreler birbiriyle eşleşmiyor.");
      return;
    }

    setLoading(true);

    try {
      // 1. Kayıt ol
      await register(email, password);
      // 2. Otomatik giriş yap ve markete yönlendir
      await login(email, password);
      navigate("/market");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError("Kayıt olunurken bir hata oluştu. Lütfen tekrar deneyin.");
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <div className="login-logo">SP</div>

        <h1>Hesap Oluştur</h1>
        <p className="login-subtitle">
          Sanal Portföy'e katıl ve piyasayı takip et.
        </p>

        <form onSubmit={handleSubmit}>
          <label htmlFor="register-email">E-posta</label>
          <input
            id="register-email"
            type="email"
            placeholder="ornek@mail.com"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            disabled={loading}
            required
          />

          <label htmlFor="register-password">Şifre</label>
          <input
            id="register-password"
            type="password"
            placeholder="En az 8 karakter"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            minLength={8}
            disabled={loading}
            required
          />

          <label htmlFor="confirm-password">Şifre Tekrar</label>
          <input
            id="confirm-password"
            type="password"
            placeholder="Şifreni tekrar gir"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            disabled={loading}
            required
          />

          {error && (
            <p role="alert" style={{ color: "#f87171", margin: "4px 0", fontSize: "14px" }}>
              {error}
            </p>
          )}

          <button type="submit" disabled={loading}>
            {loading ? "Kayıt olunuyor..." : "Kayıt Ol"}
          </button>
        </form>

        <p className="login-footer">
          Zaten hesabın var mı? <Link to="/login">Giriş Yap</Link>
        </p>

        <p className="login-warning">
          Sanal bakiye — gerçek para ve varlık yoktur.
          Yatırım tavsiyesi değildir.
        </p>
      </section>
    </main>
  );
}
