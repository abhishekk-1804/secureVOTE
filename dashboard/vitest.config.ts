import { defineConfig } from "vitest/config";
import react from "@vitejs/plugin-react";
import path from "path";

export default defineConfig({
  plugins: [react()],
  test: {
    environment: "jsdom",
    globals: true,
    setupFiles: ["./vitest.setup.ts"],
    alias: {
      "@/app/audit/page": path.resolve(__dirname, "./app/(officer)/audit/page.tsx"),
      "@/app/devices/page": path.resolve(__dirname, "./app/(officer)/devices/page.tsx"),
      "@/app/results/page": path.resolve(__dirname, "./app/(officer)/results/page.tsx"),
      "@/app/security/page": path.resolve(__dirname, "./app/(officer)/security/page.tsx"),
      "@/app/command/page": path.resolve(__dirname, "./app/(officer)/command/page.tsx"),
      "@": path.resolve(__dirname, "./"),
    },
  },
});
