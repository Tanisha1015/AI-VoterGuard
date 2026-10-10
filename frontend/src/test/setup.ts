import "@testing-library/jest-dom/vitest";
import { afterEach } from "vitest";
import { cleanup, configure } from "@testing-library/react";

// Reviewer pages are lazy-loaded (they include Recharts). The first import can exceed the
// default 1 s findBy* timeout when test files run in parallel, so allow more time.
configure({ asyncUtilTimeout: 5000 });
import "../i18n";
import { setLang } from "../i18n";
import { resetMockState } from "../api/mockRouter";

// jsdom has no layout and no ResizeObserver, which Recharts' ResponsiveContainer needs.
// This stub reports a fixed size so charts render in tests without size warnings.
const TEST_CHART_SIZE = { width: 600, height: 224 };

class ResizeObserverStub {
  private readonly callback: ResizeObserverCallback;
  constructor(callback: ResizeObserverCallback) {
    this.callback = callback;
  }
  observe(target: Element): void {
    const entry = {
      target,
      contentRect: { ...TEST_CHART_SIZE, top: 0, left: 0, right: TEST_CHART_SIZE.width, bottom: TEST_CHART_SIZE.height, x: 0, y: 0 },
    } as unknown as ResizeObserverEntry;
    this.callback([entry], this as unknown as ResizeObserver);
  }
  unobserve(): void {}
  disconnect(): void {}
}
(globalThis as unknown as { ResizeObserver: typeof ResizeObserverStub }).ResizeObserver = ResizeObserverStub;

// Give elements a non-zero box so ResponsiveContainer's first measurement is valid.
Object.defineProperty(HTMLElement.prototype, "clientWidth", { configurable: true, get: () => TEST_CHART_SIZE.width });
Object.defineProperty(HTMLElement.prototype, "clientHeight", { configurable: true, get: () => TEST_CHART_SIZE.height });

afterEach(async () => {
  cleanup();
  resetMockState();
  window.localStorage.clear();
  await setLang("en");
});
