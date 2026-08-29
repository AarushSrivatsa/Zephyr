// Zephyr — dashboard page
import * as api from "./api.js";
import { ApiError } from "./api.js";
import type { RuleDto } from "./types.js";
import { toast, escapeHtml, formatDate, requireEl } from "./ui.js";

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
  requireEl("authGate").style.display = "block";
} else {
  requireEl("app").style.display = "grid";
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

function bootInner(): void {
  void api.getMe().then((profile) => {
    requireEl("railUsername").textContent = "@" + profile.username;
    requireEl("accountUsername").textContent = "@" + profile.username;

    for (const id of ["railAvatar", "accountAvatar"]) {
      const img = document.getElementById(id) as HTMLImageElement | null;
      if (img) {
        img.src = profile.profile_pic_url;
        img.style.display = "block";
      }
    }
  }).catch(() => {
    // leave placeholder "—" if fetch fails
  });

  // ---------- view switching ----------
  const views = document.querySelectorAll<HTMLElement>(".view");
  const navLinks = document.querySelectorAll<HTMLButtonElement>(".rail-link[data-view]");

  function showView(name: string): void {
    views.forEach((v) => v.classList.toggle("is-active", v.id === "view-" + name));
    navLinks.forEach((l) => l.classList.toggle("is-active", l.dataset.view === name));
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
    confirmOverlay.classList.add("is-open");
    return new Promise((resolve) => { confirmResolver = resolve; });
  }
  function closeConfirm(result: boolean): void {
    confirmOverlay.classList.remove("is-open");
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
    row.style.cssText = "display:flex; gap:8px; align-items:flex-start;";

    const ta = document.createElement("textarea");
    ta.className = isDm ? "dm-variant-input" : "reply-variant-input";
    ta.placeholder = isDm ? "DM message…" : "Public reply…";
    ta.required = isDm;
    ta.value = value;
    ta.style.cssText = "flex:1; min-height:" + (isDm ? "72px" : "60px") + ";";

    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "btn btn-ghost btn-sm";
    removeBtn.textContent = "✕";
    removeBtn.style.cssText = "margin-top:4px; flex:none;";
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

  function ruleCardHtml(rule: RuleDto): string {
    const dmMessages = normalizeMessageArray(rule.dm_message);
    const replyMessages = normalizeMessageArray(rule.reply_message);
    const statusBadge = rule.is_active
      ? `<span class="badge">Active</span>`
      : `<span class="badge is-off">Paused</span>`;
    const dmPreview = escapeHtml(dmMessages[0] ?? "") +
      (dmMessages.length > 1
        ? ` <span style="color:var(--ink-faint);font-size:12px;">+${dmMessages.length - 1} variant${dmMessages.length > 2 ? "s" : ""}</span>`
        : "");
    const replyPreview = replyMessages.length
      ? escapeHtml(replyMessages[0]) +
        (replyMessages.length > 1
          ? ` <span style="color:var(--ink-faint);font-size:12px;">+${replyMessages.length - 1} variant${replyMessages.length > 2 ? "s" : ""}</span>`
          : "")
      : "—";
    const caseSensitiveTag = rule.is_case_sensitive
      ? ` <span style="color:var(--ink-faint);font-size:12px;">Case sensitive</span>`
      : "";
    return `
      <div class="card rule-card" data-id="${rule.id}">
      <div class="rule-top">
          <div class="rule-top-main">
            <div class="rule-catch">"${escapeHtml(rule.catchphrase)}"</div>
            <div class="rule-link"><a href="${escapeHtml(rule.link)}" target="_blank" rel="noopener">${escapeHtml(rule.link)}</a></div>
          </div>
          ${statusBadge}
        </div>
        <div class="rule-msgs">
          <div>
            <div class="lbl">DM message</div>
            <div class="txt">${dmPreview}</div>
          </div>
          <div>
            <div class="lbl">Public reply</div>
            <div class="txt">${replyPreview}</div>
          </div>
        </div>
        <div class="rule-foot">
          <div class="rule-stats">
            <span><span class="num">${rule.count}</span> sent</span>
            <span>Since ${formatDate(rule.created_at)}</span>
            ${caseSensitiveTag}
          </div>
          <div class="rule-actions">
            <label class="rule-toggle">
              <span class="switch">
                <input type="checkbox" class="toggle-active" ${rule.is_active ? "checked" : ""} />
                <span class="track"></span>
              </span>
              ${rule.is_active ? "On" : "Off"}
            </label>
            <button class="btn btn-ghost btn-sm edit-btn">Edit</button>
            <button class="btn btn-danger btn-sm delete-btn">Delete</button>
          </div>
        </div>
      </div>`;
  }

  async function loadRules(page = 1): Promise<void> {
    currentPage = page;
    rulesLoading.style.display = "flex";
    rulesList.style.display = "none";
    rulesEmpty.style.display = "none";
    pager.style.display = "none";

    try {
      const rules = await api.listRules(page, PAGE_SIZE);
      subBanner.style.display = "none";
      rulesLoading.style.display = "none";

      if (rules.length === 0 && page === 1) {
        rulesEmpty.style.display = "block";
        return;
      }
      if (rules.length === 0 && page > 1) {
        await loadRules(page - 1);
        return;
      }

      rulesList.innerHTML = rules.map(ruleCardHtml).join("");
      rulesList.style.display = "flex";
      wireRuleCardEvents();

      pager.style.display = "flex";
      pageLabel.textContent = `Page ${page}`;
      (document.getElementById("prevPageBtn") as HTMLButtonElement).disabled = page <= 1;
      (document.getElementById("nextPageBtn") as HTMLButtonElement).disabled = rules.length < PAGE_SIZE;
    } catch (e) {
      rulesLoading.style.display = "none";
      if (e instanceof ApiError && e.status === 403) {
        rulesEmpty.style.display = "none";
        rulesList.style.display = "none";
        subBanner.style.display = "flex";
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
    ruleActiveField.style.display = editingRuleId ? "block" : "none";
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
    ruleModalOverlay.classList.add("is-open");
    requireEl("ruleLink").focus();
  }

  function closeRuleModal(): void {
    ruleModalOverlay.classList.remove("is-open");
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
    const btn = requireEl("billingCheckoutBtn");
    el.textContent = "Checking…";
    try {
      const active = await api.hasActiveSubscription();
      el.textContent = active ? "Active" : "Inactive — subscribe to continue";
      el.style.color = active ? "var(--teal-deep)" : "var(--accent-deep)";
      btn.style.display = active ? "none" : "block";
    } catch {
      el.textContent = "Unknown";
      btn.style.display = "block";
    }
  }

  void loadRules(1);
}

function errorMessage(e: unknown, fallback: string): string {
  if (e instanceof ApiError) return e.detail ?? e.message ?? fallback;
  if (e instanceof Error) return e.message || fallback;
  return fallback;
}