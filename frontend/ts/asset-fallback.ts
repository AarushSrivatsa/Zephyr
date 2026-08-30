// Zephyr — graceful fallback for brand assets
//
// /assets/instagram-logo.png, /assets/zephyr-logo.png, and
// /assets/zephyr-font.png are placeholders until real brand files are
// dropped into /assets. Any <img data-fallback> that fails to load hides
// itself and reveals the placeholder markup immediately after it in the
// DOM, instead of leaving a broken-image icon on the page. Once the real
// files exist, this becomes a no-op — the images just load.
//
// Module scripts are deferred, so by the time this runs, a 404'd image's
// `error` event may already have fired and won't fire again — check
// `complete`/`naturalWidth` for images that already failed, and still
// listen for `error` to catch any that are still in flight.
function showFallback(img: HTMLImageElement): void {
  img.classList.add("hidden");
  img.nextElementSibling?.classList.remove("hidden");
}

document.querySelectorAll<HTMLImageElement>("img[data-fallback]").forEach((img) => {
  if (img.complete && img.naturalWidth === 0) {
    showFallback(img);
  } else {
    img.addEventListener("error", () => showFallback(img), { once: true });
  }
});
