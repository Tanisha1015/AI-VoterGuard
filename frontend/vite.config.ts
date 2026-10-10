/// <reference types="vitest/config" />
import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";
import tailwindcss from "@tailwindcss/vite";

// Vite + Tailwind v4 (official @tailwindcss/vite plugin) + Vitest config.
export default defineConfig({
  plugins: [react(), tailwindcss()],
  server: { port: 5173 },
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./src/test/setup.ts"],
    css: false,
    // Full-app tests lazy-load the reviewer pages (Recharts); allow headroom when files run in parallel.
    testTimeout: 15000,
    env: {
      VITE_USE_MOCKS: "true",
      VITE_MOCK_DELAY_MS: "0",
    },
  },
});
