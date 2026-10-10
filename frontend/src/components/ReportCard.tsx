import { useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { ReportCreated } from "../api/types";
import { trustFileUrl } from "../api/trust";
import { useLang } from "../i18n";
import { formatDateTime, shortHash } from "../lib/format";

type CopyState = "idle" | "copied" | "failed";

/** Shows the recorded report with shortened hashes, copy button, downloads and a verify link. */
export default function ReportCard({ report }: { report: ReportCreated }) {
  const { t } = useTranslation();
  const lang = useLang();
  const [copy, setCopy] = useState<CopyState>("idle");

  async function copyHash() {
    try {
      await navigator.clipboard.writeText(report.report_hash);
      setCopy("copied");
    } catch {
      setCopy("failed");
    }
  }

  const linkClass =
    "inline-flex min-h-11 items-center rounded-lg border-2 border-blue-700 bg-white px-3 text-sm font-medium text-blue-800 hover:bg-blue-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700";

  return (
    <article aria-labelledby="report-card-title" className="rounded-xl border-2 border-emerald-300 bg-emerald-50 p-4" data-testid="report-card">
      <h3 id="report-card-title" className="flex items-center gap-2 text-lg font-semibold text-slate-900">
        <span aria-hidden="true">✓</span>
        {t("reviewer.report.title")}
      </h3>
      <dl className="mt-3 grid gap-x-4 gap-y-2 sm:grid-cols-2">
        <div>
          <dt className="text-sm text-slate-600">{t("reviewer.report.report_id")}</dt>
          <dd className="font-mono font-semibold">{report.report_id}</dd>
        </div>
        <div>
          <dt className="text-sm text-slate-600">{t("reviewer.report.recorded_at")}</dt>
          <dd>
            <time dateTime={report.recorded_at}>{formatDateTime(report.recorded_at, lang)}</time>
          </dd>
        </div>
        <div>
          <dt className="text-sm text-slate-600">{t("reviewer.report.report_hash")}</dt>
          <dd className="flex flex-wrap items-center gap-2">
            <code title={report.report_hash} className="font-mono">
              {shortHash(report.report_hash)}
            </code>
            <button
              type="button"
              onClick={() => void copyHash()}
              className="inline-flex min-h-11 items-center rounded-lg border border-slate-400 bg-white px-3 text-sm hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
            >
              {t("reviewer.report.copy")}
            </button>
            <span aria-live="polite" className="text-sm text-slate-700">
              {copy === "copied" ? t("reviewer.report.copied") : copy === "failed" ? t("reviewer.report.copy_failed") : ""}
            </span>
          </dd>
        </div>
        <div>
          <dt className="text-sm text-slate-600">{t("reviewer.report.tx_hash")}</dt>
          <dd>
            <code title={report.tx_hash} className="font-mono">
              {shortHash(report.tx_hash)}
            </code>
            <span className="ml-2 text-sm text-slate-600">
              {t("reviewer.report.block")} {report.block_number}
            </span>
          </dd>
        </div>
      </dl>
      <div className="mt-4 flex flex-wrap gap-2">
        <a href={trustFileUrl(report.files.json)} download className={linkClass}>
          {t("reviewer.report.download_json")}
        </a>
        <a href={trustFileUrl(report.files.pdf)} download className={linkClass}>
          {t("reviewer.report.download_pdf")}
        </a>
        <Link to={`/verify?report_id=${encodeURIComponent(report.report_id)}`} className={linkClass}>
          {t("reviewer.report.verify_link")}
        </Link>
      </div>
    </article>
  );
}
