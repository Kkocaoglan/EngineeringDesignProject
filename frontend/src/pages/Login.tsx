import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useLanguage } from "../context/languageContextDef";
import { ApiError } from "../api/client";

export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const { login } = useAuth();
  const { lang } = useLanguage();
  const en = lang === "en";
  const navigate = useNavigate();

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");
    setLoading(true);

    try {
      await login(email, password);
      navigate("/market");
    } catch (err) {
      if (err instanceof ApiError) {
        setError(err.message);
      } else {
        setError(
          en
            ? "An error occurred while logging in. Please try again."
            : "Giriş yapılırken bir hata oluştu. Lütfen tekrar deneyin."
        );
      }
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <div className="login-logo">SP</div>

        <h1>{en ? "Virtual Portfolio" : "Sanal Portföy"}</h1>
        <p className="login-subtitle">
          {en ? "Log in to your account and track the market." : "Hesabına giriş yap ve piyasayı takip et."}
        </p>

        <form onSubmit={handleSubmit}>
          <label htmlFor="email">{en ? "Email" : "E-posta"}</label>
          <input
            id="email"
            type="email"
            placeholder={en ? "you@example.com" : "ornek@mail.com"}
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            disabled={loading}
            required
          />

          <label htmlFor="password">{en ? "Password" : "Şifre"}</label>
          <input
            id="password"
            type="password"
            placeholder={en ? "Enter your password" : "Şifreni gir"}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            disabled={loading}
            required
          />

          {error && (
            <p role="alert" style={{ color: "#f87171", margin: "4px 0", fontSize: "14px" }}>
              {error}
            </p>
          )}

          <button type="submit" disabled={loading}>
            {loading ? (en ? "Logging in..." : "Giriş yapılıyor...") : en ? "Log In" : "Giriş Yap"}
          </button>
        </form>

        <p className="login-footer">
          {en ? "Don't have an account?" : "Hesabın yok mu?"}{" "}
          <Link to="/register">{en ? "Sign Up" : "Kayıt Ol"}</Link>
        </p>

        <p className="login-warning">
          {en
            ? "Virtual balance — no real money or assets. Not investment advice."
            : "Sanal bakiye — gerçek para ve varlık yoktur. Yatırım tavsiyesi değildir."}
        </p>
      </section>
    </main>
  );
}
