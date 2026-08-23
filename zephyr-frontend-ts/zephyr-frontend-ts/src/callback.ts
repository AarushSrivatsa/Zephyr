import { exchangeCode, tokens, ApiError } from "./api.js";
import { escapeHtml, requireEl } from "./ui.js";

async function main(): Promise<void> {
  const panel = requireEl("panel");
  const statusText = requireEl("statusText");

  function showError(message: string): void {
    panel.innerHTML = `
      <div class="state-icon">⚠️</div>
      <h1>Connection failed</h1>
      <p>${escapeHtml(message)}</p>
      <a class="btn btn-accent btn-block" href="index.html" style="margin-top:14px;">
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