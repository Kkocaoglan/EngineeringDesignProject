import { createContext } from "react";
import type { UserInfo } from "../api/client";

export interface AuthContextType {
  user: UserInfo | null;
  loading: boolean;
  login: (email: string, pass: string) => Promise<void>;
  register: (email: string, pass: string) => Promise<void>;
  logout: () => Promise<void>;
  refreshMe: () => Promise<void>;
}

export const AuthContext = createContext<AuthContextType | undefined>(undefined);
