import { useEffect, useState } from 'react'

// Geçici iskelet ekranı. K2 (Hafta 1, görev 2.1) bunu router ve sayfalarla değiştirir.
function App() {
  const [status, setStatus] = useState('kontrol ediliyor…')

  useEffect(() => {
    fetch('/api/health')
      .then((r) => r.json())
      .then((d: { status: string }) => setStatus(d.status))
      .catch(() => setStatus('backend erişilemiyor'))
  }, [])

  return (
    <main style={{ fontFamily: 'system-ui', padding: 24 }}>
      <h1>Sanal Portföy</h1>
      <p>Backend durumu: {status}</p>
    </main>
  )
}

export default App
