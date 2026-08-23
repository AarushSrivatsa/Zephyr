// Zephyr — landing page (index.html)
import { loginUrl, tokens } from "./api.js";

function goConnect(): void {
  window.location.href = loginUrl();
}

for (const id of ["heroConnectBtn", "navConnectBtn", "pricingConnectBtn"]) {
  document.getElementById(id)?.addEventListener("click", goConnect);
}

if (tokens.isLoggedIn()) {
  const navConnect = document.getElementById("navConnectBtn");
  const navDash = document.getElementById("navDashboardLink");
  if (navConnect) navConnect.textContent = "Reconnect Instagram";
  if (navDash) navDash.style.display = "inline-flex";
}
