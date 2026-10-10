import { useTranslation } from "react-i18next";
import ComingSoon from "./ComingSoon";

/** Reviewer dashboard (route "/reviewer"). Placeholder for now. */
export default function ReviewerDashboard() {
  const { t } = useTranslation();
  return <ComingSoon title={t("placeholder.reviewer_title")} />;
}
