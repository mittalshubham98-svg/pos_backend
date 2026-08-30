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

/* Lightweight "Add to Home Screen" prompt, shared by both customer.html and admin.html.
   Appended straight to <body> (not into #app) so it isn't wiped out by each page's own
   render() re-render cycle — same reasoning as why the toast pattern in each HTML file is
   careful about where it lives, just outside the SPA's own DOM subtree here instead.

   appName    — shown in the banner copy, e.g. "Pilani Supply Co." or "Pilani Supply Co. — Admin"
   dismissKey — localStorage key remembering a dismissal for 7 days; distinct per app so
                dismissing the customer app's banner doesn't suppress the admin one */
function initPwaInstallPrompt({ appName, dismissKey }) {
  const isStandalone = window.matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
  if (isStandalone) return;

  const dismissedAt = Number(localStorage.getItem(dismissKey) || 0);
  const SEVEN_DAYS_MS = 7 * 24 * 60 * 60 * 1000;
  if (dismissedAt && Date.now() - dismissedAt < SEVEN_DAYS_MS) return;

  const isIos = /iPad|iPhone|iPod/.test(navigator.userAgent) && !window.MSStream;

  function dismiss(banner) {
    localStorage.setItem(dismissKey, String(Date.now()));
    banner.remove();
  }

  function showBanner(bodyHtml, onInstallClick) {
    const banner = document.createElement("div");
    banner.style.cssText = "position:fixed;left:16px;right:16px;bottom:16px;max-width:398px;margin:0 auto;background:#201e1d;color:#f3f2f2;padding:14px 16px;font-family:'Archivo',system-ui,sans-serif;box-shadow:0 12px 32px rgba(45,43,43,.35);z-index:99999;animation:drawerUp .22s ease-out;border:1px solid rgba(243,242,242,.15)";
    banner.innerHTML = `
      <div style="display:flex;justify-content:space-between;align-items:flex-start;gap:12px">
        <div style="flex:1">
          <div style="font-family:'Archivo Narrow',monospace;font-size:10px;letter-spacing:.1em;text-transform:uppercase;color:#ec3013;margin-bottom:4px">Install ${esc(appName)}</div>
          <div style="font-size:13px;line-height:1.5;color:rgba(243,242,242,.85)">${bodyHtml}</div>
        </div>
        <button data-pwa-dismiss style="background:none;border:0;color:rgba(243,242,242,.6);font-size:18px;line-height:1;cursor:pointer;padding:2px 4px">×</button>
      </div>
      ${onInstallClick ? `<button data-pwa-install style="margin-top:10px;width:100%;text-align:left;padding:9px 12px;font-weight:800;font-size:13px;background:#ec3013;color:#f3f2f2;border:0;cursor:pointer">Install now</button>` : ""}
    `;
    document.body.appendChild(banner);
    banner.querySelector("[data-pwa-dismiss]").onclick = () => dismiss(banner);
    if (onInstallClick) banner.querySelector("[data-pwa-install]").onclick = () => onInstallClick(banner);
  }

  if (isIos) {
    showBanner("Tap the Share button ⎋ and select “Add to Home Screen” ➕ for the full-screen app.");
    return;
  }

  window.addEventListener("beforeinstallprompt", (event) => {
    event.preventDefault();
    let deferredPrompt = event;
    showBanner("Add this to your home screen for one-tap access, even offline.", async (banner) => {
      if (!deferredPrompt) return;
      deferredPrompt.prompt();
      await deferredPrompt.userChoice;
      deferredPrompt = null;
      dismiss(banner);
    });
  });
}
