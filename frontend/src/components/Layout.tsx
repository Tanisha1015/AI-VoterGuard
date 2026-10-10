import { NavLink, Outlet } from "react-router-dom";
import { useTranslation } from "react-i18next";
import LanguageToggle from "./LanguageToggle";

const NAV_ITEMS = [
  { to: "/", key: "nav.citizen", end: true },
  { to: "/reviewer", key: "nav.reviewer", end: false },
  { to: "/verify", key: "nav.verify", end: false },
] as const;

/** App shell: header with name, nav and language toggle, a standing synthetic-data banner, and main content. */
export default function Layout() {
  const { t } = useTranslation();

  return (
    <div className="min-h-screen bg-slate-50 text-slate-900">
      <a
        href="#main"
        className="sr-only focus:not-sr-only focus:absolute focus:left-2 focus:top-2 focus:z-50 focus:rounded focus:bg-white focus:p-2 focus:outline-2 focus:outline-blue-700"
      >
        {t("app.skip_to_content")}
      </a>

      <header className="border-b border-slate-200 bg-white">
        <div className="mx-auto flex max-w-6xl flex-wrap items-center justify-between gap-2 px-4 py-2">
          <div>
            <p className="text-lg font-bold text-slate-900">{t("app.name")}</p>
            <p className="text-xs text-slate-600">{t("app.tagline")}</p>
          </div>
          <LanguageToggle />
        </div>
        <nav aria-label={t("nav.label")} className="mx-auto max-w-6xl px-2">
          <ul className="flex gap-1">
            {NAV_ITEMS.map((item) => (
              <li key={item.to}>
                <NavLink
                  to={item.to}
                  end={item.end}
                  className={({ isActive }) =>
                    `inline-flex min-h-11 items-center border-b-4 px-3 text-sm font-medium focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700 ${
                      isActive ? "border-blue-700 text-blue-800" : "border-transparent text-slate-700 hover:text-slate-900"
                    }`
                  }
                >
                  {t(item.key)}
                </NavLink>
              </li>
            ))}
          </ul>
        </nav>
      </header>

      <div role="note" className="border-b border-sky-200 bg-sky-50">
        <p className="mx-auto max-w-6xl px-4 py-2 text-sm text-sky-900">
          <span aria-hidden="true">ⓘ </span>
          {t("banner.text")}
        </p>
      </div>

      <main id="main" tabIndex={-1} className="mx-auto max-w-6xl px-4 py-6 focus:outline-none">
        <Outlet />
      </main>
    </div>
  );
}
