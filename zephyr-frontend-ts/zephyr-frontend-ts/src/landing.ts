// Zephyr — landing page (index.html)
import { loginUrl, tokens } from "./api.js";
import { setHidden } from "./ui.js";

function goConnect(): void {
  window.location.href = loginUrl();
}

for (const id of ["heroConnectBtn", "navConnectBtn", "pricingConnectBtn"]) {
  document.getElementById(id)?.addEventListener("click", goConnect);
}

if (tokens.isLoggedIn()) {
  const navConnect = document.getElementById("navConnectBtn");
  const navDash = document.getElementById("navDashboardLink");
  if (navConnect) setHidden(navConnect, true, "inline-flex");
  if (navDash) setHidden(navDash, false, "inline-flex");
}
