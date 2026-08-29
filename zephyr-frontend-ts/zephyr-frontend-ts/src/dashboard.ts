// Zephyr — dashboard page
import * as api from "./api.js";
import { ApiError } from "./api.js";
import type { RuleDto } from "./types.js";
import { toast, escapeHtml, formatDate, requireEl, setHidden } from "./ui.js";

// =========================================================
// dm_message / reply_message normalization
// =========================================================
function parsePgTextArray(raw: string): string[] {
  const inner = raw.slice(1, -1);
  if (inner === "") return [];

  const result: string[] = [];
  let current = "";
  let inQuotes = false;

  for (let i = 0; i < inner.length; i++) {
    const ch = inner[i];
    if (inQuotes) {
      if (ch === "\\" && i + 1 < inner.length) {
        current += inner[i + 1];
        i++;
      } else if (ch === '"') {
        inQuotes = false;
      } else {
        current += ch;
      }
    } else if (ch === '"') {
      inQuotes = true;
    } else if (ch === ",") {
      result.push(current);
      current = "";
    } else {
      current += ch;
    }
  }
  result.push(current);
  return result;
}

function normalizeMessageArray(raw: unknown): string[] {
  if (Array.isArray(raw)) return raw as string[];
  if (typeof raw === "string") {
    const trimmed = raw.trim();
    if (trimmed.startsWith("{") && trimmed.endsWith("}")) {
      return parsePgTextArray(trimmed);
    }
    return trimmed ? [trimmed] : [];
  }
  return [];
}

if (!api.tokens.isLoggedIn()) {
  setHidden(requireEl("authGate"), false);
} else {
  setHidden(requireEl("app"), false, "grid");
  boot();
}

function boot(): void {
  try {
    bootInner();
  } catch (e) {
    console.error("Dashboard failed to initialize:", e);
    toast("Something went wrong loading the dashboard. Try refreshing.", "error");
  }
}

// Utility classes swapped on the rail nav buttons to express active/inactive state.
const NAV_ACTIVE = ["text-teal-deep", "bg-teal-soft", "font-semibold"];
const NAV_INACTIVE = ["text-ink-soft", "font-medium", "hover:bg-bg-dim", "hover:text-ink"];

