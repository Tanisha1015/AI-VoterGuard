import { useTranslation } from "react-i18next";
import type { AgeBand } from "../../api/types";
import { formatPercent } from "../../lib/format";
import BarChartCard from "./BarChartCard";

const BANDS: AgeBand[] = ["18-25", "26-35", "36-45", "46-60", "61-80", "80+"];

/** Share of removals by age band. */
export default function AgeBandChart({ shares }: { shares: Record<AgeBand, number> }) {
  const { t } = useTranslation();
  const data = BANDS.map((b) => ({ label: b, value: shares[b] }));
  return <BarChartCard title={t("booth.chart_age")} data={data} format={formatPercent} />;
}
