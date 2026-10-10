import { useId, useState, type FormEvent } from "react";
import { useMutation } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { createReport } from "../api/trust";
import { ApiError, NetworkError } from "../api/client";
import type { CreateReportRequest, ReportCreated } from "../api/types";
import FormField from "./FormField";
import ReportCard from "./ReportCard";

/** Map a createReport failure to translated text. */
export function finalizeErrorText(error: unknown, t: (key: string, opts?: Record<string, unknown>) => string): string {
  if (error instanceof ApiError) {
    if (error.status >= 502 && error.status <= 504) return t("reviewer.finalize.error_ledger");
    if (error.status === 409 || error.status === 422 || error.status === 400) {
      return t("reviewer.finalize.error_rejected", { message: error.message });
    }
  }
  if (error instanceof NetworkError) return t("reviewer.finalize.error_network");
  return t("reviewer.finalize.error_generic");
}

interface FinalizePanelProps {
  auditId: string;
  pendingReviews: number;
}

/** Reviewer name + "Finalize and record report"; shows ReportCard on success. */
export default function FinalizePanel({ auditId, pendingReviews }: FinalizePanelProps) {
  const { t } = useTranslation();
  const baseId = useId();
  const [name, setName] = useState("");
  const [nameError, setNameError] = useState<string | undefined>();

  const finalize = useMutation<ReportCreated, unknown, CreateReportRequest>({
    mutationFn: (body) => createReport(body),
  });

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    const trimmed = name.trim();
    if (!trimmed) {
      setNameError("reviewer.finalize.reviewer_name_required");
      document.getElementById(`${baseId}-name`)?.focus();
      return;
    }
    finalize.mutate({ audit_id: auditId, reviewer_name: trimmed, supersedes: null });
  }

  return (
    <section aria-labelledby={`${baseId}-title`} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 id={`${baseId}-title`} className="text-lg font-semibold text-slate-900">
        {t("reviewer.finalize.title")}
      </h2>
      <p className="mt-1 text-sm text-slate-600">{t("reviewer.finalize.intro")}</p>

      <form noValidate onSubmit={onSubmit} className="mt-3 space-y-3">
        <FormField
          id={`${baseId}-name`}
          label={t("reviewer.finalize.reviewer_name")}
          error={nameError ? t(nameError) : undefined}
          value={name}
          onChange={(v) => {
            setName(v);
            if (nameError) setNameError(undefined);
          }}
        />

        <p className="font-medium text-slate-800" data-testid="finalize-pending">
          {t("reviewer.finalize.pending", { count: pendingReviews })}
        </p>
        {pendingReviews > 0 && (
          <p className="rounded-lg border border-amber-300 bg-amber-50 p-2 text-sm text-amber-900">
            <span aria-hidden="true">ⓘ </span>
            {t("reviewer.finalize.pending_note")}
          </p>
        )}

        <button
          type="submit"
          disabled={finalize.isPending}
          aria-busy={finalize.isPending}
          className="inline-flex min-h-12 items-center justify-center gap-2 rounded-lg bg-blue-700 px-5 font-semibold text-white hover:bg-blue-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700 disabled:cursor-wait disabled:opacity-70"
        >
          {finalize.isPending && (
            <span aria-hidden="true" className="h-4 w-4 animate-spin rounded-full border-2 border-white border-t-transparent" />
          )}
          {finalize.isPending ? t("reviewer.finalize.submitting") : t("reviewer.finalize.submit")}
        </button>
      </form>

      <div aria-live="polite" className="mt-4">
        {finalize.isError && (
          <div role="alert" className="rounded-lg border-2 border-slate-300 bg-white p-3 text-slate-800">
            <span aria-hidden="true">ⓘ </span>
            {finalizeErrorText(finalize.error, t)}
          </div>
        )}
        {finalize.isSuccess && <ReportCard report={finalize.data} />}
      </div>
    </section>
  );
}
