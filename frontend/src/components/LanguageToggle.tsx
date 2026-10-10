import { useTranslation } from "react-i18next";
import { setLang, SUPPORTED_LANGS, useLang } from "../i18n";

/** EN | हिन्दी switch. Selection is persisted in localStorage. */
export default function LanguageToggle() {
  const { t } = useTranslation();
  const active = useLang();

  return (
    <div role="group" aria-label={t("lang.label")} className="flex items-center rounded-lg border border-slate-300 bg-white p-0.5">
      {SUPPORTED_LANGS.map((lang) => {
        const pressed = lang === active;
        return (
          <button
            key={lang}
            type="button"
            lang={lang}
            aria-pressed={pressed}
            onClick={() => void setLang(lang)}
            className={`min-h-11 min-w-11 rounded-md px-3 text-sm font-medium focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700 ${
              pressed ? "bg-slate-800 text-white underline underline-offset-4" : "text-slate-700 hover:bg-slate-100"
            }`}
          >
            {t(`lang.${lang}`)}
          </button>
        );
      })}
    </div>
  );
}
