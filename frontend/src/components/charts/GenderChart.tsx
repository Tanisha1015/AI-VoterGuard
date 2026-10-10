import { useTranslation } from "react-i18next";
import type { Gender } from "../../api/types";
import BarChartCard from "./BarChartCard";

const GENDERS: Gender[] = ["F", "M", "O"];

/** Count of removals by gender. */
export default function GenderChart({ counts }: { counts: Record<Gender, number> }) {
  const { t } = useTranslation();
  const data = GENDERS.map((g) => ({ label: t(`booth.gender.${g}`), value: counts[g] }));
  return <BarChartCard title={t("booth.chart_gender")} data={data} />;
}
