import { useQuery } from "@tanstack/react-query";
import { getAudits } from "../api/core";

export const AUDITS_QUERY_KEY = ["audits"] as const;

export interface CurrentAudit {
  /** First audit from GET /api/audits, or null when none exist yet. */
  auditId: string | null;
  acName: string | null;
  isLoading: boolean;
  isError: boolean;
  error: unknown;
}

/**
 * Resolve the audit the reviewer works on: the first item of GET /api/audits.
 * In mock mode the list is derived from the summary fixture by the mock router.
 */
export function useCurrentAudit(): CurrentAudit {
  const query = useQuery({ queryKey: AUDITS_QUERY_KEY, queryFn: getAudits, staleTime: 60_000 });
  const first = query.data?.items[0];
  return {
    auditId: first?.audit_id ?? null,
    acName: first?.ac_name ?? null,
    isLoading: query.isLoading,
    isError: query.isError,
    error: query.error,
  };
}
