import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup } from "@testing-library/react";
import "../i18n";
import { setLang } from "../i18n";

afterEach(async () => {
  cleanup();
  window.localStorage.clear();
  await setLang("en");
});
