/**
 * i18next setup: English + Hindi, persisted in localStorage under "vg.lang".
 */
import i18n from "i18next";
import { initReactI18next, useTranslation } from "react-i18next";
import en from "./en.json";
import hi from "./hi.json";
import type { Bilingual, Lang } from "../api/types";

export const LANG_STORAGE_KEY = "vg.lang";
export const SUPPORTED_LANGS: readonly Lang[] = ["en", "hi"];

function isLang(value: unknown): value is Lang {
  return value === "en" || value === "hi";
}

/** Read the saved language, defaulting to English. Safe when storage is unavailable. */
export function getStoredLang(): Lang {
  try {
    const saved = window.localStorage.getItem(LANG_STORAGE_KEY);
    return isLang(saved) ? saved : "en";
  } catch {
    return "en";
  }
}

function applyDocumentLang(lang: Lang): void {
  if (typeof document !== "undefined") document.documentElement.lang = lang;
}

/** Change language, persist it, and update <html lang>. */
export async function setLang(lang: Lang): Promise<void> {
  try {
    window.localStorage.setItem(LANG_STORAGE_KEY, lang);
  } catch {
    // storage may be blocked; language still changes for this session
  }
  applyDocumentLang(lang);
  await i18n.changeLanguage(lang);
}

void i18n.use(initReactI18next).init({
  resources: { en: { translation: en }, hi: { translation: hi } },
  lng: getStoredLang(),
  fallbackLng: "en",
  supportedLngs: [...SUPPORTED_LANGS],
  interpolation: { escapeValue: false },
  returnNull: false,
});
applyDocumentLang(getStoredLang());

/** Active language as a Lang union. */
export function useLang(): Lang {
  const { i18n: instance } = useTranslation();
  return isLang(instance.language) ? instance.language : "en";
}

/** Returns a picker for bilingual API text ({en, hi}) in the active language. */
export function useBi(): (text: Bilingual | null | undefined) => string {
  const lang = useLang();
  return (text) => (text ? text[lang] || text.en : "");
}

export default i18n;
