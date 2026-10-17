
import { useState } from "react";
import { Link } from "react-router-dom";

export default function Register() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [confirmPassword, setConfirmPassword] = useState("");
  const [error, setError] = useState("");

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
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

    alert("Kayıt ekranı çalışıyor. Gerçek hesap oluşturma henüz bağlanmadı.");
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
            required
          />

          <label htmlFor="confirm-password">Şifre Tekrar</label>
          <input
            id="confirm-password"
            type="password"
            placeholder="Şifreni tekrar gir"
            value={confirmPassword}
            onChange={(event) => setConfirmPassword(event.target.value)}
            required
          />

          {error && <p role="alert" style={{ color: "#f87171" }}>{error}</p>}

          <button type="submit">Kayıt Ol</button>
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
