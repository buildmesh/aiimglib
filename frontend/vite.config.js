import { defineConfig } from "vite";

export default defineConfig({
  root: __dirname,
  build: {
    outDir: "../app/static",
    emptyOutDir: true,
    rollupOptions: {
      input: "index.html",
    },
  },
});
