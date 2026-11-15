import { defineConfig } from "vite";
import react from "@vitejs/plugin-react";

export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // In development the browser calls http://localhost:5173/api/... and Vite
    // forwards it to Flask. The browser sees one origin, so there is no CORS
    // issue while developing.
    proxy: {
      "/api": "http://127.0.0.1:5000",
    },
  },
});
