// Zephyr — tiny shared UI helpers
export type ToastKind = "default" | "ok" | "error";

const TOAST_BASE =
  "pointer-events-auto max-w-[320px] rounded-sm border px-4 py-3 font-body text-sm shadow-pop animate-toast-in";
const TOAST_KIND: Record<ToastKind, string> = {
  default: "border-line-strong bg-surface text-ink",
  ok: "border-teal bg-surface text-teal",
  error: "border-danger bg-surface text-danger",
};

function ensureStack(): HTMLElement {
  let stack = document.querySelector<HTMLElement>("[data-toast-stack]");
  if (!stack) {
    stack = document.createElement("div");
    stack.dataset.toastStack = "";
    stack.className =
      "pointer-events-none fixed bottom-6 right-6 z-[200] flex flex-col items-end gap-2.5";
    document.body.appendChild(stack);
  }
  return stack;
}

export function toast(message: string, kind: ToastKind = "default", timeout = 4200): void {
  const stack = ensureStack();
  const el = document.createElement("div");
  el.className = `${TOAST_BASE} ${TOAST_KIND[kind]}`;
  el.textContent = message;
  stack.appendChild(el);
  setTimeout(() => {
    el.classList.add("transition-opacity", "duration-200", "opacity-0");
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

/**
 * Show/hide via Tailwind's `hidden` utility instead of inline style.display
 * flips. Explicitly toggles both classes (rather than just `hidden`) so the
 * result never depends on the generated stylesheet's utility ordering.
 */
export function setHidden(el: HTMLElement, hidden: boolean, showDisplay: "block" | "flex" | "grid" | "inline-flex" = "block"): void {
  el.classList.toggle("hidden", hidden);
  el.classList.toggle(showDisplay, !hidden);
}
