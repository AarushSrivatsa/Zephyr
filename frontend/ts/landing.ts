// Zephyr — landing page (index.html)
//
// Signed-in visitors are bounced to /dashboard by an inline script in
// index.html's <head>, before this module even loads — so everything below
// only ever runs for a signed-out visitor.
import { loginUrl } from "./api.js";
import { PRICE_DISPLAY } from "./config.js"

const connectBtn = document.getElementById("connectBtn") as HTMLButtonElement | null;
const consentCheckbox = document.getElementById("privacyConsent") as HTMLInputElement | null;
const priceLabel = document.getElementById("priceLabel");

// Price varies per locale and gets set later — one config value
// (config.ts -> PRICE_DISPLAY) drives this line instead of it being
// hardcoded in the HTML.
if (priceLabel) {
  priceLabel.textContent = `7-day free trial · then ${PRICE_DISPLAY} · cancel anytime`;
}

if (connectBtn && consentCheckbox) {
  // Button starts disabled (see index.html); only enabled once the
  // person has explicitly agreed to the privacy policy.
  consentCheckbox.addEventListener("change", () => {
    connectBtn.disabled = !consentCheckbox.checked;
  });

  connectBtn.addEventListener("click", () => {
    if (!consentCheckbox.checked) return; // guard, shouldn't fire while disabled
    window.location.href = loginUrl();
  });
}

// ---------------------------------------------------------------
// Hero workflow chips: cycle a highlight through the three steps so the
// comment -> match -> DM mechanism reads at a glance, no scrolling or
// reading required. Respects prefers-reduced-motion by holding on step 1.
// ---------------------------------------------------------------
const CHIP_IDLE = ["border-line", "bg-transparent"];
const CHIP_ACTIVE = ["border-teal", "bg-teal-soft", "shadow-glow-teal"];

const chips = Array.from(document.querySelectorAll<HTMLElement>("#workflowRow [data-chip]"));
const reduceMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

function setActiveChip(index: number): void {
  chips.forEach((chip, i) => {
    chip.classList.remove(...CHIP_IDLE, ...CHIP_ACTIVE);
    chip.classList.add(...(i === index ? CHIP_ACTIVE : CHIP_IDLE));
  });
}

if (chips.length > 0) {
  setActiveChip(0);
  if (!reduceMotion) {
    let active = 0;
    setInterval(() => {
      active = (active + 1) % chips.length;
      setActiveChip(active);
    }, 1600);
  }
}