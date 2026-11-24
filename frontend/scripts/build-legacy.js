// Assemble the original pages as an optional rollback bundle from shared assets.
import { cp, mkdir, copyFile } from "node:fs/promises";
import { fileURLToPath } from "node:url";

const root = new URL("../", import.meta.url);
const path = (relative) => fileURLToPath(new URL(relative, root));
await mkdir(path("dist-legacy/css"), { recursive: true });
await cp(path("legacy"), path("dist-legacy"), { recursive: true });
await cp(path("public"), path("dist-legacy"), { recursive: true });
await cp(path("js"), path("dist-legacy/js"), { recursive: true });
await copyFile(path("src/assets/index.css"), path("dist-legacy/css/style.css"));
