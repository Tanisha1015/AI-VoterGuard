import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { getBooths, getFlags, getSummary } from "../api/core";
import { useCurrentAudit } from "../hooks/useCurrentAudit";
import KpiCards from "../components/KpiCards";
import Heatmap from "../components/Heatmap";
import BoothTable from "../components/BoothTable";
import FinalizePanel from "../components/FinalizePanel";
import Disclaimer from "../components/Disclaimer";
import { Loading, LoadError } from "../components/QueryState";

/** Reviewer dashboard (route "/reviewer"): KPIs, heatmap, booth table, finalize panel. */
export default function ReviewerDashboard() {
  const { t } = useTranslation();
  const audit = useCurrentAudit();
  const auditId = audit.auditId ?? "";
  const enabled = auditId !== "";

  const summary = useQuery({ queryKey: ["summary", auditId], queryFn: () => getSummary(auditId), enabled });
  const booths = useQuery({ queryKey: ["booths", auditId], queryFn: () => getBooths(auditId), enabled });
  const flags = useQuery({ queryKey: ["flags", auditId], queryFn: () => getFlags({}, auditId), enabled });

  if (audit.isLoading) return <Loading />;
  if (audit.isError) return <LoadError />;
  if (!enabled) return <LoadError message={t("common.no_audit")} />;

  return (
    <div className="space-y-6">
      <header>
        <h1 className="text-2xl font-bold text-slate-900">{t("reviewer.title")}</h1>
        {summary.data && (
          <p className="text-slate-600">
            {t("reviewer.subtitle", { ac_name: summary.data.ac_name, audit_id: summary.data.audit_id })}
          </p>
        )}
      </header>

      {summary.isLoading && <Loading />}
      {summary.isError && <LoadError onRetry={() => void summary.refetch()} />}
      {summary.data && <KpiCards totals={summary.data.totals} />}

      {booths.isLoading && <Loading />}
      {booths.isError && <LoadError onRetry={() => void booths.refetch()} />}
      {booths.data && (
        <>
          <Heatmap booths={booths.data.items} />
          <div>
            <BoothTable booths={booths.data.items} flags={flags.data?.items ?? []} />
            <Disclaimer text={t("common.flag_disclaimer")} />
          </div>
        </>
      )}

      {summary.data && <FinalizePanel auditId={auditId} pendingReviews={summary.data.totals.pending_reviews} />}
    </div>
  );
}
