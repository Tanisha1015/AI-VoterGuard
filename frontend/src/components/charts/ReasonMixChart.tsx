import { useTranslation } from "react-i18next";
import type { Reason, ReasonMix } from "../../api/types";
import { formatPercent } from "../../lib/format";
import BarChartCard from "./BarChartCard";

const REASONS: Reason[] = ["ABSENT", "SHIFTED", "DEAD", "DUPLICATE"];

/** Share of removals by recorded reason. */
export default function ReasonMixChart({ mix }: { mix: ReasonMix }) {
  const { t } = useTranslation();
  const data = REASONS.map((r) => ({ label: t(`booth.reason.${r}`), value: mix[r] }));
  return <BarChartCard title={t("booth.chart_reason")} data={data} format={formatPercent} />;
}
