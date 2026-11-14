import { useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { useAuth } from "../context/AuthContext";
import { useLanguage } from "../context/languageContextDef";
import { ApiError } from "../api/client";

export default function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const { register, login } = useAuth();
  const { lang } = useLanguage();
  const en = lang === "en";
  const navigate = useNavigate();

  async function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    setError("");

    if (password.length < 8) {
      setError(en ? "Password must be at least 8 characters." : "Şifre en az 8 karakter olmalıdır.");
      return;
    }

    if (password !== confirmPassword) {
      setError(en ? "Passwords do not match." : "Şifreler birbiriyle eşleşmiyor.");
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
        setError(
          en
            ? "An error occurred while signing up. Please try again."
            : "Kayıt olunurken bir hata oluştu. Lütfen tekrar deneyin."
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

        <h1>{en ? "Create Account" : "Hesap Oluştur"}</h1>
        <p className="login-subtitle">
          {en ? "Join Virtual Portfolio and track the market." : "Sanal Portföy'e katıl ve piyasayı takip et."}
        </p>

        <form onSubmit={handleSubmit}>
          <label htmlFor="register-email">{en ? "Email" : "E-posta"}</label>
          <input
            id="register-email"
            type="email"
            placeholder={en ? "you@example.com" : "ornek@mail.com"}
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            disabled={loading}
            required
          />

          <label htmlFor="register-password">{en ? "Password" : "Şifre"}</label>
          <input
            id="register-password"
            type="password"
            placeholder={en ? "At least 8 characters" : "En az 8 karakter"}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            minLength={8}
            disabled={loading}
            required
          />

          <label htmlFor="confirm-password">{en ? "Confirm Password" : "Şifre Tekrar"}</label>
          <input
            id="confirm-password"
            type="password"
            placeholder={en ? "Re-enter your password" : "Şifreni tekrar gir"}
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
            {loading ? (en ? "Signing up..." : "Kayıt olunuyor...") : en ? "Sign Up" : "Kayıt Ol"}
          </button>
        </form>

        <p className="login-footer">
          {en ? "Already have an account?" : "Zaten hesabın var mı?"}{" "}
          <Link to="/login">{en ? "Log In" : "Giriş Yap"}</Link>
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
