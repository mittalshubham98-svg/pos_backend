// Prints the error-relevant lines of an EAS build log. EAS serves logs Brotli/gzip
// compressed as newline-delimited JSON ({phase, msg, ...}).
// Usage: node mobile/scripts/build-log.js <downloaded-log-file>
const fs = require('fs');
const zlib = require('zlib');

const raw = fs.readFileSync(process.argv[2]);
let text;
for (const decode of [(b) => zlib.gunzipSync(b), (b) => zlib.brotliDecompressSync(b), (b) => b]) {
  try {
    text = decode(raw).toString('utf8');
    if (text.includes('"msg"')) break;
  } catch {
    // try the next encoding
  }
}

const lines = text.split('\n').filter(Boolean).map((l) => {
  try {
    const o = JSON.parse(l);
    return `[${o.phase || ''}] ${o.msg ?? ''}`;
  } catch {
    return l;
  }
});
const interesting = /what went wrong|error|failed|exception|could not|caused by|> task .*failed/i;
const hits = lines.map((l, i) => [l, i]).filter(([l]) => interesting.test(l));
console.log(`${lines.length} lines, ${hits.length} matches`);
for (const [, i] of hits.slice(0, 25)) console.log(lines.slice(i, i + 4).join('\n').slice(0, 600), '\n---');
