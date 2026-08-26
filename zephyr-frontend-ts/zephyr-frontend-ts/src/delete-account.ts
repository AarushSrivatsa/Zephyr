// Zephyr — account deletion page (data-deletion.html)
import * as api from "./api.js";
import { ApiError } from "./api.js";
import { requireEl } from "./ui.js";

function errorMessage(e: unknown, fallback: string): string {
  if (e instanceof ApiError) return e.detail ?? e.message ?? fallback;
  if (e instanceof Error) return e.message || fallback;
  return fallback;
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
  signedOutState.style.display = "block";
} else {
  signedInState.style.display = "block";
  const claims = api.tokens.decodeToken(api.tokens.get()!);
  userIdDisplay.textContent = claims?.user_id ?? "unknown";
}

initDeleteBtn.addEventListener("click", () => {
  step1.style.display = "none";
  step2.style.display = "block";
});

cancelDeleteBtn.addEventListener("click", () => {
  step2.style.display = "none";
  step1.style.display = "block";
});

confirmDeleteBtn.addEventListener("click", () => {
  void (async () => {
    confirmDeleteBtn.disabled = true;
    cancelDeleteBtn.disabled = true;
    deleteStatus.textContent = "Deleting your account…";
    deleteStatus.style.color = "var(--ink-soft)";

    try {
      await api.deleteAccount();
      api.tokens.clear();
      step2.style.display = "none";
      deleteStatus.style.color = "var(--teal)";
      deleteStatus.textContent =
        "Done. Your Instagram account has been disconnected and signed out everywhere. " +
        "Your rules, logs, and profile info will be permanently deleted within 30 days.";
    } catch (e) {
      deleteStatus.style.color = "var(--danger)";
      deleteStatus.textContent = errorMessage(e, "Something went wrong. Please try again.");
      confirmDeleteBtn.disabled = false;
      cancelDeleteBtn.disabled = false;
    }
  })();
});
