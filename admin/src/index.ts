import { DASHBOARD_HTML } from "./ui";

type FollowConfig = {
  youtube: Array<{ name: string; channel_id: string }>;
  bilibili: Array<{ name: string; uid: string | number }>;
  rss: Array<{ name: string; url: string }>;
  github: Array<{ name: string; repo: string }>;
  github_trending: { enabled: boolean; language: string; limit: number };
};

const json = (data: unknown, status = 200) => Response.json(data, {
  status,
  headers: { "Cache-Control": "no-store", "X-Content-Type-Options": "nosniff" },
});

async function secureEqual(a: string, b: string): Promise<boolean> {
  const encoder = new TextEncoder();
  const [aHash, bHash] = await Promise.all([
    crypto.subtle.digest("SHA-256", encoder.encode(a)),
    crypto.subtle.digest("SHA-256", encoder.encode(b)),
  ]);
  const left = new Uint8Array(aHash);
  const right = new Uint8Array(bHash);
  let difference = left.length ^ right.length;
  for (let index = 0; index < Math.max(left.length, right.length); index += 1) {
    difference |= (left[index % left.length] ?? 0) ^ (right[index % right.length] ?? 0);
  }
  return difference === 0;
}

async function authorized(request: Request, env: Env): Promise<boolean> {
  const auth = request.headers.get("Authorization") ?? "";
  if (!auth.startsWith("Basic ")) return false;
  let decoded = "";
  try { decoded = atob(auth.slice(6)); } catch { return false; }
  const separator = decoded.indexOf(":");
  if (separator < 0) return false;
  return secureEqual(decoded.slice(separator + 1), env.ADMIN_PASSWORD);
}

async function exportAuthorized(request: Request, env: Env): Promise<boolean> {
  const token = request.headers.get("Authorization")?.replace(/^Bearer\s+/i, "") ?? "";
  return secureEqual(token, env.CONFIG_READ_TOKEN);
}

function validateConfig(value: unknown): value is FollowConfig {
  if (!value || typeof value !== "object") return false;
  const cfg = value as Record<string, unknown>;
  if (!["youtube", "bilibili", "rss", "github"].every((key) => Array.isArray(cfg[key]))) return false;
  const trending = cfg.github_trending;
  return !!trending && typeof trending === "object" &&
    typeof (trending as Record<string, unknown>).enabled === "boolean" &&
    Number.isInteger((trending as Record<string, unknown>).limit) &&
    Number((trending as Record<string, unknown>).limit) >= 1 &&
    Number((trending as Record<string, unknown>).limit) <= 50;
}

async function loadConfig(env: Env): Promise<FollowConfig> {
  const row = await env.DB.prepare("SELECT value FROM settings WHERE key = ?")
    .bind("follow_config").first<{ value: string }>();
  if (!row) throw new Error("follow_config is not initialized");
  return JSON.parse(row.value) as FollowConfig;
}

async function github(path: string, env: Env, init?: RequestInit): Promise<Response> {
  return fetch(`https://api.github.com/repos/${env.GITHUB_OWNER}/${env.GITHUB_REPO}${path}`, {
    ...init,
    headers: {
      "Accept": "application/vnd.github+json",
      "Authorization": `Bearer ${env.GITHUB_TOKEN}`,
      "User-Agent": "CunRadar-Admin/1.0",
      "X-GitHub-Api-Version": "2022-11-28",
      ...(init?.headers ?? {}),
    },
  });
}

async function route(request: Request, env: Env): Promise<Response> {
  const url = new URL(request.url);

  if (url.pathname === "/api/export" && request.method === "GET") {
    if (!(await exportAuthorized(request, env))) return json({ error: "Unauthorized" }, 401);
    return json(await loadConfig(env));
  }

  if (!(await authorized(request, env))) {
    return new Response("Authentication required", {
      status: 401,
      headers: { "WWW-Authenticate": 'Basic realm="CunRadar Admin", charset="UTF-8"' },
    });
  }

  if (url.pathname === "/" && request.method === "GET") {
    return new Response(DASHBOARD_HTML, {
      headers: { "Content-Type": "text/html; charset=utf-8", "Cache-Control": "no-store" },
    });
  }
  if (url.pathname === "/api/config" && request.method === "GET") return json(await loadConfig(env));
  if (url.pathname === "/api/config" && request.method === "PUT") {
    const body: unknown = await request.json();
    if (!validateConfig(body)) return json({ error: "Invalid follow configuration" }, 400);
    await env.DB.prepare("INSERT INTO settings(key,value,updated_at) VALUES(?,?,CURRENT_TIMESTAMP) ON CONFLICT(key) DO UPDATE SET value=excluded.value,updated_at=CURRENT_TIMESTAMP")
      .bind("follow_config", JSON.stringify(body)).run();
    return json({ ok: true });
  }
  if (url.pathname === "/api/run" && request.method === "POST") {
    const response = await github("/actions/workflows/daily.yml/dispatches", env, {
      method: "POST", body: JSON.stringify({ ref: "main" }),
      headers: { "Content-Type": "application/json" },
    });
    if (!response.ok) return json({ error: "GitHub rejected the run request", status: response.status }, 502);
    return json({ ok: true, message: "Workflow queued" }, 202);
  }
  if (url.pathname === "/api/runs" && request.method === "GET") {
    const response = await github("/actions/workflows/daily.yml/runs?per_page=5", env);
    if (!response.ok) return json({ error: "Unable to load GitHub runs", status: response.status }, 502);
    const payload = await response.json<{ workflow_runs: Array<Record<string, unknown>> }>();
    return json(payload.workflow_runs.map((run) => ({
      id: run.id, status: run.status, conclusion: run.conclusion,
      created_at: run.created_at, html_url: run.html_url,
    })));
  }
  if (url.pathname === "/api/meta" && request.method === "GET") {
    return json({ report_url: env.REPORT_URL, repo: `${env.GITHUB_OWNER}/${env.GITHUB_REPO}` });
  }
  return json({ error: "Not found" }, 404);
}

export default {
  async fetch(request, env): Promise<Response> {
    try { return await route(request, env); }
    catch (error) {
      console.error(JSON.stringify({ message: "request failed", error: error instanceof Error ? error.message : String(error), path: new URL(request.url).pathname }));
      return json({ error: "Internal server error" }, 500);
    }
  },
} satisfies ExportedHandler<Env>;
