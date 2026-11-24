import { defineConfig, loadEnv } from "vite";
import { readFile, writeFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const pages = [
  "movies",
  "movie",
  "screenings",
  "seats",
  "booking",
  "bookings",
  "login",
  "register",
  "admin-movies",
  "admin-screenings",
  "admin-bookings",
];
const routes = new Set(pages.map((name) => "/" + name + ".html"));
const dist = new URL("./dist/", import.meta.url);

export default defineConfig(({ mode }) => {
  const settings = loadEnv(
    mode,
    fileURLToPath(new URL("../", import.meta.url)),
    "API_BASE_URL",
  );
  const api = new URL(
    process.env.API_BASE_URL ||
      settings.API_BASE_URL ||
      "http://localhost:5000",
  );
  if (
    !["http:", "https:"].includes(api.protocol) ||
    api.href !== api.origin + "/"
  ) {
    throw new Error("API_BASE_URL must be an HTTP(S) origin");
  }
  return {
    build: {
      rollupOptions: {
        output: {
          entryFileNames: "assets/cinema.js",
          assetFileNames: (asset) =>
            asset.names?.some((name) => name.endsWith(".css"))
              ? "assets/cinema.css"
              : "assets/[name]-[hash][extname]",
        },
      },
    },
    server: { strictPort: true },
    plugins: [
      {
        name: "cinema-page-urls",
        configureServer(server) {
          server.middlewares.use((req, res, next) => {
            const path = req.url.split("?")[0];
            if (path === "/config.js") {
              res.setHeader("Content-Type", "text/javascript");
              res.setHeader("Cache-Control", "no-store");
              res.end(
                "window.APP_CONFIG = Object.freeze(" +
                  JSON.stringify({ apiBaseUrl: api.origin }) +
                  ");",
              );
            } else {
              if (routes.has(path)) req.url = "/index.html";
              next();
            }
          });
        },
        async writeBundle() {
          const html = await readFile(new URL("index.html", dist));
          await Promise.all(
            pages.map((page) => writeFile(new URL(page + ".html", dist), html)),
          );
        },
      },
    ],
  };
});
