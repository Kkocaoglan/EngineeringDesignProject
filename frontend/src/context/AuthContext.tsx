import { useEffect, useState, type FC, type ReactNode } from "react";
import { api, type UserInfo } from "../api/client";
import { AuthContext } from "./authContextDef";

export const AuthProvider: FC<{ children: ReactNode }> = ({ children }) => {
  const [user, setUser] = useState<UserInfo | null>(null);
  const [loading, setLoading] = useState(true);

  // Kullanıcı oturumunu kontrol et (sayfa yenilendiğinde oturumun korunması için)
  const refreshMe = async () => {
    try {
      const data = await api.me();
      setUser(data);
    } catch {
      setUser(null);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    refreshMe();
  }, []);

  const login = async (email: string, pass: string) => {
    const data = await api.login(email, pass);
    setUser(data);
    // Bakiye ve kullanıcı detaylarını tam almak için me() çağrısı yapalım
    await refreshMe();
  };

  const register = async (email: string, pass: string) => {
    await api.register(email, pass);
  };

  const logout = async () => {
    try {
      await api.logout();
    } finally {
      setUser(null);
    }
  };

  return (
    <AuthContext.Provider
      value={{ user, loading, login, register, logout, refreshMe }}
    >
      {children}
    </AuthContext.Provider>
  );
};

export { useAuth } from "./useAuth";
