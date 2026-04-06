import { pathToFileURL } from "node:url";

export async function importFresh(relativePath) {
  const url = new URL(
    `${pathToFileURL(process.cwd()).href}${relativePath.replace(/^\.\//, "")}`
  );
  url.searchParams.set("t", `${Date.now()}-${Math.random()}`);
  return import(url.href);
}
