/// <reference types="vitest/config" />
import react from "@vitejs/plugin-react";
import { defineConfig, loadEnv } from "vite";

export default defineConfig(({ mode }) => {
  const env = loadEnv(mode, process.cwd(), "");
  return {
    plugins: [react()],
    server: {
      port: 5173,
      // En développement, /api est relayé vers le backend FastAPI.
      proxy: { "/api": { target: env.API_PROXY_TARGET || "http://127.0.0.1:8000", changeOrigin: true } },
    },
    build: { sourcemap: true, chunkSizeWarningLimit: 600 },
    test: { environment: "node", include: ["src/**/*.test.ts"] },
  };
});
