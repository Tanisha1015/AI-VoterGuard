import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { BoothSummary, Detector, Flag, Severity } from "../api/types";
import { formatPercent } from "../lib/format";
import { DETECTORS, SEVERITIES, SORT_COLUMNS, filterBooths, sortBooths, type SortDir, type SortKey } from "../lib/booths";

const selectClass =
  "mt-1 block min-h-11 w-full rounded-lg border-2 border-slate-400 bg-white px-2 text-sm focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700";

/** Sortable, filterable booth table. Sorting uses header buttons with aria-sort. */
export default function BoothTable({ booths, flags }: { booths: BoothSummary[]; flags: Flag[] }) {
  const { t } = useTranslation();
  const [sortKey, setSortKey] = useState<SortKey>("risk_score");
  const [sortDir, setSortDir] = useState<SortDir>("desc");
  const [severity, setSeverity] = useState<Severity | "">("");
  const [detector, setDetector] = useState<Detector | "">("");

  const rows = useMemo(
    () => sortBooths(filterBooths(booths, flags, severity, detector), sortKey, sortDir),
    [booths, flags, severity, detector, sortKey, sortDir],
  );

  function onSort(key: SortKey) {
    if (key === sortKey) {
      setSortDir((d) => (d === "asc" ? "desc" : "asc"));
    } else {
      setSortKey(key);
      setSortDir(key === "part_no" ? "asc" : "desc");
    }
  }

  return (
    <section aria-labelledby="booth-table-title" className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 id="booth-table-title" className="text-lg font-semibold text-slate-900">
        {t("reviewer.table.title")}
      </h2>

      <div className="mt-3 grid gap-3 sm:grid-cols-2">
        <label className="block text-sm font-medium text-slate-800">
          {t("reviewer.table.severity_filter")}
          <select className={selectClass} value={severity} onChange={(e) => setSeverity(e.target.value as Severity | "")}>
            <option value="">{t("common.all")}</option>
            {SEVERITIES.map((s) => (
              <option key={s} value={s}>
                {t(`reviewer.severity.${s}`)}
              </option>
            ))}
          </select>
        </label>
        <label className="block text-sm font-medium text-slate-800">
          {t("reviewer.table.detector_filter")}
          <select className={selectClass} value={detector} onChange={(e) => setDetector(e.target.value as Detector | "")}>
            <option value="">{t("common.all")}</option>
            {DETECTORS.map((d) => (
              <option key={d} value={d}>
                {t(`reviewer.detector.${d}`)}
              </option>
            ))}
          </select>
        </label>
      </div>

      <div className="mt-3 overflow-x-auto">
        <table className="w-full min-w-[32rem] border-collapse text-sm">
          <caption className="sr-only">{t("reviewer.table.caption")}</caption>
          <thead>
            <tr className="border-b-2 border-slate-300 text-left">
              {SORT_COLUMNS.map((col) => {
                const active = col === sortKey;
                const label = t(`reviewer.table.${col}`);
                return (
                  <th key={col} scope="col" aria-sort={active ? (sortDir === "asc" ? "ascending" : "descending") : "none"} className="p-0">
                    <button
                      type="button"
                      onClick={() => onSort(col)}
                      aria-label={t("reviewer.table.sort_by", { column: label })}
                      className="flex min-h-11 w-full items-center gap-1 px-2 font-semibold text-slate-800 hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-offset-[-2px] focus-visible:outline-blue-700"
                    >
                      {label}
                      <span aria-hidden="true" className="text-xs text-slate-500">
                        {active ? (sortDir === "asc" ? "▲" : "▼") : "↕"}
                      </span>
                    </button>
                  </th>
                );
              })}
            </tr>
          </thead>
          <tbody>
            {rows.map((b) => (
              <tr key={b.part_no} className="border-b border-slate-200" data-testid="booth-row">
                <th scope="row" className="px-2 py-1 text-left font-semibold">
                  <Link
                    to={`/reviewer/booth/${b.part_no}`}
                    aria-label={t("reviewer.table.open_booth", { part: b.part_no })}
                    className="inline-flex min-h-11 min-w-11 items-center text-blue-800 underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
                  >
                    {b.part_no}
                    {b.flagged && <span aria-hidden="true" className="ml-1">⚑</span>}
                  </Link>
                </th>
                <td className="px-2 py-1">{b.removed}</td>
                <td className="px-2 py-1">{formatPercent(b.deletion_rate)}</td>
                <td className="px-2 py-1">{b.risk_score}</td>
                <td className="px-2 py-1">{b.flag_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
        {rows.length === 0 && <p className="p-3 text-slate-700">{t("reviewer.table.empty")}</p>}
      </div>
    </section>
  );
}
