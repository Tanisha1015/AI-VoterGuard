import { useParams } from "react-router-dom";
import { useTranslation } from "react-i18next";
import ComingSoon from "./ComingSoon";

/** Booth detail (route "/reviewer/booth/:part"). Placeholder for now. */
export default function BoothDetail() {
  const { t } = useTranslation();
  const { part = "" } = useParams<{ part: string }>();
  return <ComingSoon title={t("placeholder.booth_title", { part })} />;
}
