import { useTranslation } from "react-i18next";

/** Calm loading indicator. */
export function Loading() {
  const { t } = useTranslation();
  return (
    <p role="status" className="flex items-center gap-2 text-slate-700">
      <span aria-hidden="true" className="h-4 w-4 animate-spin rounded-full border-2 border-slate-500 border-t-transparent" />
      {t("common.loading")}
    </p>
  );
}

/** Friendly empty state: a dashed box with a short title and an optional hint. */
export function EmptyState({ title, hint, testId }: { title: string; hint?: string; testId?: string }) {
  return (
    <div
      role="status"
      data-testid={testId}
      className="rounded-xl border-2 border-dashed border-slate-300 bg-white p-5 text-center text-slate-800"
    >
      <p aria-hidden="true" className="text-2xl text-slate-500">
        ○
      </p>
      <p className="mt-1 font-medium">{title}</p>
      {hint && <p className="mt-1 text-sm text-slate-600">{hint}</p>}
    </div>
  );
}

/** Neutral error box with optional retry. */
export function LoadError({ message, onRetry }: { message?: string; onRetry?: () => void }) {
  const { t } = useTranslation();
  return (
    <div role="alert" className="rounded-xl border-2 border-slate-300 bg-white p-4 text-slate-800">
      <p>
        <span aria-hidden="true">ⓘ </span>
        {message ?? t("common.load_error")}
      </p>
      {onRetry && (
        <button
          type="button"
          onClick={onRetry}
          className="mt-2 inline-flex min-h-11 items-center rounded-lg border-2 border-blue-700 px-4 font-medium text-blue-800 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
        >
          {t("common.retry")}
        </button>
      )}
    </div>
  );
}
