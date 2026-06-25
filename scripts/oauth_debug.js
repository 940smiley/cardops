#!/usr/bin/env node
"use strict";

const childProcess = require("node:child_process");
const fs = require("node:fs");
const https = require("node:https");
const path = require("node:path");
const { URL } = require("node:url");

const ROOT = path.resolve(__dirname, "..");
const DEFAULT_OWNER = "940smiley";
const DEFAULT_REPO = "cardops";
const GOOGLE_PATTERNS = [
  ["cloud", "functions.net"].join(""),
  ["CARDOPS_", "GCP_PROJECT"].join(""),
  ["CARDOPS_", "GCP_REGION"].join(""),
  ["EBAY_", "CALLBACK_FUNCTION"].join(""),
  ["ebay", "AuthCallback"].join(""),
  ["Google ", "Cloud Function"].join("")
];

function findEnvPath() {
  const exact = path.join(ROOT, ".env");
  if (fs.existsSync(exact)) return exact;
  const found = fs.readdirSync(ROOT).find((name) => name.toLowerCase() === ".env");
  return found ? path.join(ROOT, found) : exact;
}

const ENV_PATH = findEnvPath();

function parseEnvFile(filePath) {
  const values = {};
  if (!fs.existsSync(filePath)) {
    return values;
  }
  for (const rawLine of fs.readFileSync(filePath, "utf8").split(/\r?\n/)) {
    const line = rawLine.trim();
    if (!line || line.startsWith("#") || !line.includes("=")) continue;
    const index = line.indexOf("=");
    const key = line.slice(0, index).trim();
    const value = line.slice(index + 1).trim().replace(/^"|"$/g, "");
    values[key] = value;
  }
  return values;
}

function envValue(env, key, fallback = "") {
  return process.env[key] || env[key] || fallback;
}

function run(command, args) {
  try {
    let file = command;
    let commandArgs = args;
    if (process.platform === "win32" && /\.(cmd|bat)$/i.test(command)) {
      const psQuote = (value) => `'${String(value).replace(/'/g, "''")}'`;
      file = "powershell.exe";
      commandArgs = [
        "-NoProfile",
        "-ExecutionPolicy",
        "Bypass",
        "-Command",
        `& ${psQuote(command)} ${args.map(psQuote).join(" ")}`
      ];
    }
    const result = childProcess.spawnSync(file, commandArgs, {
      cwd: ROOT,
      encoding: "utf8",
      shell: false
    });
    if (result.error) {
      return { ok: false, stdout: "", stderr: result.error.message, status: 1 };
    }
    return {
      ok: result.status === 0,
      stdout: (result.stdout || "").trim(),
      stderr: (result.stderr || "").trim(),
      status: result.status
    };
  } catch (error) {
    return { ok: false, stdout: "", stderr: error.message, status: 1 };
  }
}

function commonCommandPaths(command) {
  if (process.platform !== "win32") return [command];
  if (command === "gh") {
    return [
      "gh",
      "C:\\Program Files\\GitHub CLI\\gh.exe",
      path.join(process.env.LOCALAPPDATA || "", "Microsoft\\WinGet\\Links\\gh.exe")
    ];
  }
  return [command];
}

function resolveCommand(command) {
  if (process.platform === "win32") {
    const whereProbe = run("where.exe", [command]);
    if (whereProbe.ok) {
      const first = whereProbe.stdout.split(/\r?\n/).find(Boolean);
      if (first) return first;
    }
  } else {
    const whichProbe = run("which", [command]);
    if (whichProbe.ok) return whichProbe.stdout.split(/\r?\n/)[0];
  }
  return commonCommandPaths(command).find((candidate) => candidate !== command && fs.existsSync(candidate)) || "";
}

function parseGitHubRemote(remote) {
  if (!remote) return null;
  const normalized = remote.trim().replace(/\.git$/i, "");
  const patterns = [
    /^https:\/\/github\.com\/([^/]+)\/([^/]+)$/i,
    /^git@github\.com:([^/]+)\/([^/]+)$/i,
    /^ssh:\/\/git@github\.com\/([^/]+)\/([^/]+)$/i
  ];
  for (const pattern of patterns) {
    const match = normalized.match(pattern);
    if (match) {
      return { owner: match[1], repo: match[2] };
    }
  }
  return null;
}

