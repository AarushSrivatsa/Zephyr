// Zephyr — account deletion page (data-deletion.html)
import * as api from "./api.js";
import { ApiError } from "./api.js";
import { requireEl, setHidden } from "./ui.js";

function errorMessage(e: unknown, fallback: string): string {
  if (e instanceof ApiError) return e.detail ?? e.message ?? fallback;
  if (e instanceof Error) return e.message || fallback;
  return fallback;
}

const STATUS_COLOR_CLASSES = ["text-ink-soft", "text-teal", "text-danger"];
function setStatusColor(el: HTMLElement, cls: (typeof STATUS_COLOR_CLASSES)[number]): void {
  el.classList.remove(...STATUS_COLOR_CLASSES);
  el.classList.add(cls);
}

const signedOutState = requireEl("signedOutState");
const signedInState = requireEl("signedInState");
const userIdDisplay = requireEl("accountUserIdDisplay");

const step1 = requireEl("confirmStep1");
const step2 = requireEl("confirmStep2");
const initDeleteBtn = requireEl<HTMLButtonElement>("initDeleteBtn");
const cancelDeleteBtn = requireEl<HTMLButtonElement>("cancelDeleteBtn");
const confirmDeleteBtn = requireEl<HTMLButtonElement>("confirmDeleteBtn");
const deleteStatus = requireEl("deleteStatus");

if (!api.tokens.isLoggedIn()) {
  setHidden(signedOutState, false);
} else {
  setHidden(signedInState, false);
  const claims = api.tokens.decodeToken(api.tokens.get()!);
  userIdDisplay.textContent = claims?.user_id ?? "unknown";
}

initDeleteBtn.addEventListener("click", () => {
  setHidden(step1, true);
  setHidden(step2, false);
});

cancelDeleteBtn.addEventListener("click", () => {
  setHidden(step2, true);
  setHidden(step1, false);
});

confirmDeleteBtn.addEventListener("click", () => {
  void (async () => {
    confirmDeleteBtn.disabled = true;
    cancelDeleteBtn.disabled = true;
    setStatusColor(deleteStatus, "text-ink-soft");
    deleteStatus.textContent = "Deleting your account…";

    try {
      await api.deleteAccount();
      api.tokens.clear();
      setHidden(step2, true);
      setStatusColor(deleteStatus, "text-teal");
      deleteStatus.textContent =
        "Done. Your Instagram account has been disconnected and signed out everywhere. " +
        "Your rules, logs, and profile info will be permanently deleted within 30 days.";
    } catch (e) {
      setStatusColor(deleteStatus, "text-danger");
      deleteStatus.textContent = errorMessage(e, "Something went wrong. Please try again.");
      confirmDeleteBtn.disabled = false;
      cancelDeleteBtn.disabled = false;
    }
  })();
});
