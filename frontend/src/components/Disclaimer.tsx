import { useTranslation } from "react-i18next";

interface DisclaimerProps {
  /** Already-localised text; defaults to the general disclaimer. */
  text?: string;
}

/** Small, calm note reminding users to confirm details with official sources. */
export default function Disclaimer({ text }: DisclaimerProps) {
  const { t } = useTranslation();
  return (
    <p className="mt-4 border-l-4 border-slate-300 pl-3 text-sm text-slate-600">
      <span aria-hidden="true">ⓘ </span>
      {text ?? t("disclaimer.general")}
    </p>
  );
}
