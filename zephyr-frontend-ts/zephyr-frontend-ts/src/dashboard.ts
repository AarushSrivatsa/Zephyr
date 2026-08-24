// Zephyr — dashboard page
import * as api from "./api.js";
import { ApiError } from "./api.js";
import type { RuleDto } from "./types.js";
import { toast, escapeHtml, formatDate, requireEl } from "./ui.js";

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
  const claims = api.tokens.decodeToken(api.tokens.get()!);
  const userId = claims?.user_id ?? "unknown";
  requireEl("railUserId").textContent = userId;
  requireEl("accountUserId").textContent = userId;

  // ---------- view switching ----------
  const views = document.querySelectorAll<HTMLElement>(".view");
  const navLinks = document.querySelectorAll<HTMLButtonElement>(".rail-link[data-view]");

  function showView(name: string): void {
    views.forEach((v) => v.classList.toggle("is-active", v.id === "view-" + name));
    navLinks.forEach((l) => l.classList.toggle("is-active", l.dataset.view === name));
    if (name === "billing") void refreshBillingStatus();
  }
  navLinks.forEach((l) => l.addEventListener("click", () => showView(l.dataset.view!)));

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

  // ---------- account deletion ----------
  requireEl("deleteAccountBtn").addEventListener("click", () => {
    void (async () => {
      const ok = await askConfirm(
        "Disconnect Instagram?",
        "This deletes your rules and logs and signs you out everywhere. This can't be undone."
      );
      if (!ok) return;
      try {
        await api.deleteAccount();
        api.tokens.clear();
        toast("Account disconnected.", "ok");
        window.location.href = "index.html";
      } catch (e) {
        toast(errorMessage(e, "Couldn't delete your account."), "error");
      }
    })();
  });

  // =========================================================
  // DM VARIANTS
  // =========================================================
  function renderVariants(messages: string[]): void {
    const container = requireEl("dmVariants");
    container.innerHTML = "";
    const toRender = messages.length ? messages : [""];
    toRender.forEach((msg) => addVariantRow(msg));
  }

  function addVariantRow(value = ""): void {
    const container = requireEl("dmVariants");
    const row = document.createElement("div");
    row.style.cssText = "display:flex; gap:8px; align-items:flex-start;";

    const ta = document.createElement("textarea");
    ta.className = "dm-variant-input";
    ta.placeholder = "DM message…";
    ta.required = true;
    ta.value = value;
    ta.style.cssText = "flex:1; min-height:72px;";

    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "btn btn-ghost btn-sm";
    removeBtn.textContent = "✕";
    removeBtn.style.cssText = "margin-top:4px; flex:none;";
    removeBtn.addEventListener("click", () => {
      if (container.querySelectorAll(".dm-variant-input").length <= 1) return;
      row.remove();
    });

    row.appendChild(ta);
    row.appendChild(removeBtn);
    container.appendChild(row);
  }

  function getVariants(): string[] {
    return Array.from(document.querySelectorAll<HTMLTextAreaElement>(".dm-variant-input"))
      .map((ta) => ta.value.trim())
      .filter(Boolean);
  }

  requireEl("addVariantBtn").addEventListener("click", () => addVariantRow());

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
    const statusBadge = rule.is_active
      ? `<span class="badge">Active</span>`
      : `<span class="badge is-off">Paused</span>`;
    const dmPreview = escapeHtml(rule.dm_message[0]) +
      (rule.dm_message.length > 1
        ? ` <span style="color:var(--ink-faint);font-size:12px;">+${rule.dm_message.length - 1} variant${rule.dm_message.length > 1 ? "s" : ""}</span>`
        : "");
    return `
      <div class="card rule-card" data-id="${rule.id}">
        <div class="rule-top">
          <div>
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
            <div class="txt">${rule.reply_message ? escapeHtml(rule.reply_message) : "—"}</div>
          </div>
        </div>
        <div class="rule-foot">
          <div class="rule-stats">
            <span><span class="num">${rule.count}</span> sent</span>
            <span>Since ${formatDate(rule.created_at)}</span>
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
  const ruleSubmitBtn = requireEl<HTMLButtonElement>("ruleSubmitBtn");
  let editingRuleId: number | null = null;

  function openRuleModal(id: number | null): void {
    editingRuleId = id;
    ruleForm.reset();
    renderVariants([""]);
    ruleActiveField.style.display = editingRuleId ? "block" : "none";

    if (editingRuleId) {
      ruleModalTitle.textContent = "Edit rule";
      ruleSubmitBtn.textContent = "Save changes";
      api.getRule(editingRuleId)
        .then((rule) => {
          requireEl<HTMLInputElement>("ruleLink").value = rule.link;
          requireEl<HTMLInputElement>("ruleCatchphrase").value = rule.catchphrase;
          renderVariants(rule.dm_message);
          requireEl<HTMLTextAreaElement>("ruleReply").value = rule.reply_message ?? "";
          ruleActiveInput.checked = rule.is_active;
          ruleActiveLabel.textContent = rule.is_active ? "Active" : "Paused";
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
      const dmMessages = getVariants();
      const replyMessage = requireEl<HTMLTextAreaElement>("ruleReply").value.trim();

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
            reply_message: replyMessage || null,
            is_active: ruleActiveInput.checked,
          });
          toast("Rule updated.", "ok");
        } else {
          await api.createRule({
            link,
            catchphrase,
            dm_message: dmMessages,
            reply_message: replyMessage || null,
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