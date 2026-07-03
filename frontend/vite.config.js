import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Dev server proxies /api → FastAPI backend so the frontend calls same-origin
// relative URLs in both dev and production. Override the target with
// VITE_API_TARGET if the backend runs elsewhere.
const API_TARGET = process.env.VITE_API_TARGET || "http://localhost:8000";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: API_TARGET,
        changeOrigin: true,
      },
    },
  },
});
