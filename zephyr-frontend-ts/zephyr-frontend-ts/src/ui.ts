// Zephyr — tiny shared UI helpers
export type ToastKind = "default" | "ok" | "error";

function ensureStack(): HTMLElement {
  let stack = document.querySelector<HTMLElement>(".toast-stack");
  if (!stack) {
    stack = document.createElement("div");
    stack.className = "toast-stack";
    document.body.appendChild(stack);
  }
  return stack;
}

export function toast(message: string, kind: ToastKind = "default", timeout = 4200): void {
  const stack = ensureStack();
  const el = document.createElement("div");
  el.className = "toast" + (kind === "error" ? " is-error" : kind === "ok" ? " is-ok" : "");
  el.textContent = message;
  stack.appendChild(el);
  setTimeout(() => {
    el.style.opacity = "0";
    el.style.transition = "opacity .2s ease";
    setTimeout(() => el.remove(), 220);
  }, timeout);
}

export function escapeHtml(value: unknown): string {
  if (value == null) return "";
  return String(value)
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/"/g, "&quot;")
    .replace(/'/g, "&#39;");
}

export function formatDate(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString(undefined, {
      year: "numeric",
      month: "short",
      day: "numeric",
    });
  } catch {
    return iso;
  }
}

/** Small typed wrapper around document.getElementById that throws instead of returning null. */
export function requireEl<T extends HTMLElement = HTMLElement>(id: string): T {
  const el = document.getElementById(id);
  if (!el) throw new Error(`Expected element #${id} to exist`);
  return el as T;
}
