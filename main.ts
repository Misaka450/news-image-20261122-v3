import { copyFileSync, mkdirSync } from "node:fs";
import { dirname, join } from "node:path";

const outputDir: string = process.env.MAKEFUN_OUTPUT_DIR || "/output";
mkdirSync(outputDir, { recursive: true });

const scriptDir: string = dirname(new URL(import.meta.url).pathname);
const sourcePath: string = join(scriptDir, "entry.png");
const targetPath: string = join(outputDir, "entry.png");

copyFileSync(sourcePath, targetPath);
console.log(targetPath);
