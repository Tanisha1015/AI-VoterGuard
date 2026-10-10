import { useTranslation } from "react-i18next";

/** Shared "Coming soon" placeholder for pages under construction. */
export default function ComingSoon({ title }: { title: string }) {
  const { t } = useTranslation();
  return (
    <section className="rounded-xl border border-slate-200 bg-white p-6 shadow-sm">
      <h1 className="text-2xl font-bold text-slate-900">{title}</h1>
      <p className="mt-2 font-medium text-slate-700">{t("placeholder.coming_soon")}</p>
      <p className="mt-1 text-slate-600">{t("placeholder.body")}</p>
    </section>
  );
}
