/// <reference types="vite/client" />

interface ImportMetaEnv {
  readonly VITE_CORE_URL?: string;
  readonly VITE_TRUST_URL?: string;
  readonly VITE_AUDIT_ID?: string;
  readonly VITE_USE_MOCKS?: string;
  /** Test-only override for the mock delay (defaults to 300 ms). */
  readonly VITE_MOCK_DELAY_MS?: string;
}

interface ImportMeta {
  readonly env: ImportMetaEnv;
}
