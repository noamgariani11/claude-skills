"use strict";

// Resolve the newest stable Playwright API deterministically. MCP/npx caches
// commonly contain several versions; directory iteration order is not a
// version policy and can select an API whose expected browser revision is not
// installed.
const fs = require("node:fs");
const path = require("node:path");

module.exports = function resolvePlaywright() {
  const candidates = [];
  const add = (root) => {
    try {
      const pkg = require(path.join(root, "package.json"));
      const api = require(root);
      const match = String(pkg.version || "0.0.0").match(/^(\d+)\.(\d+)\.(\d+)(.*)$/);
      const order = match ? [Number(match[1]), Number(match[2]), Number(match[3]), match[4] ? 0 : 1] : [0, 0, 0, 0];
      candidates.push({ api, version: pkg.version, root, order });
    } catch { /* not a usable package */ }
  };
  for (const name of ["playwright", "playwright-core"]) {
    try { add(path.dirname(require.resolve(`${name}/package.json`))); } catch { /* next */ }
  }
  const npx = path.join(process.env.HOME || "", ".npm", "_npx");
  try {
    for (const dir of fs.readdirSync(npx)) add(path.join(npx, dir, "node_modules", "playwright-core"));
  } catch { /* no cache */ }
  candidates.sort((a, b) => {
    for (let i = 0; i < a.order.length; i++)
      if (a.order[i] !== b.order[i]) return b.order[i] - a.order[i];
    return 0;
  });
  return candidates[0] || null;
};
