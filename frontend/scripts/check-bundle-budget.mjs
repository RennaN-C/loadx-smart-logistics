import { readdir, readFile } from "node:fs/promises";
import { gzipSync } from "node:zlib";

const LOAD_VIEWER_GZIP_BUDGET_BYTES = 250 * 1024;
const assetsDirectory = new URL("../dist/assets/", import.meta.url);
const assetNames = await readdir(assetsDirectory);
const loadViewerAssets = assetNames.filter(
  (assetName) => assetName.startsWith("LoadViewer-") && assetName.endsWith(".js"),
);

if (loadViewerAssets.length !== 1) {
  throw new Error(
    `Expected one LoadViewer JavaScript chunk, found ${loadViewerAssets.length}.`,
  );
}

const [loadViewerAsset] = loadViewerAssets;
const bundle = await readFile(new URL(loadViewerAsset, assetsDirectory));
const gzipBytes = gzipSync(bundle, { level: 9 }).byteLength;
const gzipKibibytes = (gzipBytes / 1024).toFixed(1);

if (gzipBytes > LOAD_VIEWER_GZIP_BUDGET_BYTES) {
  throw new Error(
    `LoadViewer is ${gzipKibibytes} KiB gzip; budget is 250 KiB.`,
  );
}

process.stdout.write(
  `Bundle budget passed: LoadViewer ${gzipKibibytes} KiB gzip <= 250 KiB.\n`,
);
