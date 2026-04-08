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

const katex = require('katex');
const readline = require('readline');

const rl = readline.createInterface({
    input: process.stdin,
    terminal: false,
});

const KATEX_OPTIONS_BASE = {
    throwOnError: false,
    output: 'html',
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

rl.on('line', (line) => {
    try {
        const request = JSON.parse(line);

        if (request.type === 'ping') {
            process.stdout.write(JSON.stringify({ status: 'ok' }) + '\n');
            return;
        }

        if (request.type === 'batch') {
            const results = (request.items || []).map(item =>
                renderOne(item.math, item.displayMode)
            );
            process.stdout.write(JSON.stringify({ results }) + '\n');
        } else {
            // Single render
            const result = renderOne(request.math, request.displayMode);
            process.stdout.write(JSON.stringify(result) + '\n');
        }
    } catch (e) {
        process.stdout.write(JSON.stringify({ html: null, error: 'Invalid request: ' + e.message }) + '\n');
    }
});

// Graceful shutdown
process.on('SIGTERM', () => process.exit(0));
process.on('SIGINT', () => process.exit(0));

// Signal ready
process.stderr.write('katex-worker ready\n');
