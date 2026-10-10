import { useTranslation } from "react-i18next";
import type { ReportListItem } from "../api/types";
import { useLang } from "../i18n";
import { formatDateTime, shortHash } from "../lib/format";
import { EmptyState } from "./QueryState";

interface ReportListProps {
  reports: ReportListItem[];
  activeId: string | null;
  onSelect: (reportId: string) => void;
}

/** Recorded reports, newest first. Superseded reports get an icon + text badge (not colour alone). */
export default function ReportList({ reports, activeId, onSelect }: ReportListProps) {
  const { t } = useTranslation();
  const lang = useLang();

  if (reports.length === 0) {
    return <EmptyState title={t("verify.list.empty")} hint={t("verify.list.empty_hint")} testId="reports-empty" />;
  }

  return (
    <ul className="space-y-2" data-testid="report-list">
      {reports.map((r) => {
        const active = r.report_id === activeId;
        return (
          <li key={r.report_id}>
            <button
              type="button"
              onClick={() => onSelect(r.report_id)}
              aria-current={active ? "true" : undefined}
              aria-label={t("verify.list.select", { id: r.report_id })}
              data-testid={`report-row-${r.report_id}`}
              className={`flex w-full min-h-11 flex-col items-start gap-1 rounded-lg border-2 p-3 text-left focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700 ${
                active ? "border-blue-700 bg-blue-50" : "border-slate-200 bg-white hover:bg-slate-50"
              }`}
            >
              <span className="flex w-full flex-wrap items-center gap-2">
                {active && <span aria-hidden="true">▶</span>}
                <span className="font-mono font-semibold text-slate-900">{r.report_id}</span>
                {r.superseded_by ? (
                  <span className="inline-flex items-center gap-1 rounded-full border border-slate-400 bg-slate-100 px-2 py-0.5 text-xs font-semibold text-slate-800">
                    <span aria-hidden="true">⟲</span>
                    {t("verify.list.superseded", { id: r.superseded_by })}
                  </span>
                ) : (
                  <span className="inline-flex items-center gap-1 rounded-full border border-emerald-300 bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-900">
                    <span aria-hidden="true">●</span>
                    {t("verify.list.latest")}
                  </span>
                )}
              </span>
              <span className="text-sm text-slate-700">
                {t("verify.list.recorded_at", { time: formatDateTime(r.recorded_at, lang) })}
              </span>
              <code className="font-mono text-xs text-slate-600" title={r.report_hash}>
                {shortHash(r.report_hash)}
              </code>
            </button>
          </li>
        );
      })}
    </ul>
  );
}
