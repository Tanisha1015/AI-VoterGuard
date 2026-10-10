import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { VerifyResult as VerifyResultData, VerifyStatus } from "../api/types";
import { useLang } from "../i18n";
import { formatDateTime, shortHash } from "../lib/format";
import CopyHash from "./CopyHash";

const STYLE: Record<VerifyStatus, { box: string; icon: string }> = {
  MATCH: { box: "border-emerald-400 bg-emerald-50", icon: "✓" },
  MISMATCH: { box: "border-red-400 bg-red-50", icon: "✕" },
  NOT_FOUND: { box: "border-slate-300 bg-slate-50", icon: "?" },
};

interface VerifyResultProps {
  result: VerifyResultData;
  /** True when the verified file was produced by "Simulate tampering". */
  simulated?: boolean;
}

/** Verification outcome card: icon + heading + text, never colour alone. */
export default function VerifyResult({ result, simulated = false }: VerifyResultProps) {
  const { t } = useTranslation();
  const lang = useLang();
  const style = STYLE[result.status];
  const time = result.recorded_at ? formatDateTime(result.recorded_at, lang) : t("verify.result.not_recorded");

  return (
    <article
      aria-labelledby="verify-result-title"
      data-testid="verify-result"
      data-status={result.status}
      className={`rounded-xl border-2 p-4 ${style.box}`}
    >
      {simulated && (
        <p className="mb-3 rounded-lg border-2 border-dashed border-slate-500 bg-white p-2 text-sm font-semibold text-slate-900">
          <span aria-hidden="true">⚗ </span>
          {t("verify.result.simulation")}
        </p>
      )}
      <header className="flex items-start gap-3">
        <span
          aria-hidden="true"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-2 border-current bg-white text-lg font-bold text-slate-800"
        >
          {style.icon}
        </span>
        <div>
          <h3 id="verify-result-title" className="text-lg font-semibold text-slate-900">
            {t(`verify.result.${result.status}_title`)}
          </h3>
          <p className="text-slate-800">
            {t(`verify.result.${result.status}_body`, { time, id: result.report_id })}
          </p>
        </div>
      </header>

      <dl className="mt-3 grid gap-x-4 gap-y-2 sm:grid-cols-2">
        <div>
          <dt className="text-sm text-slate-600">{t("verify.result.report_id")}</dt>
          <dd className="font-mono font-semibold">{result.report_id}</dd>
        </div>
        <div>
          <dt className="text-sm text-slate-600">{t("verify.result.recorded_at")}</dt>
          <dd>{result.recorded_at ? <time dateTime={result.recorded_at}>{time}</time> : time}</dd>
        </div>
        <div>
          <dt className="text-sm text-slate-600">{t("verify.result.submitter")}</dt>
          <dd>
            {result.submitter ? (
              <code className="font-mono" title={result.submitter}>
                {shortHash(result.submitter)}
              </code>
            ) : (
              t("verify.result.not_recorded")
            )}
          </dd>
        </div>
        {result.status === "MISMATCH" && (
          <>
            <div className="sm:col-span-2">
              <dt className="text-sm text-slate-600">{t("verify.result.computed_hash")}</dt>
              <dd>
                <CopyHash value={result.computed_hash} copyLabel={t("verify.result.copy_computed")} testId="computed-hash" />
              </dd>
            </div>
            {result.onchain_hash && (
              <div className="sm:col-span-2">
                <dt className="text-sm text-slate-600">{t("verify.result.onchain_hash")}</dt>
                <dd>
                  <CopyHash value={result.onchain_hash} copyLabel={t("verify.result.copy_onchain")} testId="onchain-hash" />
                </dd>
              </div>
            )}
          </>
        )}
      </dl>

      {result.superseded_by && (
        <p className="mt-3 text-slate-800">
          <span aria-hidden="true">⟲ </span>
          {t("verify.result.superseded")}{" "}
          <Link
            to={`/verify?report_id=${encodeURIComponent(result.superseded_by)}`}
            className="inline-flex min-h-11 items-center font-medium text-blue-800 underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
          >
            {t("verify.result.open_superseding", { id: result.superseded_by })}
          </Link>
        </p>
      )}
    </article>
  );
}
