import { useState, type FC, type ReactNode } from "react";
import { LanguageContext, type Lang } from "./languageContextDef";

export const LanguageProvider: FC<{ children: ReactNode }> = ({ children }) => {
  const [lang, setLangState] = useState<Lang>(() => {
    try {
      const saved = localStorage.getItem("sp_lang");
      return saved === "en" ? "en" : "tr";
    } catch {
      return "tr";
    }
  });

  const setLang = (next: Lang) => {
    setLangState(next);
    try {
      localStorage.setItem("sp_lang", next);
    } catch {
      /* ignore */
    }
  };

  const toggleLang = () => {
    setLang(lang === "tr" ? "en" : "tr");
  };

  return (
    <LanguageContext.Provider value={{ lang, setLang, toggleLang }}>
      {children}
    </LanguageContext.Provider>
  );
};
