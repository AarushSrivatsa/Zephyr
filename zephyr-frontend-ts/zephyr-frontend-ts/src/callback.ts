import { exchangeCode, tokens, ApiError } from "./api.js";
import { escapeHtml, requireEl } from "./ui.js";

async function main(): Promise<void> {
  const panel = requireEl("panel");
  const statusText = requireEl("statusText");

  function showError(message: string): void {
    panel.innerHTML = `
      <div class="mb-3.5 text-3xl">⚠️</div>
      <h1 class="mb-2 font-display text-xl font-semibold text-ink">Connection failed</h1>
      <p class="text-ink-soft">${escapeHtml(message)}</p>
      <a
        class="mt-3.5 inline-flex w-full items-center justify-center gap-2 rounded-md bg-accent px-5 py-3 font-display text-[15px] font-semibold text-[#150014] shadow-glow-accent transition hover:-translate-y-px hover:bg-accent-deep hover:shadow-glow-accent-lg"
        href="index.html"
      >
        Back to Zephyr
      </a>
    `;
  }

  const params = new URLSearchParams(window.location.search);

  const code = params.get("code");
  const errorParam =
    params.get("error_description") ??
    params.get("error");

  if (errorParam) {
    showError(errorParam);
    return;
  }

  if (!code) {
    showError(
      "No authorization code was returned by Instagram. Please try connecting again."
    );
    return;
  }

  try {
    const data = await exchangeCode(code);

    tokens.set(data);

    statusText.textContent =
      "Connected. Taking you to your dashboard…";

    window.location.replace("dashboard.html");

  } catch (e) {
    const message =
      e instanceof ApiError
        ? e.detail ?? e.message
        : "Something went wrong while connecting your account.";

    showError(message);
  }
}

void main();
