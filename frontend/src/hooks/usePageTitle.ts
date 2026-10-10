import { useEffect } from "react";
import { useTranslation } from "react-i18next";

/** Set document.title to "<page title> · <app name>" in the active language. */
export function usePageTitle(title: string): void {
  const { t } = useTranslation();
  const appName = t("app.name");

  useEffect(() => {
    document.title = title ? `${title} · ${appName}` : appName;
  }, [title, appName]);
}
