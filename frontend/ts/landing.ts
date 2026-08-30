// Zephyr — landing page (index.html)
//
// Signed-in visitors are bounced to /dashboard by an inline script in
// index.html's <head>, before this module even loads — so everything below
// only ever runs for a signed-out visitor.
import { loginUrl } from "./api.js";

function goConnect(): void {
  window.location.href = loginUrl();
}

for (const id of ["heroConnectBtn", "navConnectBtn", "pricingConnectBtn"]) {
  document.getElementById(id)?.addEventListener("click", goConnect);
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
