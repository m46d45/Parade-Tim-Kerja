import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";
import { defineConfig, type Plugin } from "vite";

const rootDir = path.dirname(fileURLToPath(import.meta.url));

/** Serve /kelas/ as static HTML (avoid SPA fallback to index.html). */
function serveKelas(): Plugin {
  return {
    name: "serve-kelas",
    configureServer(server) {
      server.middlewares.use((req, res, next) => {
        const url = req.url?.split("?")[0] ?? "";
        if (url !== "/kelas" && url !== "/kelas/") return next();
        const file = path.resolve(rootDir, "public/kelas/index.html");
        if (!fs.existsSync(file)) return next();
        res.setHeader("Content-Type", "text/html; charset=utf-8");
        fs.createReadStream(file).pipe(res);
      });
    },
  };
}

export default defineConfig({
  root: ".",
  publicDir: "public",
  plugins: [serveKelas()],
  build: {
    outDir: "dist",
    emptyOutDir: true,
  },
  server: {
    port: 5173,
  },
  test: {
    globals: true,
    environment: "node",
  },
});
