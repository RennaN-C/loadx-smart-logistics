/* Deployment-only static artifact. Never copies the shared API rewrite or secrets. */
const fs = require("node:fs");
const path = require("node:path");
const crypto = require("node:crypto");
const assert = require("node:assert/strict");

const root = path.resolve(__dirname, "../..");
const source = path.join(root, "frontend/dist");
const destination = path.join(root, ".tmp/3d-planner/preview-artifact");
const original = JSON.parse(fs.readFileSync(path.join(root, "frontend/vercel.json"), "utf8"));
const headers = Object.fromEntries(original.headers[0].headers.map(({ key, value }) => [key, value]));
const config = {
  version: 2,
  framework: null,
  buildCommand: "",
  installCommand: "",
  outputDirectory: "public",
  routes: [
    { src: "/(.*)", headers, continue: true },
    { src: "^/api(?:/.*)?$", status: 503, headers: { "Cache-Control": "no-store", "X-LoadX-Preview": "isolated-3d" } },
    { handle: "filesystem" },
    { src: "/(.*)", dest: "/index.html" },
  ],
};
assert(!JSON.stringify(config).includes("onrender.com"));
assert(config.routes[1].status === 503 && !config.routes[1].dest && !config.routes[1].methods);
assert(config.routes[0].headers["Content-Security-Policy"] === headers["Content-Security-Policy"]);
const manifest = [];
function write(relative, bytes) {
  const target = path.join(destination, relative);
  fs.mkdirSync(path.dirname(target), { recursive: true });
  fs.writeFileSync(target, bytes);
  manifest.push({ file: relative.replaceAll("\\", "/"), size: bytes.length, sha: crypto.createHash("sha1").update(bytes).digest("hex") });
}
function copy(directory, relative = "") {
  for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
    assert(!entry.isSymbolicLink(), "Artifact must not follow symbolic links");
    const next = path.join(relative, entry.name);
    if (entry.isDirectory()) copy(path.join(directory, entry.name), next);
    else {
      assert(!entry.name.startsWith(".") && !entry.name.endsWith(".map"), "Only public build files belong in the artifact");
      const bytes = fs.readFileSync(path.join(directory, entry.name));
      // Both roots are self-contained: works with the existing frontend root
      // setting without changing the shared project's configuration.
      write(path.join("public", next), bytes);
      write(path.join("frontend/public", next), bytes);
    }
  }
}
copy(source);
const encoded = Buffer.from(JSON.stringify(config, null, 2));
write("vercel.json", encoded);
write("frontend/vercel.json", encoded);
assert(manifest.some((file) => file.file === "frontend/public/index.html"));
fs.writeFileSync(path.join(root, ".tmp/3d-planner/preview-manifest.json"), JSON.stringify(manifest, null, 2));
console.log(JSON.stringify({ destination, files: manifest.length, uniqueFiles: new Set(manifest.map((file) => file.sha)).size, apiStatus: 503, sharedProjectSettingsChanged: false }));