function getRepoSlug() {
  const remote = run("git", ["config", "--get", "remote.origin.url"]);
  const parsed = parseGitHubRemote(remote.ok ? remote.stdout : "");
  return parsed || { owner: DEFAULT_OWNER, repo: DEFAULT_REPO };
}

function buildRedirectUrl({ owner, repo }) {
  return `https://${owner}.github.io/${repo}/ebay/callback/`;
}

function checkHttp200(url, redirectsRemaining = 3) {
  return new Promise((resolve) => {
    let parsed;
    try {
      parsed = new URL(url);
    } catch (error) {
      resolve({ ok: false, detail: `Invalid URL: ${error.message}` });
      return;
    }

    const req = https.request(
      {
        method: "GET",
        hostname: parsed.hostname,
        path: `${parsed.pathname}${parsed.search || ""}`,
        timeout: 10000,
        headers: {
          "User-Agent": "cardops-oauth-debug"
        }
      },
      (res) => {
        res.resume();
        const location = res.headers.location;
        if (
          location &&
          [301, 302, 303, 307, 308].includes(res.statusCode) &&
          redirectsRemaining > 0
        ) {
          const nextUrl = new URL(location, parsed).toString();
          checkHttp200(nextUrl, redirectsRemaining - 1).then(resolve);
          return;
        }
        resolve({
          ok: res.statusCode === 200,
          detail: `HTTP ${res.statusCode}`
        });
      }
    );
    req.on("timeout", () => {
      req.destroy();
      resolve({ ok: false, detail: "Timed out after 10 seconds" });
    });
    req.on("error", (error) => resolve({ ok: false, detail: error.message }));
    req.end();
  });
}

function checkPagesConfigured(owner, repo) {
  const gh = resolveCommand("gh");
  if (!gh) {
    return { status: "WARN", detail: "GitHub CLI is not installed or not on PATH" };
  }
  const auth = run(gh, ["auth", "status"]);
  if (!auth.ok) {
    return { status: "WARN", detail: "GitHub CLI is installed but not authenticated" };
  }
  const result = run(gh, ["api", `repos/${owner}/${repo}/pages`]);
  if (result.ok) {
    const pages = JSON.parse(result.stdout);
    const branch = pages.source && pages.source.branch;
    const sourcePath = pages.source && pages.source.path;
    if (pages.build_type === "legacy" && branch === "gh-pages" && sourcePath === "/") {
      return { status: "PASS", detail: pages.html_url || "GitHub Pages is configured" };
    }
    return {
      status: "FAIL",
      detail: `GitHub Pages is build_type=${pages.build_type || "[unknown]"} source=${branch || "[unknown]"}${sourcePath || ""}, expected legacy gh-pages/`
    };
  }
  return {
    status: "FAIL",
    detail: result.stderr || result.stdout || "GitHub Pages is not configured"
  };
}

function checkRemoteFile(owner, repo, branch, remotePath) {
  const gh = resolveCommand("gh");
  if (!gh) {
    return { status: "WARN", detail: "GitHub CLI is unavailable" };
  }
  const result = run(gh, [
    "api",
    `repos/${owner}/${repo}/contents/${remotePath}?ref=${encodeURIComponent(branch)}`,
    "--jq",
    ".sha"
  ]);
  if (result.ok && result.stdout) {
    return { status: "PASS", detail: `${remotePath} is on ${branch}` };
  }
  return {
    status: "FAIL",
    detail: `${remotePath} is not on ${branch} yet`
  };
}

function fileExists(relativePath) {
  const filePath = path.join(ROOT, ...relativePath.split("/"));
  return fs.existsSync(filePath);
}

function checkCallbackRelay() {
  const filePath = path.join(ROOT, "public", "ebay", "callback", "index.html");
  if (!fs.existsSync(filePath)) {
    return { ok: false, detail: "callback file is missing" };
  }
  const content = fs.readFileSync(filePath, "utf8");
  const hasLocalCallback = content.includes("http://127.0.0.1:8000/ebay/callback");
  const hasBrowserMode = content.includes("browser") && content.includes("window.location.replace");
  const avoidsBlockedFetch = !content.includes("fetch(localUrl");
  return {
    ok: hasLocalCallback && hasBrowserMode && avoidsBlockedFetch,
    detail: `localCallback=${hasLocalCallback}, browserMode=${hasBrowserMode}, noLoopbackFetch=${avoidsBlockedFetch}`
  };
}

