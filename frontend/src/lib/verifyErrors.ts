import { ApiError, NetworkError } from "../api/client";

/** Map a trust-service error to an i18n key under verify.errors. */
export function verifyErrorKey(error: unknown): string {
  if (error instanceof ApiError) {
    if (error.status === 404) return "verify.errors.file_not_found";
    if (error.status === 422) return "verify.errors.report_id_required";
    if (error.status === 409) return "verify.errors.conflict";
    if (error.status >= 502 && error.status <= 504) return "verify.errors.ledger";
  }
  if (error instanceof NetworkError) return "verify.errors.network";
  return "verify.errors.generic";
}
