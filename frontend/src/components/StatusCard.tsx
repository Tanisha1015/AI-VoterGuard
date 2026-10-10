import type { ReactNode } from "react";
import type { CitizenStatus } from "../api/types";

/** Styling + icon per status. Colour is never the only indicator: each has an icon and a text title. */
const STYLES: Record<CitizenStatus, { box: string; icon: string }> = {
  PRESENT: { box: "border-emerald-300 bg-emerald-50", icon: "✓" },
  ADDED: { box: "border-emerald-300 bg-emerald-50", icon: "+" },
  REMOVED: { box: "border-amber-300 bg-amber-50", icon: "!" },
  NOT_FOUND: { box: "border-slate-300 bg-white", icon: "?" },
  AMBIGUOUS: { box: "border-slate-300 bg-white", icon: "≈" },
};

interface StatusCardProps {
  status: CitizenStatus;
  title: string;
  statusLabel: string;
  children?: ReactNode;
}

/** Bordered result card with an icon, a heading and arbitrary content. */
export default function StatusCard({ status, title, statusLabel, children }: StatusCardProps) {
  const style = STYLES[status];
  return (
    <article data-status={status} className={`rounded-xl border-2 p-4 shadow-sm sm:p-6 ${style.box}`}>
      <header className="flex items-start gap-3">
        <span
          aria-hidden="true"
          className="flex h-9 w-9 shrink-0 items-center justify-center rounded-full border-2 border-current bg-white text-lg font-bold text-slate-800"
        >
          {style.icon}
        </span>
        <div>
          <p className="text-xs font-semibold uppercase tracking-wide text-slate-600">{statusLabel}</p>
          <h2 className="text-lg font-semibold text-slate-900">{title}</h2>
        </div>
      </header>
      <div className="mt-3 space-y-3 text-slate-800">{children}</div>
    </article>
  );
}