function checkOauthBuilder(expectedRedirect) {
  const builderPath = path.join(ROOT, "apps", "api", "cardops_api", "ebay_oauth.py");
  if (!fs.existsSync(builderPath)) {
    return { ok: false, detail: "apps/api/cardops_api/ebay_oauth.py is missing" };
  }
  const content = fs.readFileSync(builderPath, "utf8");
  const hasRedirect = content.includes("EBAY_REDIRECT_URI") || content.includes("ebay_redirect_uri");
  const hasRuname = content.includes("EBAY_RUNAME") || content.includes("runame");
  const hasExpectedDefault =
    content.includes(expectedRedirect) || content.includes("github_pages_callback_url");
  return {
    ok: hasRedirect && hasRuname && hasExpectedDefault,
    detail: `redirect=${hasRedirect}, runame=${hasRuname}, githubPagesDefault=${hasExpectedDefault}`
  };
}

function scanForGoogleCloudReferences() {
  const allowedExtensions = new Set([
    ".bat",
    ".example",
    ".html",
    ".js",
    ".json",
    ".md",
    ".ps1",
    ".py",
    ".toml",
    ".ts",
    ".tsx",
    ".yml",
    ".yaml"
  ]);
  const ignoredParts = new Set([
    ".git",
    ".pytest_cache",
    ".ruff_cache",
    ".venv",
    "data",
    "node_modules",
    "__pycache__"
  ]);
  const matches = [];

  function walk(directory) {
    for (const entry of fs.readdirSync(directory, { withFileTypes: true })) {
      if (ignoredParts.has(entry.name)) continue;
      const fullPath = path.join(directory, entry.name);
      if (entry.isDirectory()) {
        walk(fullPath);
        continue;
      }
      const extension = path.extname(entry.name);
      if (!allowedExtensions.has(extension) && entry.name !== ".env" && entry.name !== ".ENV") {
        continue;
      }
      const relativePath = path.relative(ROOT, fullPath).replace(/\\/g, "/");
      if (relativePath === "scripts/oauth_debug.js" || relativePath === "scripts/fix.ps1") {
        continue;
      }
      const content = fs.readFileSync(fullPath, "utf8");
      for (const pattern of GOOGLE_PATTERNS) {
        if (content.includes(pattern)) {
          matches.push(relativePath);
          break;
        }
      }
    }
  }

  walk(ROOT);
  return Array.from(new Set(matches));
}

function formatRow(status, check, detail, fix) {
  return { status, check, detail, fix };
}

function printTable(rows) {
  const headers = ["STATUS", "CHECK", "DETAIL", "SUGGESTED FIX"];
  const allRows = rows.map((row) => [row.status, row.check, row.detail, row.fix]);
  const widths = headers.map((header, index) =>
    Math.max(header.length, ...allRows.map((row) => String(row[index]).length))
  );
  const print = (row) =>
    console.log(row.map((cell, index) => String(cell).padEnd(widths[index])).join(" | "));
  print(headers);
  console.log(widths.map((width) => "-".repeat(width)).join("-+-"));
  for (const row of allRows) print(row);
}

