import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// 开发时 /api 代理到后端 8000；构建产物 dist 由后端静态托管。
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    proxy: {
      "/api": {
        target: "http://127.0.0.1:8000",
        changeOrigin: true,
      },
    },
  },
  build: {
    outDir: "dist",
  },
});
