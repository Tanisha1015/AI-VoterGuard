import { useEffect, useSyncExternalStore } from "react";
import { useTranslation } from "react-i18next";
import { dismissToast, getToasts, subscribeToasts, type Toast } from "../lib/toast";

export const TOAST_SECONDS = 7;

function ToastItem({ toast }: { toast: Toast }) {
  const { t } = useTranslation();

  useEffect(() => {
    const timer = window.setTimeout(() => dismissToast(toast.id), TOAST_SECONDS * 1000);
    return () => window.clearTimeout(timer);
  }, [toast.id]);

  return (
    <li className="flex items-start gap-2 rounded-lg border-2 border-slate-700 bg-white p-3 text-slate-900 shadow-lg">
      <span aria-hidden="true">ⓘ</span>
      <span className="min-w-0 flex-1 break-words" data-testid="toast-text">
        {t(toast.key)}
      </span>
      <button
        type="button"
        onClick={() => dismissToast(toast.id)}
        aria-label={t("toast.dismiss")}
        className="-my-1 -mr-1 inline-flex min-h-11 min-w-11 items-center justify-center rounded-md text-slate-700 hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
      >
        <span aria-hidden="true">✕</span>
      </button>
    </li>
  );
}

/**
 * Bottom-of-screen notices for failed requests. A polite live region (not role="alert", because the
 * detailed message already appears inline next to the control that failed). Dismiss with the button
 * or wait 7 seconds.
 */
export default function Toaster() {
  const toasts = useSyncExternalStore(subscribeToasts, getToasts, getToasts);

  return (
    <div
      aria-live="polite"
      className="pointer-events-none fixed inset-x-0 bottom-0 z-40 flex justify-center px-3 pb-3 sm:justify-end"
    >
      <ul className="pointer-events-auto w-full max-w-sm space-y-2">
        {toasts.map((toast) => (
          <ToastItem key={toast.id} toast={toast} />
        ))}
      </ul>
    </div>
  );
}
