import { cpSync, existsSync, mkdirSync, readdirSync, rmSync } from "node:fs";
import { join } from "node:path";

const source = join("..", ".exchange", "generated", "zips");
const target = join("public", "downloads");

rmSync(target, { force: true, recursive: true });
mkdirSync(target, { recursive: true });

if (existsSync(source)) {
  for (const entry of readdirSync(source)) {
    if (entry.endsWith(".zip")) {
      cpSync(join(source, entry), join(target, entry));
    }
  }
}
