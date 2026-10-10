import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { ReportCreated } from "../api/types";
import { trustFileUrl } from "../api/trust";
import { useLang } from "../i18n";
import { formatDateTime, shortHash } from "../lib/format";
import CopyHash from "./CopyHash";

/** Shows the recorded report with shortened hashes, copy button, downloads and a verify link. */
export default function ReportCard({ report }: { report: ReportCreated }) {
  const { t } = useTranslation();
  const lang = useLang();

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
          <dd>
            <CopyHash value={report.report_hash} />
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
