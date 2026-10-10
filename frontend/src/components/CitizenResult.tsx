import { useTranslation } from "react-i18next";
import type { CitizenLookupResponse } from "../api/types";
import { useBi } from "../i18n";
import StatusCard from "./StatusCard";
import Disclaimer from "./Disclaimer";

interface CitizenResultProps {
  result: CitizenLookupResponse;
  /** Switch the form to EPIC mode (offered for NOT_FOUND / AMBIGUOUS). */
  onUseEpic: () => void;
}

/** Renders exactly what the lookup API returned, laid out per status. */
export default function CitizenResult({ result, onUseEpic }: CitizenResultProps) {
  const { t } = useTranslation();
  const bi = useBi();
  const { status, record, reason, next_step: nextStep } = result;
  const body = status === "AMBIGUOUS" && result.message ? bi(result.message) : t(`result.status.${status}.body`);

  return (
    <StatusCard status={status} statusLabel={t("result.status_label")} title={t(`result.status.${status}.title`)}>
      <p>{body}</p>

      {record && (
        <dl className="grid grid-cols-1 gap-x-4 gap-y-2 rounded-lg bg-white/70 p-3 sm:grid-cols-2">
          <div>
            <dt className="text-sm text-slate-600">{t("result.name")}</dt>
            <dd className="font-medium">{record.name_display}</dd>
          </div>
          <div>
            <dt className="text-sm text-slate-600">{t("result.epic")}</dt>
            <dd className="font-mono font-medium">{record.epic_masked}</dd>
          </div>
          <div>
            <dt className="text-sm text-slate-600">{t("result.part_no")}</dt>
            <dd className="font-medium">{record.part_no}</dd>
          </div>
          <div>
            <dt className="text-sm text-slate-600">{t("result.age_band")}</dt>
            <dd className="font-medium">{record.age_band}</dd>
          </div>
          {reason && (
            <div className="sm:col-span-2">
              <dt className="text-sm text-slate-600">{t("result.reason")}</dt>
              <dd className="font-medium">{t(`result.reasons.${reason}`)}</dd>
            </div>
          )}
        </dl>
      )}

      {status === "REMOVED" && nextStep && (
        <section aria-labelledby="what-you-can-do" className="rounded-lg border border-amber-200 bg-white p-3">
          <h3 id="what-you-can-do" className="font-semibold text-slate-900">
            {t("result.what_you_can_do")}
          </h3>
          <p className="mt-1 text-slate-800">{bi(nextStep.title)}</p>
          <ol className="mt-2 list-decimal space-y-1 pl-5">
            {nextStep.steps.map((step, index) => (
              <li key={index}>{bi(step)}</li>
            ))}
          </ol>
          <p className="mt-3">
            <span className="text-slate-600">{t("result.deadline")}: </span>
            <time dateTime={nextStep.deadline} className="font-semibold">
              {nextStep.deadline}
            </time>
          </p>
          <Disclaimer text={bi(nextStep.disclaimer)} />
        </section>
      )}

      {(status === "NOT_FOUND" || status === "AMBIGUOUS") && (
        <button
          type="button"
          onClick={onUseEpic}
          className="inline-flex min-h-11 items-center rounded-lg border-2 border-blue-700 bg-white px-4 font-medium text-blue-800 hover:bg-blue-50 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
        >
          {t("result.try_epic")}
        </button>
      )}

      {status !== "REMOVED" && <Disclaimer />}
    </StatusCard>
  );
}
