import { useTranslation } from "react-i18next";
import type { Severity } from "../api/types";

const STYLE: Record<Severity, { icon: string; cls: string }> = {
  LOW: { icon: "●", cls: "border-slate-400 bg-slate-50 text-slate-800" },
  MEDIUM: { icon: "◆", cls: "border-amber-400 bg-amber-50 text-amber-900" },
  HIGH: { icon: "▲", cls: "border-orange-500 bg-orange-50 text-orange-900" },
};

/** Severity indicator with icon + text (never colour alone). */
export default function SeverityChip({ severity }: { severity: Severity }) {
  const { t } = useTranslation();
  const style = STYLE[severity];
  return (
    <span className={`inline-flex items-center gap-1 rounded-full border px-2 py-0.5 text-xs font-semibold ${style.cls}`}>
      <span aria-hidden="true">{style.icon}</span>
      {t(`reviewer.severity.${severity}`)}
    </span>
  );
}
