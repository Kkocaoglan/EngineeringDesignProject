
import { useState } from "react";
import { Link } from "react-router-dom";
export default function Login() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");

  function handleSubmit(event: React.FormEvent<HTMLFormElement>) {
    event.preventDefault();
    alert("Giriş ekranı hazır. Backend bağlantısı sonraki adımda eklenecek.");
  }

  return (
    <main className="login-page">
      <section className="login-card">
        <div className="login-logo">SP</div>

        <h1>Sanal Portföy</h1>
        <p className="login-subtitle">
          Hesabına giriş yap ve piyasayı takip et.
        </p>

        <form onSubmit={handleSubmit}>
          <label htmlFor="email">E-posta</label>
          <input
            id="email"
            type="email"
            placeholder="ornek@mail.com"
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            required
          />

          <label htmlFor="password">Şifre</label>
          <input
            id="password"
            type="password"
            placeholder="Şifreni gir"
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            required
          />

          <button type="submit">Giriş Yap</button>
        </form>

        <p className="login-footer">
         Hesabın yok mu? <Link to="/register">Kayıt Ol</Link>
        </p>

        <p className="login-warning">
          Sanal bakiye — gerçek para ve varlık yoktur.
          Yatırım tavsiyesi değildir.
        </p>
      </section>
    </main>
  );
}
