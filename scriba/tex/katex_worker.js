#!/usr/bin/env node
/**
 * KaTeX Worker - Persistent rendering process
 *
 * Giao tiếp qua stdin/stdout với JSON-line protocol.
 * Mỗi dòng input = 1 JSON request, mỗi dòng output = 1 JSON response.
 *
 * Protocol:
 *   Request:  {"type": "batch", "items": [{"math": "x^2", "displayMode": false}, ...]}
 *   Response: {"results": [{"html": "...", "error": null}, ...]}
 *
 *   Request:  {"type": "single", "math": "x^2", "displayMode": false}
 *   Response: {"html": "...", "error": null}
 *
 *   Request:  {"type": "ping"}
 *   Response: {"status": "ok"}
 */

const path = require("path");
const fs = require("fs");
const readline = require("readline");

// Prefer the vendored KaTeX shipped inside the wheel. Fall back to a
// globally installed `katex` npm module if the vendored file is somehow
// missing (e.g. running from a partial source checkout).
const VENDORED_KATEX = path.join(__dirname, "vendor", "katex", "katex.min.js");
let katex;
if (fs.existsSync(VENDORED_KATEX)) {
  katex = require(VENDORED_KATEX);
  process.stderr.write("katex-worker using vendored katex\n");
} else {
  katex = require("katex");
  process.stderr.write("katex-worker using global katex (vendored copy not found)\n");
}

const rl = readline.createInterface({
  input: process.stdin,
  terminal: false,
});

const KATEX_OPTIONS_BASE = {
  throwOnError: false,
  output: "html",
  strict: false,
};

function renderOne(math, displayMode) {
  try {
    const html = katex.renderToString(math, {
      ...KATEX_OPTIONS_BASE,
      displayMode: displayMode || false,
    });
    return { html, error: null };
  } catch (e) {
    return { html: null, error: e.message };
  }
}

rl.on("line", (line) => {
  try {
    const request = JSON.parse(line);

    if (request.type === "ping") {
      process.stdout.write(JSON.stringify({ status: "ok" }) + "\n");
      return;
    }

    if (request.type === "batch") {
      const results = (request.items || []).map((item) => renderOne(item.math, item.displayMode));
      process.stdout.write(JSON.stringify({ results }) + "\n");
    } else {
      // Single render
      const result = renderOne(request.math, request.displayMode);
      process.stdout.write(JSON.stringify(result) + "\n");
    }
  } catch (e) {
    process.stdout.write(
      JSON.stringify({ html: null, error: "Invalid request: " + e.message }) + "\n",
    );
  }
});

// Graceful shutdown
process.on("SIGTERM", () => process.exit(0));
process.on("SIGINT", () => process.exit(0));

// Signal ready
process.stderr.write("katex-worker ready\n");
