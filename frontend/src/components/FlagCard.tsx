import { useTranslation } from "react-i18next";
import type { Flag } from "../api/types";
import { useBi } from "../i18n";
import { formatPercent } from "../lib/format";
import SeverityChip from "./SeverityChip";
import ReviewControls from "./ReviewControls";

/** Metric values are shares (0..1) in the contract; show them as percentages. */
function MetricLine({ flag }: { flag: Flag }) {
  const { t } = useTranslation();
  const name = t(`reviewer.metric.${flag.metric.name}`, { defaultValue: flag.metric.name });
  return (
    <p className="text-sm text-slate-800">
      {t("reviewer.metric.line", {
        name,
        value: formatPercent(flag.metric.value),
        baseline: formatPercent(flag.metric.baseline),
      })}
    </p>
  );
}

/** One flag: detector, severity, metric vs baseline, explanation, checks, source and review controls. */
export default function FlagCard({ flag, auditId }: { flag: Flag; auditId: string }) {
  const { t } = useTranslation();
  const bi = useBi();
  const isAgent = flag.explanation_source === "agent";

  return (
    <article
      aria-labelledby={`flag-${flag.flag_id}-title`}
      className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm"
      data-testid={`flag-${flag.flag_id}`}
    >
      <header className="flex flex-wrap items-center gap-2">
        <h3 id={`flag-${flag.flag_id}-title`} className="mr-auto text-base font-semibold text-slate-900">
          {t(`reviewer.detector.${flag.detector}`)}
        </h3>
        <SeverityChip severity={flag.severity} />
        <span className="inline-flex items-center gap-1 rounded-full border border-slate-300 bg-slate-50 px-2 py-0.5 text-xs font-medium text-slate-700">
          <span aria-hidden="true">{isAgent ? "✦" : "▤"}</span>
          {t(isAgent ? "reviewer.source.agent" : "reviewer.source.template")}
        </span>
      </header>

      <div className="mt-2 space-y-2">
        <MetricLine flag={flag} />
        <div>
          <h4 className="text-sm font-semibold text-slate-700">{t("booth.explanation")}</h4>
          <p className="text-slate-900" data-testid={`explanation-${flag.flag_id}`}>
            {bi(flag.explanation)}
          </p>
        </div>
        {flag.recommended_checks.length > 0 && (
          <div>
            <h4 className="text-sm font-semibold text-slate-700">{t("booth.checks")}</h4>
            <ul className="list-disc space-y-1 pl-5 text-slate-900">
              {flag.recommended_checks.map((check, i) => (
                <li key={i}>{bi(check)}</li>
              ))}
            </ul>
          </div>
        )}
      </div>

      <ReviewControls auditId={auditId} flag={flag} />
    </article>
  );
}
