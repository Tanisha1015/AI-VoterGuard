import { useId } from "react";
import { useTranslation } from "react-i18next";
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

export interface BarDatum {
  label: string;
  value: number;
}

interface BarChartCardProps {
  title: string;
  data: BarDatum[];
  /** Formats values for axis, tooltip and the data table. */
  format?: (value: number) => string;
}

/**
 * Single-hue Recharts bar chart with a visible title and a collapsible data table,
 * so the same information is available without relying on the graphic.
 */
export default function BarChartCard({ title, data, format = (v) => String(v) }: BarChartCardProps) {
  const { t } = useTranslation();
  const captionId = useId();

  return (
    <figure aria-labelledby={captionId} className="rounded-xl border border-slate-200 bg-white p-3 shadow-sm">
      <figcaption id={captionId} className="text-sm font-semibold text-slate-900">
        {title}
      </figcaption>
      <div className="mt-2 h-56 w-full" aria-hidden="true">
        <ResponsiveContainer width="100%" height="100%">
          <BarChart data={data} margin={{ top: 8, right: 8, bottom: 8, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="#e2e8f0" />
            <XAxis dataKey="label" tick={{ fontSize: 12, fill: "#334155" }} interval={0} />
            <YAxis tickFormatter={format} tick={{ fontSize: 12, fill: "#334155" }} width={48} />
            <Tooltip formatter={(v) => format(Number(v))} />
            <Bar dataKey="value" fill="#1d4ed8" radius={[4, 4, 0, 0]} isAnimationActive={false} />
          </BarChart>
        </ResponsiveContainer>
      </div>
      <details className="mt-2 text-sm">
        <summary className="inline-flex min-h-11 cursor-pointer items-center text-blue-800 underline focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700">
          {t("booth.chart_table")}
        </summary>
        <table className="mt-1 w-full border-collapse">
          <caption className="sr-only">{title}</caption>
          <thead>
            <tr className="border-b border-slate-300 text-left">
              <th scope="col" className="py-1">{t("booth.chart_category")}</th>
              <th scope="col" className="py-1">{t("booth.chart_value")}</th>
            </tr>
          </thead>
          <tbody>
            {data.map((d) => (
              <tr key={d.label} className="border-b border-slate-100">
                <th scope="row" className="py-1 text-left font-normal">{d.label}</th>
                <td className="py-1">{format(d.value)}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </details>
    </figure>
  );
}
