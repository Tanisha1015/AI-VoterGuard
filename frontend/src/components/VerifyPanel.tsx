import { useId, useState, type ChangeEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { fetchReportFile, verifyReport } from "../api/trust";
import type { VerifyResult as VerifyResultData } from "../api/types";
import { readFileText } from "../lib/readFile";
import { tamperText, type TamperResult } from "../lib/tamper";
import { verifyErrorKey } from "../lib/verifyErrors";
import VerifyResult from "./VerifyResult";

interface VerifyJob {
  file: File;
  simulated: boolean;
}

const btn =
  "inline-flex min-h-11 items-center justify-center gap-2 rounded-lg px-4 font-semibold focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700 disabled:opacity-60";

/** File slot + "Load original" + "Verify" + "Simulate tampering" for the active report. */
export default function VerifyPanel({ reportId }: { reportId: string }) {
  const { t } = useTranslation();
  const baseId = useId();
  const [file, setFile] = useState<File | null>(null);
  const [original, setOriginal] = useState<File | null>(null);
  const [tamper, setTamper] = useState<TamperResult | null>(null);
  const [localError, setLocalError] = useState<string | null>(null);

  const load = useMutation<File, unknown, string>({
    mutationFn: (id) => fetchReportFile(id),
    onSuccess: (loaded) => {
      setFile(loaded);
      setOriginal(loaded);
      setTamper(null);
      verify.reset();
    },
  });

  const verify = useMutation<VerifyResultData, unknown, VerifyJob>({
    mutationFn: (job) => verifyReport(job.file, reportId),
  });

  function onPick(event: ChangeEvent<HTMLInputElement>) {
    const picked = event.target.files?.[0] ?? null;
    setFile(picked);
    setOriginal(null);
    setTamper(null);
    setLocalError(null);
    verify.reset();
  }

  async function onTamper() {
    if (!original) return;
    setLocalError(null);
    try {
      const change = tamperText(await readFileText(original));
      const changed = new File([change.text], `tampered-${original.name}`, { type: "application/json" });
      setTamper(change);
      setFile(changed);
      verify.mutate({ file: changed, simulated: true });
    } catch {
      setLocalError("verify.errors.read_failed");
    }
  }

  const error = localError ?? (load.isError ? verifyErrorKey(load.error) : verify.isError ? verifyErrorKey(verify.error) : null);

  return (
    <section aria-labelledby={`${baseId}-title`} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 id={`${baseId}-title`} className="text-lg font-semibold text-slate-900">
        {t("verify.slot.title", { id: reportId })}
      </h2>

      <div className="mt-3 space-y-3">
        <div>
          <label htmlFor={`${baseId}-file`} className="block font-medium text-slate-800">
            {t("verify.slot.file_label")}
          </label>
          <p id={`${baseId}-hint`} className="text-sm text-slate-600">{t("verify.slot.file_hint")}</p>
          <input
            id={`${baseId}-file`}
            type="file"
            accept=".json,application/json"
            aria-describedby={`${baseId}-hint`}
            onChange={onPick}
            className="mt-1 block min-h-11 w-full rounded-lg border-2 border-slate-400 bg-white p-2 text-sm file:mr-3 file:min-h-9 file:rounded file:border-0 file:bg-slate-200 file:px-3 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
          />
        </div>

        <div className="flex flex-wrap gap-2">
          <button type="button" onClick={() => load.mutate(reportId)} disabled={load.isPending}
            className={`${btn} border-2 border-blue-700 bg-white text-blue-800 hover:bg-blue-50`}>
            {load.isPending ? t("verify.slot.loading_original") : t("verify.slot.load_original")}
          </button>
          <button type="button" onClick={() => file && verify.mutate({ file, simulated: tamper !== null })}
            disabled={!file || verify.isPending} aria-busy={verify.isPending}
            className={`${btn} bg-blue-700 text-white hover:bg-blue-800`}>
            {verify.isPending ? t("verify.slot.verifying") : t("verify.slot.verify")}
          </button>
          {original && (
            <button type="button" onClick={() => void onTamper()} disabled={verify.isPending}
              className={`${btn} border-2 border-dashed border-slate-600 bg-white text-slate-900 hover:bg-slate-50`}>
              <span aria-hidden="true">⚗</span>
              {t("verify.slot.tamper")}
            </button>
          )}
        </div>
        {original && <p className="text-sm text-slate-600">{t("verify.slot.tamper_hint")}</p>}

        <p className="text-sm text-slate-800" data-testid="file-slot">
          {file ? t("verify.slot.in_slot", { name: file.name, size: file.size }) : t("verify.slot.empty")}
        </p>
        {tamper && (
          <p className="text-sm font-medium text-slate-900" data-testid="tamper-note">
            {tamper.kind === "digit"
              ? t("verify.slot.tamper_change", { position: tamper.index + 1, before: tamper.before, after: tamper.after })
              : t("verify.slot.tamper_space")}
          </p>
        )}
      </div>

      <div aria-live="polite" aria-label={t("verify.result.region")} className="mt-4">
        {error && (
          <p role="alert" className="rounded-lg border-2 border-slate-300 bg-white p-3 text-slate-800">
            <span aria-hidden="true">ⓘ </span>
            {t(error)}
          </p>
        )}
        {verify.isSuccess && <VerifyResult result={verify.data} simulated={verify.variables.simulated} />}
      </div>
    </section>
  );
}
