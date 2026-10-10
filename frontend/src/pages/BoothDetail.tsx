import { Link, useParams } from "react-router-dom";
import { useQuery } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { getBoothDetail } from "../api/core";
import { ApiError } from "../api/client";
import type { BoothDetail as BoothDetailData } from "../api/types";
import { useCurrentAudit } from "../hooks/useCurrentAudit";
import { useLang } from "../i18n";
import { formatNumber, formatPercent } from "../lib/format";
import { boothQueryKey } from "../components/ReviewControls";
import FlagCard from "../components/FlagCard";
import Disclaimer from "../components/Disclaimer";
import ReasonMixChart from "../components/charts/ReasonMixChart";
import GenderChart from "../components/charts/GenderChart";
import AgeBandChart from "../components/charts/AgeBandChart";
import { Loading, LoadError } from "../components/QueryState";
import { usePageTitle } from "../hooks/usePageTitle";

function Stats({ booth }: { booth: BoothDetailData }) {
  const { t } = useTranslation();
  const lang = useLang();
  const items: [string, string][] = [
    ["booth.draft_count", formatNumber(booth.draft_count, lang)],
    ["booth.final_count", formatNumber(booth.final_count, lang)],
    ["booth.removed", formatNumber(booth.removed, lang)],
    ["booth.added", formatNumber(booth.added, lang)],
    ["booth.deletion_rate", formatPercent(booth.deletion_rate)],
    ["booth.risk_score", String(booth.risk_score)],
  ];
  return (
    <dl aria-label={t("booth.stats_label")} className="grid grid-cols-2 gap-3 sm:grid-cols-3 lg:grid-cols-6">
      {items.map(([key, value]) => (
        <div key={key} className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
          <dt className="text-sm text-slate-600">{t(key)}</dt>
          <dd className="mt-1 text-xl font-bold text-slate-900">{value}</dd>
        </div>
      ))}
    </dl>
  );
}

/** Booth detail (route "/reviewer/booth/:part"): stats, three charts, flag cards with review controls. */
export default function BoothDetail() {
  const { t } = useTranslation();
  const { part = "" } = useParams<{ part: string }>();
  const partNo = Number(part);
  const audit = useCurrentAudit();
  const auditId = audit.auditId ?? "";

  const booth = useQuery({
    queryKey: boothQueryKey(auditId, partNo),
    queryFn: () => getBoothDetail(partNo, auditId),
    enabled: auditId !== "" && Number.isInteger(partNo),
  });

  const notFound = booth.error instanceof ApiError && booth.error.status === 404;
  usePageTitle(t("booth.title", { part }));

  return (
    <div className="space-y-6">
      <Link
        to="/reviewer"
        className="inline-flex min-h-11 items-center text-blue-800 underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
      >
        <span aria-hidden="true">← </span>
        {t("booth.back")}
      </Link>
      <h1 className="text-2xl font-bold text-slate-900">{t("booth.title", { part })}</h1>

      {(audit.isLoading || booth.isLoading) && <Loading />}
      {audit.isError && <LoadError />}
      {!audit.isLoading && !audit.isError && auditId === "" && <LoadError message={t("common.no_audit")} />}
      {booth.isError &&
        (notFound ? <LoadError message={t("booth.not_found")} /> : <LoadError onRetry={() => void booth.refetch()} />)}

      {booth.data && (
        <>
          <Stats booth={booth.data} />

          <section aria-labelledby="charts-title">
            <h2 id="charts-title" className="text-lg font-semibold text-slate-900">
              {t("booth.charts_title")}
            </h2>
            <div className="mt-3 grid gap-4 md:grid-cols-2 xl:grid-cols-3">
              <ReasonMixChart mix={booth.data.reason_mix} />
              <GenderChart counts={booth.data.gender_removed} />
              <AgeBandChart shares={booth.data.age_band_removed_share} />
            </div>
          </section>

          <section aria-labelledby="flags-title">
            <h2 id="flags-title" className="text-lg font-semibold text-slate-900">
              {t("booth.flags_title")}
            </h2>
            <Disclaimer text={t("common.flag_disclaimer")} />
            {booth.data.flags.length === 0 ? (
              <p className="mt-3 text-slate-700">{t("booth.no_flags")}</p>
            ) : (
              <div className="mt-3 space-y-4">
                {booth.data.flags.map((flag) => (
                  <FlagCard key={flag.flag_id} flag={flag} auditId={auditId} />
                ))}
              </div>
            )}
          </section>
        </>
      )}
    </div>
  );
}