async function main() {
  const fileEnv = parseEnvFile(ENV_PATH);
  const repoSlug = getRepoSlug();
  const owner = envValue(fileEnv, "CARDOPS_GITHUB_OWNER", repoSlug.owner);
  const repo = envValue(fileEnv, "CARDOPS_GITHUB_REPO", repoSlug.repo);
  const expectedRedirect = buildRedirectUrl({ owner, repo });
  const actualRedirect = envValue(fileEnv, "EBAY_REDIRECT_URI", "");
  const accepted = envValue(fileEnv, "EBAY_AUTH_ACCEPTED_URL", "");
  const declined = envValue(fileEnv, "EBAY_AUTH_DECLINED_URL", "");
  const runame = envValue(fileEnv, "EBAY_RUNAME", "");

  const rows = [];
  rows.push(
    fs.existsSync(ENV_PATH)
      ? formatRow("PASS", ".env file", path.basename(ENV_PATH), "None")
      : formatRow("FAIL", ".env file", "[missing]", "Run scripts/fix.ps1")
  );

  rows.push(
    actualRedirect === expectedRedirect
      ? formatRow("PASS", ".env EBAY_REDIRECT_URI", actualRedirect, "None")
      : formatRow(
          "FAIL",
          ".env EBAY_REDIRECT_URI",
          actualRedirect || "[missing]",
          `Run scripts/fix.ps1 to set ${expectedRedirect}`
        )
  );

  rows.push(
    accepted === expectedRedirect && declined === expectedRedirect
      ? formatRow("PASS", "Developer Portal target URLs", expectedRedirect, "Paste this exact URL into eBay if not already done")
      : formatRow(
          "FAIL",
          "Developer Portal target URLs",
          `accepted=${accepted || "[missing]"}, declined=${declined || "[missing]"}`,
          `Use ${expectedRedirect} for Auth Accepted URL and Auth Declined URL`
        )
  );

  rows.push(
    runame
      ? formatRow("PASS", "EBAY_RUNAME", "[configured]", "None")
      : formatRow(
          "WARN",
          "EBAY_RUNAME",
          "[missing]",
          "After eBay creates the RuName, set EBAY_RUNAME; the callback URL stays unchanged"
        )
  );

  rows.push(
    fileExists("public/ebay/callback/index.html")
      ? formatRow("PASS", "Static callback file", "public/ebay/callback/index.html", "None")
      : formatRow("FAIL", "Static callback file", "[missing]", "Restore public/ebay/callback/index.html")
  );

  const relayCheck = checkCallbackRelay();
  rows.push(
    relayCheck.ok
      ? formatRow("PASS", "Static callback relay", relayCheck.detail, "None")
      : formatRow(
          "FAIL",
          "Static callback relay",
          relayCheck.detail,
          "Update public/ebay/callback/index.html and publish gh-pages"
        )
  );

  const builderCheck = checkOauthBuilder(expectedRedirect);
  rows.push(
    builderCheck.ok
      ? formatRow("PASS", "OAuth URL builder", builderCheck.detail, "None")
      : formatRow("FAIL", "OAuth URL builder", builderCheck.detail, "Restore apps/api/cardops_api/ebay_oauth.py")
  );

  const googleMatches = scanForGoogleCloudReferences();
  rows.push(
    googleMatches.length === 0
      ? formatRow("PASS", "Google Cloud references", "None found in source/config text files", "None")
      : formatRow(
          "FAIL",
          "Google Cloud references",
          googleMatches.join(", "),
          "Run scripts/fix.ps1 and remove billing-only callback leftovers"
        )
  );

  const pagesCheck = checkPagesConfigured(owner, repo);
  rows.push(
    pagesCheck.status === "PASS"
      ? formatRow("PASS", "GitHub Pages configured", pagesCheck.detail, "None")
      : formatRow(
          pagesCheck.status,
          "GitHub Pages configured",
          pagesCheck.detail,
          "Run scripts/fix.ps1 -PublishPages"
        )
  );

  const remoteCallback = checkRemoteFile(owner, repo, "gh-pages", "ebay/callback/index.html");
  rows.push(
    remoteCallback.status === "PASS"
      ? formatRow("PASS", "Callback file on gh-pages", remoteCallback.detail, "None")
      : formatRow(
          remoteCallback.status,
          "Callback file on gh-pages",
          remoteCallback.detail,
          "Run scripts/fix.ps1 -PublishPages to publish only the static callback files"
        )
  );

  const httpCheck = await checkHttp200(expectedRedirect);
  rows.push(
    httpCheck.ok
      ? formatRow("PASS", "Callback HTTP 200", httpCheck.detail, "None")
      : formatRow(
          "FAIL",
          "Callback HTTP 200",
          httpCheck.detail,
          "Run scripts/fix.ps1 -PublishPages, then wait for GitHub Pages to update"
        )
  );

  console.log("\nCardOps AI eBay OAuth Debug");
  console.log(`Expected redirect URL: ${expectedRedirect}`);
  console.log(`Expected .env line: EBAY_REDIRECT_URI=${expectedRedirect}`);
  console.log("eBay Developer Portal must use this exact URL for Auth Accepted URL and Auth Declined URL.\n");
  printTable(rows);

  const failed = rows.some((row) => row.status === "FAIL");
  process.exit(failed ? 1 : 0);
}

main().catch((error) => {
  console.error(error);
  process.exit(1);
});
