import { fileURLToPath, URL } from "node:url";
import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";
import { viteStaticCopy } from "vite-plugin-static-copy";

// Short git SHA of the build (injected by the Dockerfile via APP_GIT_HASH;
// falls back to "dev" in local dev). Shown in the app footer so you can tell
// which version is running on a phone.
const APP_GIT_HASH = process.env.APP_GIT_HASH || "dev";

export default defineConfig({
  define: {
    "import.meta.env.APP_GIT_HASH": JSON.stringify(APP_GIT_HASH),
  },
  plugins: [
    vue(),
    viteStaticCopy({
      targets: [
        { src: "public/sw.js", dest: "." },
        { src: "public/manifest.webmanifest", dest: "." },
        { src: "public/icon-192.png", dest: "." },
        { src: "public/icon-512.png", dest: "." },
      ],
    }),
  ],
  resolve: {
    alias: {
      "@": fileURLToPath(new URL("./src", import.meta.url)),
    },
  },
  server: {
    port: 5173,
    proxy: {
      "/api": { target: "http://localhost:8983", changeOrigin: true },
      "/ws": { target: "ws://localhost:8983", ws: true },
      "/uploads": { target: "http://localhost:8983" },
    },
  },
  build: {
    outDir: "dist",
    assetsDir: "assets",
  },
});
