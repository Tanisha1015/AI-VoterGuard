import { useTranslation } from "react-i18next";
import ComingSoon from "./ComingSoon";

/** Report verification (route "/verify"). Placeholder for now. */
export default function Verify() {
  const { t } = useTranslation();
  return <ComingSoon title={t("placeholder.verify_title")} />;
}
