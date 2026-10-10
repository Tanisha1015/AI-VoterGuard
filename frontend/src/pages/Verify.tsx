import { useState } from "react";
import { useSearchParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { listReports } from "../api/trust";
import type { ReportCreated } from "../api/types";
import { useCurrentAudit } from "../hooks/useCurrentAudit";
import ReportList from "../components/ReportList";
import VerifyPanel from "../components/VerifyPanel";
import CorrectionPanel, { REPORTS_QUERY_KEY } from "../components/CorrectionPanel";
import { Loading, LoadError } from "../components/QueryState";
import { usePageTitle } from "../hooks/usePageTitle";

/** "What this proves / does not prove" panel (requirement 7). */
function Explanation() {
  const { t } = useTranslation();
  return (
    <aside aria-labelledby="verify-explain-title" className="rounded-xl border border-sky-200 bg-sky-50 p-4 text-sky-950">
      <h2 id="verify-explain-title" className="font-semibold">
        <span aria-hidden="true">ⓘ </span>
        {t("verify.explain.title")}
      </h2>
      <p className="mt-1">
        <strong>{t("verify.explain.proves_label")}</strong> {t("verify.explain.proves")}
      </p>
      <p className="mt-1">
        <strong>{t("verify.explain.not_proves_label")}</strong> {t("verify.explain.not_proves")}
      </p>
    </aside>
  );
}

/** Verify page (route "/verify"): pick a recorded report, verify a file, simulate tampering, record corrections. */
export default function Verify() {
  const { t } = useTranslation();
  const [params, setParams] = useSearchParams();
  const audit = useCurrentAudit();
  const reports = useQuery({ queryKey: REPORTS_QUERY_KEY, queryFn: listReports });
  usePageTitle(t("verify.title"));

  const requested = params.get("report_id");
  const items = reports.data?.items ?? [];
  const active = items.find((r) => r.report_id === requested) ?? null;

  const [recorded, setRecorded] = useState<ReportCreated | null>(null);
  const select = (reportId: string) => {
    setRecorded(null);
    setParams({ report_id: reportId });
  };
  const onRecorded = (created: ReportCreated) => {
    setParams({ report_id: created.report_id });
    setRecorded(created);
  };

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">{t("verify.title")}</h1>
        <p className="mt-1 text-slate-700">{t("verify.intro")}</p>
      </header>

      <Explanation />

      <div aria-live="polite">
        {recorded && (
          <p className="rounded-xl border-2 border-emerald-300 bg-emerald-50 p-3 font-medium text-emerald-950" data-testid="correction-notice">
            <span aria-hidden="true">✓ </span>
            {t("verify.correct.success", { id: recorded.report_id, old: recorded.supersedes })}
          </p>
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-[minmax(0,2fr)_minmax(0,3fr)]">
        <section aria-labelledby="report-list-title">
          <h2 id="report-list-title" className="mb-2 text-lg font-semibold text-slate-900">
            {t("verify.list.title")}
          </h2>
          {reports.isLoading && <Loading />}
          {reports.isError && <LoadError onRetry={() => void reports.refetch()} />}
          {reports.data && <ReportList reports={items} activeId={active?.report_id ?? null} onSelect={select} />}
        </section>

        <div className="space-y-4">
          {active ? (
            <>
              {/* key: switching report resets the file slot and result */}
              <VerifyPanel key={active.report_id} reportId={active.report_id} />
              <CorrectionPanel key={`c-${active.report_id}`} report={active} auditId={audit.auditId} onRecorded={onRecorded} />
            </>
          ) : (
            reports.data && (
              <p className="rounded-xl border border-dashed border-slate-300 bg-white p-4 text-slate-700">
                {t("verify.slot.none_selected")}
              </p>
            )
          )}
        </div>
      </div>
    </div>
  );
}
