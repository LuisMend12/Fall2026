// Proof Patterns: local study app for MATH 3150 Exam 1.
// Run `npm install` once, then `npm start` and open http://localhost:3150
const http = require("node:http");
const fs = require("node:fs");
const path = require("node:path");

const PORT = Number(process.env.PORT) || 3150;
const PUBLIC = path.join(__dirname, "public");
const MATHJAX = path.join(__dirname, "node_modules", "mathjax", "es5");
const PROGRESS = path.join(__dirname, "progress.json");

const TYPES = {
  ".html": "text/html; charset=utf-8",
  ".js": "text/javascript; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".json": "application/json; charset=utf-8",
  ".woff": "font/woff",
  ".woff2": "font/woff2",
};

function sendFile(res, root, rel) {
  const file = path.join(root, rel);
  if (!file.startsWith(root + path.sep)) return send(res, 403, "Forbidden");
  fs.readFile(file, (err, buf) => {
    if (err) return send(res, 404, "Not found");
    res.writeHead(200, { "Content-Type": TYPES[path.extname(file)] || "application/octet-stream" });
    res.end(buf);
  });
}

function send(res, code, body, type = "text/plain; charset=utf-8") {
  res.writeHead(code, { "Content-Type": type });
  res.end(body);
}

function readProgress() {
  try {
    return JSON.parse(fs.readFileSync(PROGRESS, "utf8"));
  } catch {
    return {};
  }
}

const server = http.createServer((req, res) => {
  const url = new URL(req.url, `http://${req.headers.host}`);
  const p = decodeURIComponent(url.pathname);

  if (p === "/api/progress") {
    if (req.method === "GET") return send(res, 200, JSON.stringify(readProgress()), TYPES[".json"]);
    if (req.method === "PUT") {
      let body = "";
      req.on("data", (c) => {
        body += c;
        if (body.length > 1e6) req.destroy();
      });
      req.on("end", () => {
        try {
          const data = JSON.parse(body);
          fs.writeFileSync(PROGRESS, JSON.stringify(data, null, 2));
          send(res, 204, "");
        } catch {
          send(res, 400, "Progress must be JSON");
        }
      });
      return;
    }
    return send(res, 405, "Method not allowed");
  }

  if (p.startsWith("/vendor/mathjax/")) return sendFile(res, MATHJAX, p.slice("/vendor/mathjax/".length));
  sendFile(res, PUBLIC, p === "/" ? "index.html" : p.slice(1));
});

server.listen(PORT, "127.0.0.1", () => {
  console.log(`Proof Patterns running at http://localhost:${PORT}`);
  if (!fs.existsSync(MATHJAX)) console.warn("MathJax missing: run `npm install` so the math renders.");
});
