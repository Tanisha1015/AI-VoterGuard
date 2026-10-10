/** Tiny toast store (no dependency): components call pushToast, <Toaster /> renders the list. */
import { ApiError, NetworkError } from "../api/client";

export interface Toast {
  id: number;
  /** i18n key under "toast.*"; translated when rendered so a language switch applies at once. */
  key: string;
}

type Listener = () => void;

const MAX_TOASTS = 3;
let nextId = 1;
let toasts: readonly Toast[] = [];
const listeners = new Set<Listener>();

function emit(): void {
  listeners.forEach((listener) => listener());
}

/** Subscribe to changes (for useSyncExternalStore). Returns the unsubscribe function. */
export function subscribeToasts(listener: Listener): () => void {
  listeners.add(listener);
  return () => {
    listeners.delete(listener);
  };
}

/** Current toasts, oldest first. The array identity only changes when the list changes. */
export function getToasts(): readonly Toast[] {
  return toasts;
}

/** Show a toast for an i18n key such as "toast.network". Keeps at most three on screen. */
export function pushToast(key: string): void {
  toasts = [...toasts, { id: nextId, key }].slice(-MAX_TOASTS);
  nextId += 1;
  emit();
}

/** Remove one toast. */
export function dismissToast(id: number): void {
  toasts = toasts.filter((t) => t.id !== id);
  emit();
}

/** Remove every toast (used by tests). */
export function clearToasts(): void {
  toasts = [];
  emit();
}

/** Short, calm toast key for a failed request. Detailed wording stays inline next to the form. */
export function toastKeyFor(error: unknown): string {
  if (error instanceof NetworkError) return "toast.network";
  if (error instanceof ApiError) {
    if (error.status === 429) return "toast.rate_limited";
    if (error.status >= 502 && error.status <= 504) return "toast.ledger";
  }
  return "toast.generic";
}
