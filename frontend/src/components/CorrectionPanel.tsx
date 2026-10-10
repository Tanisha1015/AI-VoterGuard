import { useId, useState, type FormEvent } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { createReport } from "../api/trust";
import type { CreateReportRequest, ReportCreated, ReportListItem } from "../api/types";
import { verifyErrorKey } from "../lib/verifyErrors";
import { pushToast, toastKeyFor } from "../lib/toast";
import FormField from "./FormField";

export const REPORTS_QUERY_KEY = ["reports"] as const;

interface CorrectionPanelProps {
  report: ReportListItem;
  auditId: string | null;
  onRecorded: (created: ReportCreated) => void;
}

/** "Record corrected version": a new report that supersedes the active one. */
export default function CorrectionPanel({ report, auditId, onRecorded }: CorrectionPanelProps) {
  const { t } = useTranslation();
  const baseId = useId();
  const queryClient = useQueryClient();
  const [name, setName] = useState("");
  const [nameError, setNameError] = useState(false);

  const mutation = useMutation<ReportCreated, unknown, CreateReportRequest>({
    mutationFn: (body) => createReport(body),
    // Refresh the list first, then select the new report, so the selection never points at a missing row.
    onSuccess: async (created) => {
      await queryClient.invalidateQueries({ queryKey: REPORTS_QUERY_KEY });
      onRecorded(created);
    },
    onError: (err) => {
      pushToast(toastKeyFor(err));
      return queryClient.invalidateQueries({ queryKey: REPORTS_QUERY_KEY });
    },
  });

  const blocked = report.superseded_by !== null;

  function onSubmit(event: FormEvent<HTMLFormElement>) {
    event.preventDefault();
    if (!name.trim()) {
      setNameError(true);
      document.getElementById(`${baseId}-name`)?.focus();
      return;
    }
    if (!auditId || blocked) return;
    mutation.mutate({ audit_id: auditId, reviewer_name: name.trim(), supersedes: report.report_id });
  }

  return (
    <section aria-labelledby={`${baseId}-title`} className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h3 id={`${baseId}-title`} className="text-base font-semibold text-slate-900">
        {t("verify.correct.title")}
      </h3>
      <p className="mt-1 text-sm text-slate-600">{t("verify.correct.intro", { id: report.report_id })}</p>

      {blocked ? (
        <p className="mt-3 rounded-lg border border-slate-300 bg-slate-50 p-2 text-sm text-slate-800">
          <span aria-hidden="true">ⓘ </span>
          {t("verify.correct.already_superseded", { id: report.superseded_by })}
        </p>
      ) : (
        <form noValidate onSubmit={onSubmit} className="mt-3 space-y-3">
          <FormField
            id={`${baseId}-name`}
            label={t("verify.correct.reviewer_name")}
            error={nameError ? t("verify.correct.reviewer_name_required") : undefined}
            value={name}
            onChange={(v) => {
              setName(v);
              setNameError(false);
            }}
          />
          <button
            type="submit"
            disabled={mutation.isPending || !auditId}
            aria-busy={mutation.isPending}
            className="inline-flex min-h-11 items-center gap-2 rounded-lg bg-slate-800 px-4 font-semibold text-white hover:bg-slate-900 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700 disabled:opacity-60"
          >
            {mutation.isPending ? t("verify.correct.submitting") : t("verify.correct.submit")}
          </button>
        </form>
      )}

      <div aria-live="polite" className="mt-2">
        {mutation.isError && (
          <p role="alert" className="text-sm font-medium text-red-800">
            <span aria-hidden="true">⚠ </span>
            {t(verifyErrorKey(mutation.error))}
          </p>
        )}

      </div>
    </section>
  );
}
