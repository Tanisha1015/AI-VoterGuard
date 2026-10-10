import { useId, useState } from "react";
import { useMutation, useQueryClient } from "@tanstack/react-query";
import { useTranslation } from "react-i18next";
import { reviewFlag } from "../api/core";
import type { BoothDetail, Flag, ReviewRequest, ReviewStatus } from "../api/types";
import { useLang } from "../i18n";
import { formatDateTime } from "../lib/format";
import { pushToast, toastKeyFor } from "../lib/toast";

export const boothQueryKey = (auditId: string, part: number) => ["booth", auditId, part] as const;

const STATUS_ICON: Record<ReviewStatus, string> = { PENDING: "…", ACCEPTED: "✓", REJECTED: "✕" };

interface ReviewControlsProps {
  auditId: string;
  flag: Flag;
}

type Ctx = { previous: BoothDetail | undefined };

/** Replace one flag inside a cached booth detail. */
function withFlag(detail: BoothDetail, flag: Flag): BoothDetail {
  return { ...detail, flags: detail.flags.map((f) => (f.flag_id === flag.flag_id ? flag : f)) };
}

/**
 * Accept / not-taken-forward buttons + note. Optimistically updates the booth cache,
 * rolls back on error, and refreshes the summary (pending count) after saving.
 */
export default function ReviewControls({ auditId, flag }: ReviewControlsProps) {
  const { t } = useTranslation();
  const lang = useLang();
  const queryClient = useQueryClient();
  const noteId = useId();
  const [note, setNote] = useState(flag.review.note ?? "");
  const key = boothQueryKey(auditId, flag.part_no);

  const mutation = useMutation<Flag, unknown, ReviewRequest, Ctx>({
    mutationFn: (body) => reviewFlag(flag.flag_id, body, auditId),
    onMutate: async (body) => {
      await queryClient.cancelQueries({ queryKey: key });
      const previous = queryClient.getQueryData<BoothDetail>(key);
      if (previous) {
        const optimistic: Flag = { ...flag, review: { status: body.status, note: body.note, reviewed_at: flag.review.reviewed_at } };
        queryClient.setQueryData<BoothDetail>(key, withFlag(previous, optimistic));
      }
      return { previous };
    },
    onError: (err, _body, ctx) => {
      if (ctx?.previous) queryClient.setQueryData(key, ctx.previous);
      pushToast(toastKeyFor(err));
    },
    onSuccess: (saved) => {
      queryClient.setQueryData<BoothDetail>(key, (old) => (old ? withFlag(old, saved) : old));
      void queryClient.invalidateQueries({ queryKey: ["summary", auditId] });
      void queryClient.invalidateQueries({ queryKey: ["flags", auditId] });
    },
  });

  const status = flag.review.status;
  const decide = (next: ReviewStatus) => mutation.mutate({ status: next, note: note.trim() || null });

  const btn =
    "inline-flex min-h-11 items-center gap-1 rounded-lg border-2 px-4 font-medium focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700 disabled:opacity-60";

  return (
    <fieldset className="mt-3 rounded-lg border border-slate-200 bg-slate-50 p-3">
      <legend className="px-1 text-sm font-semibold text-slate-800">{t("booth.review.label")}</legend>

      <label htmlFor={noteId} className="block text-sm font-medium text-slate-800">
        {t("booth.review.note")}
      </label>
      <textarea
        id={noteId}
        rows={2}
        value={note}
        onChange={(e) => setNote(e.target.value)}
        className="mt-1 block w-full rounded-lg border-2 border-slate-400 bg-white p-2 text-base focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
      />

      <div className="mt-2 flex flex-wrap gap-2">
        <button
          type="button"
          aria-pressed={status === "ACCEPTED"}
          disabled={mutation.isPending}
          onClick={() => decide("ACCEPTED")}
          className={`${btn} ${status === "ACCEPTED" ? "border-emerald-700 bg-emerald-700 text-white" : "border-emerald-700 bg-white text-emerald-900"}`}
        >
          <span aria-hidden="true">✓</span>
          {t("booth.review.accept")}
        </button>
        <button
          type="button"
          aria-pressed={status === "REJECTED"}
          disabled={mutation.isPending}
          onClick={() => decide("REJECTED")}
          className={`${btn} ${status === "REJECTED" ? "border-slate-700 bg-slate-700 text-white" : "border-slate-700 bg-white text-slate-900"}`}
        >
          <span aria-hidden="true">✕</span>
          {t("booth.review.reject")}
        </button>
      </div>

      <p aria-live="polite" className="mt-2 text-sm text-slate-800" data-testid={`review-status-${flag.flag_id}`}>
        <span className="text-slate-600">{t("booth.review.status")}: </span>
        <span className="font-semibold">
          <span aria-hidden="true">{STATUS_ICON[status]} </span>
          {mutation.isPending ? t("booth.review.saving") : t(`booth.review.${status}`)}
        </span>
        {!mutation.isPending && flag.review.reviewed_at && (
          <span className="ml-2 text-slate-600">
            {t("booth.review.reviewed_at", { time: formatDateTime(flag.review.reviewed_at, lang) })}
          </span>
        )}
      </p>
      {mutation.isError && (
        <p role="alert" className="mt-1 text-sm font-medium text-red-800">
          <span aria-hidden="true">⚠ </span>
          {t("booth.review.error")}
        </p>
      )}
    </fieldset>
  );
}
