/**
 * Routes API requests to the synthetic fixtures in src/mocks by URL pattern.
 * Used only when VITE_USE_MOCKS === "true". Unknown routes raise a clear error.
 */
import type { Service } from "./client";
import type { CitizenLookupRequest, Flag, FlagList, ReviewRequest } from "./types";

import auditSummary from "../mocks/audit_summary.json";
import booths from "../mocks/booths.json";
import booth17 from "../mocks/booth_17.json";
import flags from "../mocks/flags.json";
import exportPayload from "../mocks/export.json";
import citizenPresent from "../mocks/citizen_present.json";
import citizenRemoved from "../mocks/citizen_removed.json";
import citizenAdded from "../mocks/citizen_added.json";
import citizenNotFound from "../mocks/citizen_not_found.json";
import citizenAmbiguous from "../mocks/citizen_ambiguous.json";
import reportCreated from "../mocks/report_created.json";
import reportList from "../mocks/report_list.json";
import verifyMatch from "../mocks/verify_match.json";
import verifyMismatch from "../mocks/verify_mismatch.json";
import chainStatus from "../mocks/chain_status.json";

/** Error thrown when no fixture matches a request. */
export class MockRouteError extends Error {
  constructor(method: string, service: Service, path: string) {
    super(`MOCK_ROUTE_NOT_FOUND: no mock for ${method} ${service}:${path}`);
    this.name = "MockRouteError";
  }
}

type Handler = (match: RegExpMatchArray, body: unknown, query: URLSearchParams) => unknown;

interface Route {
  service: Service;
  method: string;
  pattern: RegExp;
  handler: Handler;
}

/** Deep copy so callers can never mutate the shared fixture objects. */
function clone<T>(value: T): T {
  return JSON.parse(JSON.stringify(value)) as T;
}

/** Mock rule for citizen lookup, keyed on the (lower-cased) name. */
export function pickCitizenFixture(req: Partial<CitizenLookupRequest> | undefined): unknown {
  const name = (req?.name ?? "").toLowerCase();
  if (name.includes("sunita")) return citizenRemoved;
  if (name.includes("ambig")) return citizenAmbiguous;
  if (name.includes("none")) return citizenNotFound;
  if (name.includes("added")) return citizenAdded;
  return citizenPresent;
}

function pickVerifyFixture(body: unknown): unknown {
  if (typeof FormData !== "undefined" && body instanceof FormData) {
    const file = body.get("file");
    const fileName = file instanceof File ? file.name.toLowerCase() : "";
    if (fileName.includes("mismatch") || fileName.includes("tamper")) return verifyMismatch;
  }
  return verifyMatch;
}

function filterFlags(query: URLSearchParams): FlagList {
  const all = clone(flags as FlagList).items;
  const part = query.get("part_no");
  const severity = query.get("severity");
  const detector = query.get("detector");
  return {
    items: all.filter(
      (f) =>
        (part === null || f.part_no === Number(part)) &&
        (severity === null || f.severity === severity) &&
        (detector === null || f.detector === detector),
    ),
  };
}

function reviewFlag(flagId: string, body: unknown): Flag {
  const found = (flags as FlagList).items.find((f) => f.flag_id === flagId);
  if (!found) throw new Error(`MOCK_FLAG_NOT_FOUND: ${flagId}`);
  const req = body as ReviewRequest;
  return {
    ...clone(found),
    review: { status: req.status, note: req.note ?? null, reviewed_at: new Date().toISOString() },
  };
}

const AUDIT = "/api/audits/([^/]+)";

const routes: Route[] = [
  { service: "core", method: "GET", pattern: new RegExp(`^${AUDIT}/summary$`), handler: () => auditSummary },
  { service: "core", method: "GET", pattern: new RegExp(`^${AUDIT}/booths$`), handler: () => booths },
  {
    service: "core",
    method: "GET",
    pattern: new RegExp(`^${AUDIT}/booths/(\\d+)$`),
    // Only booth 17 has a detailed fixture; reuse it with the requested part number.
    handler: (m) => ({ ...clone(booth17), part_no: Number(m[2]) }),
  },
  { service: "core", method: "GET", pattern: new RegExp(`^${AUDIT}/flags$`), handler: (_m, _b, q) => filterFlags(q) },
  {
    service: "core",
    method: "PUT",
    pattern: new RegExp(`^${AUDIT}/flags/([^/]+)/review$`),
    handler: (m, b) => reviewFlag(decodeURIComponent(m[2] ?? ""), b),
  },
  { service: "core", method: "GET", pattern: new RegExp(`^${AUDIT}/export$`), handler: () => exportPayload },
  {
    service: "core",
    method: "POST",
    pattern: /^\/api\/citizen\/lookup$/,
    handler: (_m, b) => pickCitizenFixture(b as Partial<CitizenLookupRequest>),
  },
  { service: "trust", method: "POST", pattern: /^\/api\/reports$/, handler: () => reportCreated },
  { service: "trust", method: "GET", pattern: /^\/api\/reports$/, handler: () => reportList },
  { service: "trust", method: "POST", pattern: /^\/api\/reports\/verify$/, handler: (_m, b) => pickVerifyFixture(b) },
  {
    service: "trust",
    method: "GET",
    pattern: /^\/api\/reports\/([^/]+)$/,
    handler: (m) => {
      const id = decodeURIComponent(m[1] ?? "");
      const listed = reportList.items.find((r) => r.report_id === id);
      return { ...clone(reportCreated), report_id: id, superseded_by: listed?.superseded_by ?? null };
    },
  },
  { service: "trust", method: "GET", pattern: /^\/api\/chain\/status$/, handler: () => chainStatus },
];

/** Resolve a request against the mock table, or throw MockRouteError. */
export function resolveMock<T>(service: Service, method: string, fullPath: string, body: unknown): T {
  const [path = "", queryString = ""] = fullPath.split("?");
  const query = new URLSearchParams(queryString);
  for (const route of routes) {
    if (route.service !== service || route.method !== method) continue;
    const match = path.match(route.pattern);
    if (match) return clone(route.handler(match, body, query)) as T;
  }
  throw new MockRouteError(method, service, fullPath);
}
