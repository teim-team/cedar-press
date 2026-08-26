import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

// Served at the domain root (cedarpress.ai), so base stays "/".
export default defineConfig({
  plugins: [react()],
  base: "/",
});
