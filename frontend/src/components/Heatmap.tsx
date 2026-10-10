import { Link } from "react-router-dom";
import { useTranslation } from "react-i18next";
import type { BoothSummary } from "../api/types";
import { RISK_STEPS, riskShade } from "../lib/format";

/** Accessible label for a tile, e.g. "Booth 17, risk score 87, 3 flag(s), worth verifying". */
function useTileLabel() {
  const { t } = useTranslation();
  return (b: BoothSummary) =>
    `${t("reviewer.heatmap.tile_label", { part: b.part_no, score: b.risk_score })}, ${
      b.flagged ? t("reviewer.heatmap.tile_flagged", { count: b.flag_count }) : t("reviewer.heatmap.tile_unflagged")
    }`;
}

/**
 * Responsive grid of booth tiles shaded on a single-hue sequential scale by risk_score.
 * Flagged booths get a bold border and a flag mark, so colour is never the only cue.
 */
export default function Heatmap({ booths }: { booths: BoothSummary[] }) {
  const { t } = useTranslation();
  const tileLabel = useTileLabel();
  const ordered = [...booths].sort((a, b) => a.part_no - b.part_no);

  return (
    <section aria-labelledby="heatmap-title" className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <h2 id="heatmap-title" className="text-lg font-semibold text-slate-900">
        {t("reviewer.heatmap.title")}
      </h2>
      <p className="mt-1 text-sm text-slate-600">{t("reviewer.heatmap.intro")}</p>

      <ul className="mt-4 grid grid-cols-3 gap-2 sm:grid-cols-5 md:grid-cols-6 lg:grid-cols-8" data-testid="heatmap">
        {ordered.map((booth) => {
          const shade = riskShade(booth.risk_score);
          return (
            <li key={booth.part_no}>
              <Link
                to={`/reviewer/booth/${booth.part_no}`}
                aria-label={tileLabel(booth)}
                data-testid="heatmap-tile"
                className={`relative flex min-h-16 flex-col items-center justify-center rounded-lg p-2 text-center focus-visible:outline-3 focus-visible:outline-offset-2 focus-visible:outline-amber-500 ${shade.bg} ${shade.text} ${
                  booth.flagged ? "border-4 border-slate-900" : "border border-slate-300"
                }`}
              >
                {booth.flagged && (
                  <span aria-hidden="true" className="absolute right-1 top-0.5 text-sm">
                    ⚑
                  </span>
                )}
                <span className="text-base font-bold">{booth.part_no}</span>
                <span className="text-xs">{booth.risk_score}</span>
              </Link>
            </li>
          );
        })}
      </ul>

      <div className="mt-4 flex flex-wrap items-center gap-x-4 gap-y-2 text-xs text-slate-700">
        <span>{t("reviewer.heatmap.legend")}:</span>
        <ol className="flex">
          {RISK_STEPS.map(([lo, hi]) => {
            const shade = riskShade(lo);
            return (
              <li key={lo} className={`px-2 py-1 ${shade.bg} ${shade.text}`}>
                {lo}–{hi}
              </li>
            );
          })}
        </ol>
        <span className="inline-flex items-center gap-1">
          <span aria-hidden="true" className="inline-block h-4 w-4 rounded border-4 border-slate-900 bg-white" />
          {t("reviewer.heatmap.flagged_legend")}
        </span>
      </div>
    </section>
  );
}
