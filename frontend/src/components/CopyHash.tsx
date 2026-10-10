import { useState } from "react";
import { useTranslation } from "react-i18next";
import { shortHash } from "../lib/format";

type CopyState = "idle" | "copied" | "failed";

interface CopyHashProps {
  value: string;
  /** Accessible name for the copy button, e.g. "Copy computed hash". Defaults to "Copy hash". */
  copyLabel?: string;
  testId?: string;
}

/** Shortened hash (full value in the title) with a copy-to-clipboard button and live feedback. */
export default function CopyHash({ value, copyLabel, testId }: CopyHashProps) {
  const { t } = useTranslation();
  const [state, setState] = useState<CopyState>("idle");

  async function copy() {
    try {
      await navigator.clipboard.writeText(value);
      setState("copied");
    } catch {
      setState("failed");
    }
  }

  return (
    <span className="inline-flex flex-wrap items-center gap-2">
      <code title={value} className="font-mono break-all" data-testid={testId}>
        {shortHash(value)}
      </code>
      <button
        type="button"
        onClick={() => void copy()}
        className="inline-flex min-h-11 items-center rounded-lg border border-slate-400 bg-white px-3 text-sm hover:bg-slate-100 focus-visible:outline-2 focus-visible:outline-offset-2 focus-visible:outline-blue-700"
      >
        {copyLabel ?? t("reviewer.report.copy")}
      </button>
      <span aria-live="polite" className="text-sm text-slate-700">
        {state === "copied" ? t("reviewer.report.copied") : state === "failed" ? t("reviewer.report.copy_failed") : ""}
      </span>
    </span>
  );
}
