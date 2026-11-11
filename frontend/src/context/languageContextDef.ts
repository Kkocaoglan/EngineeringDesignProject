import { createContext, useContext } from "react";

export type Lang = "tr" | "en";

export interface LanguageContextType {
  lang: Lang;
  setLang: (l: Lang) => void;
  toggleLang: () => void;
}

export const LanguageContext = createContext<LanguageContextType | undefined>(undefined);

export function useLanguage(): LanguageContextType {
  const ctx = useContext(LanguageContext);
  if (!ctx) {
    return {
      lang: "tr",
      setLang: () => {},
      toggleLang: () => {},
    };
  }
  return ctx;
}
