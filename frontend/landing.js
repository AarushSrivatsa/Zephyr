(function () {
  "use strict";

  const CONFIG = window.ZEPHYR_CONFIG || {};

  const API_BASE = String(
    CONFIG.API_BASE ||
    CONFIG.API_URL ||
    window.API_BASE ||
    ""
  ).replace(/\/$/, "");

  const INSTAGRAM_CONNECT_URL =
    CONFIG.INSTAGRAM_CONNECT_URL ||
    CONFIG.INSTAGRAM_AUTH_URL ||
    API_BASE + "/auth/instagram";

  function get(id) {
    return document.getElementById(id);
  }

  function ensureToastContainer() {
    let container = get("toastContainer");

    if (!container) {
      container = document.createElement("div");
      container.id = "toastContainer";
      container.className = "toast-container";
      document.body.appendChild(container);
    }

    return container;
  }

  function toast(message, type) {
    const container = ensureToastContainer();
    const item = document.createElement("div");

    item.className = "toast " + (type || "");
    item.textContent = message;

    container.appendChild(item);

    setTimeout(function () {
      item.style.opacity = "0";
      item.style.transform = "translateY(8px)";

      setTimeout(function () {
        item.remove();
      }, 180);
    }, 3200);
  }

  function setLoading(button, loading, label) {
    if (!button) return;

    if (loading) {
      if (!button.dataset.originalText) {
        button.dataset.originalText = button.textContent.trim();
      }

      button.disabled = true;
      button.innerHTML =
        '<span class="spinner"></span>' +
        (label || "Connecting…");
    } else {
      button.disabled = false;
      button.textContent =
        button.dataset.originalText ||
        "Connect your Instagram";
    }
  }

  function hasStoredSession() {
    const keys = [
      "access_token",
      "accessToken",
      "zephyr_access_token",
      "token",
      "jwt"
    ];

    return keys.some(function (key) {
      try {
        return Boolean(localStorage.getItem(key));
      } catch (error) {
        return false;
      }
    });
  }

  function connectInstagram(button) {
    if (!INSTAGRAM_CONNECT_URL) {
      toast(
        "Instagram connection URL is not configured.",
        "error"
      );
      return;
    }

    setLoading(button, true, "Connecting…");

    window.location.href = INSTAGRAM_CONNECT_URL;
  }

  function setupConnectButtons() {
    const buttons = [
      get("navConnectBtn"),
      get("heroConnectBtn"),
      get("pricingConnectBtn")
    ];

    buttons.forEach(function (button) {
      if (!button) return;

      button.addEventListener("click", function () {
        connectInstagram(button);
      });
    });
  }

  function setupDashboardLink() {
    const dashboardLink = get("navDashboardLink");

    if (!dashboardLink) return;

    if (hasStoredSession()) {
      dashboardLink.style.display = "inline-flex";
    }
  }

  function setupScrollReveal() {
    if (!("IntersectionObserver" in window)) return;

    const items = document.querySelectorAll(
      ".step, .feature, .rule-mock, .price-card"
    );

    items.forEach(function (item) {
      item.style.opacity = "0";
      item.style.transform = "translateY(10px)";
      item.style.transition =
        "opacity .45s ease, transform .45s ease";
    });

    const observer = new IntersectionObserver(
      function (entries) {
        entries.forEach(function (entry) {
          if (!entry.isIntersecting) return;

          entry.target.style.opacity = "1";
          entry.target.style.transform = "translateY(0)";

          observer.unobserve(entry.target);
        });
      },
      {
        threshold: 0.12
      }
    );

    items.forEach(function (item) {
      observer.observe(item);
    });
  }

  function setupHashLinks() {
    document
      .querySelectorAll('a[href^="#"]')
      .forEach(function (link) {
        link.addEventListener("click", function (event) {
          const targetId = link.getAttribute("href");

          if (!targetId || targetId === "#") return;

          const target = document.querySelector(targetId);

          if (!target) return;

          event.preventDefault();

          target.scrollIntoView({
            behavior: "smooth",
            block: "start"
          });
        });
      });
  }

  function init() {
    setupConnectButtons();
    setupDashboardLink();
    setupScrollReveal();
    setupHashLinks();

    const params = new URLSearchParams(
      window.location.search
    );

    if (params.has("connected")) {
      toast(
        "Instagram connected successfully.",
        "success"
      );
    }
  }

  if (document.readyState === "loading") {
    document.addEventListener(
      "DOMContentLoaded",
      init
    );
  } else {
    init();
  }

  window.ZephyrLanding = {
    connectInstagram: connectInstagram,
    toast: toast
  };
})();