/** Pure helpers for the citizen lookup form: validation, request building, error mapping. */
import { ApiError, NetworkError } from "../api/client";
import type { CitizenLookupRequest, Lang } from "../api/types";

export type FieldName = "name" | "relative_name" | "part_no" | "epic_no";
/** Values are i18n keys. */
export type FieldErrors = Partial<Record<FieldName, string>>;

export interface FormValues {
  name: string;
  relative_name: string;
  part_no: string;
  epic_no: string;
}

export const EMPTY_FORM: FormValues = { name: "", relative_name: "", part_no: "", epic_no: "" };

/** Returns i18n error keys for each invalid field (empty object when valid). */
export function validate(values: FormValues, useEpic: boolean): FieldErrors {
  const errors: FieldErrors = {};
  if (useEpic) {
    if (!values.epic_no.trim()) errors.epic_no = "citizen.errors.epic_required";
    return errors;
  }
  if (!values.name.trim()) errors.name = "citizen.errors.name_required";
  if (!values.relative_name.trim()) errors.relative_name = "citizen.errors.relative_name_required";
  const part = values.part_no.trim();
  if (!part) errors.part_no = "citizen.errors.part_no_required";
  else if (!/^\d+$/.test(part) || Number(part) < 1) errors.part_no = "citizen.errors.part_no_invalid";
  return errors;
}

/** Build the contract request body (CONTRACT.md 6.3, POST /api/citizen/lookup). */
export function buildRequest(values: FormValues, useEpic: boolean, lang: Lang): CitizenLookupRequest {
  if (useEpic) {
    return { name: null, relative_name: null, part_no: null, epic_no: values.epic_no.trim().toUpperCase(), lang };
  }
  return {
    name: values.name.trim(),
    relative_name: values.relative_name.trim(),
    part_no: Number(values.part_no.trim()),
    epic_no: null,
    lang,
  };
}

/** Map a thrown error to a friendly i18n key. */
export function errorKey(error: unknown): string {
  if (error instanceof ApiError && error.status === 429) return "citizen.errors.rate_limited";
  if (error instanceof NetworkError) return "citizen.errors.network";
  return "citizen.errors.generic";
}