function bootInner(): void {
  void api.getMe().then((profile) => {
    requireEl("railUsername").textContent = "@" + profile.username;
    requireEl("accountUsername").textContent = "@" + profile.username;

    for (const id of ["railAvatar", "accountAvatar"]) {
      const img = document.getElementById(id) as HTMLImageElement | null;
      if (img) {
        img.src = profile.profile_pic_url;
        setHidden(img, false);
      }
    }
  }).catch(() => {
    // leave placeholder "—" if fetch fails
  });

  // ---------- view switching ----------
  const views = document.querySelectorAll<HTMLElement>(".view");
  const navLinks = document.querySelectorAll<HTMLButtonElement>(".nav-link[data-view]");

  function showView(name: string): void {
    views.forEach((v) => setHidden(v, v.id !== "view-" + name));
    navLinks.forEach((l) => {
      const isActive = l.dataset.view === name;
      l.classList.remove(...NAV_ACTIVE, ...NAV_INACTIVE);
      l.classList.add(...(isActive ? NAV_ACTIVE : NAV_INACTIVE));
    });
    if (name === "billing") void refreshBillingStatus();
  }
  navLinks.forEach((l) => l.addEventListener("click", () => showView(l.dataset.view!)));

  const requestedView = new URLSearchParams(window.location.search).get("view");
  if (requestedView && ["rules", "billing", "account"].includes(requestedView)) {
    showView(requestedView);
  }

  // ---------- sign out ----------
  async function doLogout(): Promise<void> {
    await api.logout();
    window.location.href = "index.html";
  }
  requireEl("logoutBtn").addEventListener("click", () => void doLogout());
  requireEl("accountLogoutBtn").addEventListener("click", () => void doLogout());

  // ---------- confirm modal ----------
  const confirmOverlay = requireEl("confirmModalOverlay");
  let confirmResolver: ((result: boolean) => void) | null = null;

  function askConfirm(title: string, body: string): Promise<boolean> {
    requireEl("confirmTitle").textContent = title;
    requireEl("confirmBody").textContent = body;
    setHidden(confirmOverlay, false, "flex");
    return new Promise((resolve) => { confirmResolver = resolve; });
  }
  function closeConfirm(result: boolean): void {
    setHidden(confirmOverlay, true, "flex");
    confirmResolver?.(result);
    confirmResolver = null;
  }
  requireEl("confirmOkBtn").addEventListener("click", () => closeConfirm(true));
  requireEl("confirmCancelBtn").addEventListener("click", () => closeConfirm(false));
  requireEl("confirmClose").addEventListener("click", () => closeConfirm(false));
  confirmOverlay.addEventListener("click", (e) => { if (e.target === confirmOverlay) closeConfirm(false); });

  // =========================================================
  // VARIANT LISTS
  // =========================================================
  function renderVariants(containerId: string, messages: unknown): void {
    const container = requireEl(containerId);
    container.innerHTML = "";
    const list = normalizeMessageArray(messages);
    const toRender = containerId === "dmVariants" && list.length === 0 ? [""] : list;
    toRender.forEach((msg) => addVariantRow(containerId, msg));
  }

  function addVariantRow(containerId: string, value = ""): void {
    const isDm = containerId === "dmVariants";
    const container = requireEl(containerId);
    const row = document.createElement("div");
    row.className = "flex items-start gap-2";

    const ta = document.createElement("textarea");
    ta.className =
      (isDm ? "dm-variant-input" : "reply-variant-input") +
      ` flex-1 resize-y rounded-sm border border-line-strong bg-surface px-3.5 py-3 text-[15px] text-ink transition focus:border-teal focus:outline-none focus:ring-[3px] focus:ring-teal-soft ${isDm ? "min-h-[72px]" : "min-h-[60px]"}`;
    ta.placeholder = isDm ? "DM message…" : "Public reply…";
    ta.required = isDm;
    ta.value = value;

    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className =
      "mt-1 inline-flex flex-none items-center justify-center gap-2 rounded-md px-3.5 py-2 font-display text-[13.5px] font-semibold text-ink-soft transition hover:bg-teal/[0.06]";
    removeBtn.textContent = "✕";
    removeBtn.addEventListener("click", () => {
      if (isDm && container.querySelectorAll(".dm-variant-input").length <= 1) return;
      row.remove();
    });

    row.appendChild(ta);
    row.appendChild(removeBtn);
    container.appendChild(row);
  }

  function getVariants(containerId: string, className: string): string[] {
    return Array.from(document.querySelectorAll<HTMLTextAreaElement>(`#${containerId} .${className}`))
      .map((ta) => ta.value.trim())
      .filter(Boolean);
  }

  requireEl("addVariantBtn").addEventListener("click", () => addVariantRow("dmVariants"));
  requireEl("addReplyVariantBtn").addEventListener("click", () => addVariantRow("replyVariants"));

  // =========================================================
  // RULES
  // =========================================================
  const PAGE_SIZE = 10;
  let currentPage = 1;

  const rulesLoading = requireEl("rulesLoading");
  const rulesList = requireEl("rulesList");
  const rulesEmpty = requireEl("rulesEmpty");
  const pager = requireEl("pager");
  const pageLabel = requireEl("pageLabel");
  const subBanner = requireEl("subBanner");
  const subBannerText = requireEl("subBannerText");

  const BADGE_BASE = "inline-flex flex-none items-center gap-1.5 rounded-full px-2.5 py-1 font-mono text-[11.5px] tracking-wide";

  function ruleCardHtml(rule: RuleDto): string {
    const dmMessages = normalizeMessageArray(rule.dm_message);
    const replyMessages = normalizeMessageArray(rule.reply_message);
    const statusBadge = rule.is_active
      ? `<span class="${BADGE_BASE} bg-teal-soft text-teal">Active</span>`
      : `<span class="${BADGE_BASE} bg-white/[0.06] text-ink-faint">Paused</span>`;
    const dmPreview = escapeHtml(dmMessages[0] ?? "") +
      (dmMessages.length > 1
        ? ` <span class="text-xs text-ink-faint">+${dmMessages.length - 1} variant${dmMessages.length > 2 ? "s" : ""}</span>`
        : "");
    const replyPreview = replyMessages.length
      ? escapeHtml(replyMessages[0]) +
        (replyMessages.length > 1
          ? ` <span class="text-xs text-ink-faint">+${replyMessages.length - 1} variant${replyMessages.length > 2 ? "s" : ""}</span>`
          : "")
      : "—";
    const caseSensitiveTag = rule.is_case_sensitive
      ? ` <span class="text-xs text-ink-faint">Case sensitive</span>`
      : "";
    return `
      <div class="rule-card flex flex-col gap-3 rounded-lg border border-line bg-surface p-5 shadow-card" data-id="${rule.id}">
        <div class="flex items-start justify-between gap-3.5">
          <div class="min-w-0 flex-1">
            <div class="break-words font-mono text-[15px] font-medium text-ink">"${escapeHtml(rule.catchphrase)}"</div>
            <div class="mt-1 break-all text-xs text-ink-faint"><a class="text-teal hover:underline" href="${escapeHtml(rule.link)}" target="_blank" rel="noopener">${escapeHtml(rule.link)}</a></div>
          </div>
          ${statusBadge}
        </div>
        <div class="grid grid-cols-1 gap-3.5 text-[13.5px] sm:grid-cols-2">
          <div>
            <div class="mb-1 font-mono text-[11px] uppercase tracking-wide text-ink-faint">DM message</div>
            <div class="text-ink-soft">${dmPreview}</div>
          </div>
          <div>
            <div class="mb-1 font-mono text-[11px] uppercase tracking-wide text-ink-faint">Public reply</div>
            <div class="text-ink-soft">${replyPreview}</div>
          </div>
        </div>
        <div class="flex flex-wrap items-center justify-between gap-2.5 border-t border-dashed border-line pt-2.5">
          <div class="flex items-center gap-4 font-mono text-[13px] text-ink-soft">
            <span><span class="font-semibold text-ink">${rule.count}</span> sent</span>
            <span>Since ${formatDate(rule.created_at)}</span>
            ${caseSensitiveTag}
          </div>
          <div class="flex items-center gap-2">
            <label class="flex cursor-pointer items-center gap-2 text-xs text-ink-soft">
              <span class="relative inline-flex h-[22px] w-10 flex-none cursor-pointer">
                <input type="checkbox" class="toggle-active peer absolute inset-0 z-10 h-full w-full cursor-pointer opacity-0" ${rule.is_active ? "checked" : ""} />
                <span class="pointer-events-none absolute inset-0 rounded-full bg-line-strong transition-colors duration-150 peer-checked:bg-teal after:absolute after:left-[3px] after:top-[3px] after:h-4 after:w-4 after:rounded-full after:bg-surface after:transition-transform after:duration-150 after:content-[''] peer-checked:after:translate-x-[18px]"></span>
              </span>
              ${rule.is_active ? "On" : "Off"}
            </label>
            <button class="edit-btn inline-flex items-center justify-center gap-2 rounded-md px-3.5 py-2 font-display text-[13.5px] font-semibold text-ink-soft transition hover:bg-teal/[0.06]">Edit</button>
            <button class="delete-btn inline-flex items-center justify-center gap-2 rounded-md border border-danger-line px-3.5 py-2 font-display text-[13.5px] font-semibold text-danger transition hover:bg-danger-soft">Delete</button>
          </div>
        </div>
      </div>`;
  }

  async function loadRules(page = 1): Promise<void> {
    currentPage = page;
    setHidden(rulesLoading, false, "flex");
    setHidden(rulesList, true, "flex");
    setHidden(rulesEmpty, true);
    setHidden(pager, true, "flex");

    try {
      const rules = await api.listRules(page, PAGE_SIZE);
      setHidden(subBanner, true, "flex");
      setHidden(rulesLoading, true, "flex");

      if (rules.length === 0 && page === 1) {
        setHidden(rulesEmpty, false);
        return;
      }
      if (rules.length === 0 && page > 1) {
        await loadRules(page - 1);
        return;
      }

      rulesList.innerHTML = rules.map(ruleCardHtml).join("");
      setHidden(rulesList, false, "flex");
      wireRuleCardEvents();

      setHidden(pager, false, "flex");
      pageLabel.textContent = `Page ${page}`;
      (document.getElementById("prevPageBtn") as HTMLButtonElement).disabled = page <= 1;
      (document.getElementById("nextPageBtn") as HTMLButtonElement).disabled = rules.length < PAGE_SIZE;
    } catch (e) {
      setHidden(rulesLoading, true, "flex");
      if (e instanceof ApiError && e.status === 403) {
        setHidden(rulesEmpty, true);
        setHidden(rulesList, true, "flex");
        setHidden(subBanner, false, "flex");
        subBannerText.textContent =
          e.detail === "No active subscription"
            ? "Your trial has ended. Start a subscription to keep your rules running."
            : e.detail ?? "Your account needs an active subscription to manage rules.";
      } else {
        toast(errorMessage(e, "Couldn't load your rules."), "error");
      }
    }
  }

  requireEl("prevPageBtn").addEventListener("click", () => void loadRules(currentPage - 1));
  requireEl("nextPageBtn").addEventListener("click", () => void loadRules(currentPage + 1));
  requireEl("subBannerBtn").addEventListener("click", () => void openCheckout());

  function wireRuleCardEvents(): void {
    rulesList.querySelectorAll<HTMLElement>(".rule-card").forEach((card) => {
      const id = Number(card.dataset.id);
      card.querySelector(".edit-btn")?.addEventListener("click", () => openRuleModal(id));
      card.querySelector(".delete-btn")?.addEventListener("click", () => void deleteRule(id));
      card.querySelector(".toggle-active")?.addEventListener("change", (e) => {
        void toggleActive(id, (e.target as HTMLInputElement).checked);
      });
    });
  }

  async function toggleActive(id: number, isActive: boolean): Promise<void> {
    try {
      await api.updateRule(id, { is_active: isActive });
      toast(isActive ? "Rule turned on." : "Rule paused.", "ok");
    } catch (e) {
      toast(errorMessage(e, "Couldn't update that rule."), "error");
    }
    await loadRules(currentPage);
  }

  async function deleteRule(id: number): Promise<void> {
    const ok = await askConfirm(
      "Delete this rule?",
      "Comments matching this catchphrase will stop being answered. This can't be undone."
    );
    if (!ok) return;
    try {
      await api.deleteRule(id);
      toast("Rule deleted.", "ok");
      await loadRules(currentPage);
    } catch (e) {
      toast(errorMessage(e, "Couldn't delete that rule."), "error");
    }
  }

  // ---------- rule modal ----------
  const ruleModalOverlay = requireEl("ruleModalOverlay");
  const ruleForm = requireEl<HTMLFormElement>("ruleForm");
  const ruleModalTitle = requireEl("ruleModalTitle");
  const ruleActiveField = requireEl("ruleActiveField");
  const ruleActiveInput = requireEl<HTMLInputElement>("ruleActive");
  const ruleActiveLabel = requireEl("ruleActiveLabel");
  const ruleCaseSensitiveInput = requireEl<HTMLInputElement>("ruleCaseSensitive");
  const ruleCaseSensitiveLabel = requireEl("ruleCaseSensitiveLabel");
  const ruleSubmitBtn = requireEl<HTMLButtonElement>("ruleSubmitBtn");
  let editingRuleId: number | null = null;

  ruleCaseSensitiveInput.addEventListener("change", () => {
    ruleCaseSensitiveLabel.textContent = ruleCaseSensitiveInput.checked
      ? "On — exact case match only"
      : "Off — matches any case";
  });

  function openRuleModal(id: number | null): void {
    editingRuleId = id;
    ruleForm.reset();
    renderVariants("dmVariants", [""]);
    renderVariants("replyVariants", []);
    setHidden(ruleActiveField, !editingRuleId);
    ruleCaseSensitiveInput.checked = false;
    ruleCaseSensitiveLabel.textContent = "Off — matches any case";

    if (editingRuleId) {
      ruleModalTitle.textContent = "Edit rule";
      ruleSubmitBtn.textContent = "Save changes";
      api.getRule(editingRuleId)
        .then((rule) => {
          requireEl<HTMLInputElement>("ruleLink").value = rule.link;
          requireEl<HTMLInputElement>("ruleCatchphrase").value = rule.catchphrase;
          renderVariants("dmVariants", rule.dm_message);
          renderVariants("replyVariants", rule.reply_message ?? []);
          ruleActiveInput.checked = rule.is_active;
          ruleActiveLabel.textContent = rule.is_active ? "Active" : "Paused";
          ruleCaseSensitiveInput.checked = rule.is_case_sensitive;
          ruleCaseSensitiveLabel.textContent = rule.is_case_sensitive
            ? "On — exact case match only"
            : "Off — matches any case";
        })
        .catch((e: unknown) => {
          toast(errorMessage(e, "Couldn't load that rule."), "error");
          closeRuleModal();
        });
    } else {
      ruleModalTitle.textContent = "New rule";
      ruleSubmitBtn.textContent = "Create rule";
    }
    setHidden(ruleModalOverlay, false, "flex");
    requireEl("ruleLink").focus();
  }

  function closeRuleModal(): void {
    setHidden(ruleModalOverlay, true, "flex");
    editingRuleId = null;
  }

  ruleActiveInput.addEventListener("change", () => {
    ruleActiveLabel.textContent = ruleActiveInput.checked ? "Active" : "Paused";
  });

  requireEl("newRuleBtn").addEventListener("click", () => openRuleModal(null));
  requireEl("emptyNewRuleBtn").addEventListener("click", () => openRuleModal(null));
  requireEl("ruleCancelBtn").addEventListener("click", closeRuleModal);
  requireEl("ruleModalClose").addEventListener("click", closeRuleModal);
  ruleModalOverlay.addEventListener("click", (e) => { if (e.target === ruleModalOverlay) closeRuleModal(); });

  ruleForm.addEventListener("submit", (e) => {
    e.preventDefault();
    void (async () => {
      const link = requireEl<HTMLInputElement>("ruleLink").value.trim();
      const catchphrase = requireEl<HTMLInputElement>("ruleCatchphrase").value.trim();
      const dmMessages = getVariants("dmVariants", "dm-variant-input");
      const replyMessages = getVariants("replyVariants", "reply-variant-input");

      if (dmMessages.length === 0) {
        toast("Add at least one DM message.", "error");
        return;
      }

      ruleSubmitBtn.disabled = true;
      try {
        if (editingRuleId) {
          await api.updateRule(editingRuleId, {
            link,
            catchphrase,
            dm_message: dmMessages,
            reply_message: replyMessages.length ? replyMessages : null,
            is_active: ruleActiveInput.checked,
            is_case_sensitive: ruleCaseSensitiveInput.checked,
          });
          toast("Rule updated.", "ok");
        } else {
          await api.createRule({
            link,
            catchphrase,
            dm_message: dmMessages,
            reply_message: replyMessages.length ? replyMessages : null,
            is_case_sensitive: ruleCaseSensitiveInput.checked,
          });
          toast("Rule created.", "ok");
        }
        closeRuleModal();
        await loadRules(editingRuleId ? currentPage : 1);
      } catch (e) {
        toast(errorMessage(e, "Couldn't save that rule. Double check the post link."), "error");
      } finally {
        ruleSubmitBtn.disabled = false;
      }
    })();
  });

  // =========================================================
  // BILLING
  // =========================================================
  const BILLING_COLOR_CLASSES = ["text-ink-soft", "text-teal-deep", "text-accent-deep"];
  function setBillingColor(el: HTMLElement, cls: (typeof BILLING_COLOR_CLASSES)[number]): void {
    el.classList.remove(...BILLING_COLOR_CLASSES);
    el.classList.add(cls);
  }

  async function openCheckout(): Promise<void> {
    try {
      const url = await api.startCheckout();
      if (url) window.location.href = url;
      else toast("Couldn't start checkout. Try again in a moment.", "error");
    } catch (e) {
      toast(errorMessage(e, "Couldn't start checkout."), "error");
    }
  }
  requireEl("billingCheckoutBtn").addEventListener("click", () => void openCheckout());

  async function refreshBillingStatus(): Promise<void> {
    const el = requireEl("billingStatus");
    const btn = requireEl<HTMLButtonElement>("billingCheckoutBtn");
    setBillingColor(el, "text-ink-soft");
    el.textContent = "Checking…";
    try {
      const active = await api.hasActiveSubscription();
      el.textContent = active ? "Active" : "Inactive — subscribe to continue";
      setBillingColor(el, active ? "text-teal-deep" : "text-accent-deep");
      setHidden(btn, active);
    } catch {
      el.textContent = "Unknown";
      setBillingColor(el, "text-ink-soft");
      setHidden(btn, false);
    }
  }

  void loadRules(1);
}

function errorMessage(e: unknown, fallback: string): string {
  if (e instanceof ApiError) return e.detail ?? e.message ?? fallback;
  if (e instanceof Error) return e.message || fallback;
  return fallback;
}
