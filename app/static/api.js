/* Shared helpers for the Pilani Supply Co. frontend — customer.html and admin.html.
   Talks to the FastAPI backend at the same origin this file is served from. */

const GST_ALLOWED = [0, 3, 5, 18, 28, 40];

function inr(n) {
  return "₹" + (Math.round((Number(n) || 0) * 100) / 100).toLocaleString("en-IN", { minimumFractionDigits: 2, maximumFractionDigits: 2 });
}
function inr0(n) {
  return "₹" + Math.round(Number(n) || 0).toLocaleString("en-IN");
}
function slugOf(name) {
  return (name || "").toLowerCase().replace(/[^a-z0-9 ]/g, "").split(" ").slice(0, 3).join(" ");
}
function esc(s) {
  return String(s == null ? "" : s).replace(/[&<>"']/g, c => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]));
}
function decodeJwt(token) {
  try {
    const body = token.split(".")[1];
    const json = decodeURIComponent(atob(body.replace(/-/g, "+").replace(/_/g, "/")).split("").map(c => "%" + c.charCodeAt(0).toString(16).padStart(2, "0")).join(""));
    return JSON.parse(json);
  } catch (err) {
    return null;
  }
}

class ApiError extends Error {
  constructor(status, detail) {
    super(typeof detail === "string" ? detail : JSON.stringify(detail));
    this.status = status;
    this.detail = detail;
  }
}

/* Thin fetch wrapper: JSON in, JSON out, throws ApiError on non-2xx so callers can show the
   backend's own message instead of a generic failure — matches the "never a silent 500" spirit
   of the API by always surfacing what the server actually said. */
async function api(path, { method = "GET", token = null, json = undefined, form = undefined } = {}) {
  const headers = {};
  if (token) headers["Authorization"] = "Bearer " + token;
  let body;
  if (json !== undefined) {
    headers["Content-Type"] = "application/json";
    body = JSON.stringify(json);
  } else if (form !== undefined) {
    body = form; // FormData — let the browser set the multipart boundary
  }
  const res = await fetch(path, { method, headers, body });
  const text = await res.text();
  let data = null;
  if (text) {
    try { data = JSON.parse(text); } catch (err) { data = text; }
  }
  if (!res.ok) {
    const detail = data && typeof data === "object" && "detail" in data ? data.detail : data;
    throw new ApiError(res.status, detail || (res.status + " " + res.statusText));
  }
  return data;
}

/* GET a binary resource (PDF/CSV) that requires an Authorization header — a plain <a href>
   can't attach that header, so fetch as a blob and hand the browser an object URL instead. */
async function apiDownload(path, token, filename) {
  const res = await fetch(path, { headers: token ? { Authorization: "Bearer " + token } : {} });
  if (!res.ok) {
    let detail = res.status + " " + res.statusText;
    try { const j = await res.json(); if (j && j.detail) detail = j.detail; } catch (err) { /* not JSON */ }
    throw new ApiError(res.status, detail);
  }
  const blob = await res.blob();
  const url = URL.createObjectURL(blob);
  const contentType = res.headers.get("Content-Type") || "";
  if (contentType.includes("pdf")) {
    window.open(url, "_blank");
  } else {
    const a = document.createElement("a");
    a.href = url;
    a.download = filename || "download";
    document.body.appendChild(a);
    a.click();
    a.remove();
  }
  setTimeout(() => URL.revokeObjectURL(url), 30000);
}

function errorMessage(err) {
  if (err instanceof ApiError) {
    if (Array.isArray(err.detail)) {
      return err.detail.map(d => (d && d.msg) || JSON.stringify(d)).join("; ");
    }
    return String(err.detail);
  }
  return err && err.message ? err.message : String(err);
}
