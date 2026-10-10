import { useTranslation } from "react-i18next";
import type { Totals } from "../api/types";
import { useLang } from "../i18n";
import { formatNumber } from "../lib/format";

const KPI_KEYS = ["draft_count", "final_count", "removed", "added", "flagged_booths", "pending_reviews"] as const;

/** Six headline figures from the audit summary. */
export default function KpiCards({ totals }: { totals: Totals }) {
  const { t } = useTranslation();
  const lang = useLang();

  return (
    <section aria-label={t("reviewer.kpi.label")}>
      <dl className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
        {KPI_KEYS.map((key) => (
          <div key={key} className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
            <dt className="text-sm text-slate-600">{t(`reviewer.kpi.${key}`)}</dt>
            <dd className="mt-1 text-2xl font-bold text-slate-900" data-testid={`kpi-${key}`}>
              {formatNumber(totals[key], lang)}
            </dd>
          </div>
        ))}
      </dl>
    </section>
  );
}
