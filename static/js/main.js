Finflow/static/js/main.js#L1-134
(function () {
  // Small DOM helpers
  const $ = (sel, root = document) => root.querySelector(sel);
  const $$ = (sel, root = document) => Array.from(root.querySelectorAll(sel));

  // Toggle sidebar visibility for responsive layout
  function initSidebarToggle() {
    const toggle = $(".sidebar-toggle");
    const sidebar = $(".sidebar");
    if (!toggle || !sidebar) return;

    toggle.addEventListener("click", () => {
      sidebar.classList.toggle("collapsed");
      document.body.classList.toggle("sidebar-collapsed");
    });
  }

  // Simple currency formatter (uses browser locale)
  function formatCurrency(amount) {
    try {
      return new Intl.NumberFormat(navigator.language || "en-US", {
        style: "currency",
        currency: "USD",
        maximumFractionDigits: 2,
      }).format(Number(amount) || 0);
    } catch {
      return `$${Number(amount || 0).toFixed(2)}`;
    }
  }

  // Alerts area helper
  function showAlert(message, type = "info", timeout = 3500) {
    const container =
      $("#alerts") || document.body.appendChild(createAlertsContainer());
    const el = document.createElement("div");
    el.className = `alert alert-${type}`;
    el.textContent = message;
    container.appendChild(el);
    setTimeout(() => {
      el.classList.add("visible");
    }, 10);
    if (timeout) {
      setTimeout(() => {
        el.classList.remove("visible");
        setTimeout(() => el.remove(), 300);
      }, timeout);
    }
  }

  function createAlertsContainer() {
    const c = document.createElement("div");
    c.id = "alerts";
    c.className = "alerts-container";
    document.body.appendChild(c);
    return c;
  }

  // Basic client-side form validation for required fields and numeric amounts
  function initFormValidation() {
    const forms = $$("form[data-validate]");
    forms.forEach((form) => {
      form.addEventListener("submit", (e) => {
        const required = $$("[data-required]", form);
        let valid = true;
        required.forEach((el) => {
          const val = (el.value || "").trim();
          if (!val) {
            valid = false;
            el.classList.add("invalid");
          } else {
            el.classList.remove("invalid");
          }
          if (el.dataset.type === "number" && val) {
            if (isNaN(Number(val))) {
              valid = false;
              el.classList.add("invalid");
            }
          }
        });

        if (!valid) {
          e.preventDefault();
          showAlert("Please fix highlighted fields before submitting.", "warning");
        }
      });
    });
  }

  // Confirm before destructive actions (delete)
  function initDeleteConfirm() {
    const deletes = $$(".btn-delete[data-url]");
    deletes.forEach((btn) => {
      btn.addEventListener("click", async (e) => {
        e.preventDefault();
        const ok = window.confirm(btn.dataset.confirm || "Are you sure?");
        if (!ok) return;
        const url = btn.dataset.url;
        try {
          const resp = await fetch(url, {
            method: btn.dataset.method || "DELETE",
            headers: jsonHeaders(),
          });
          if (!resp.ok) throw new Error("Request failed");
          const payload = await resp.json().catch(() => ({}));
          showAlert(payload.message || "Deleted.", "success");
          // If element to remove specified, remove it
          if (btn.dataset.remove) {
            const el = btn.closest(btn.dataset.remove) || document.querySelector(btn.dataset.remove);
            if (el) el.remove();
          } else {
            // fallback: reload page
            setTimeout(() => location.reload(), 600);
          }
        } catch (err) {
          showAlert(err.message || "Delete failed", "danger");
        }
      });
    });
  }

  function jsonHeaders() {
    const headers = { "Content-Type": "application/json" };
    const tokenEl = document.querySelector('meta[name="csrf-token"]');
    if (tokenEl) headers["X-CSRFToken"] = tokenEl.getAttribute("content");
    return headers;
  }

  // Budget progress update: reads data attributes and updates progress bar width + label
  function initBudgetProgress() {
    const bars = $$(".budget-progress[data-spent][data-budget]");
    bars.forEach((bar) => {
      const spent = Number(bar.dataset.spent) || 0;
      const budget = Number(bar.dataset.budget) || 1;
      const pct = Math.min(100, Math.round((spent / budget) * 100));
      const fill = bar.querySelector(".budget-fill");
      const label = bar.querySelector(".budget-label");
      if (fill) fill.style.width = pct + "%";
      if (label) label.textContent = `${pct}% • ${formatCurrency(spent)} of ${formatCurrency(budget)}`;
      if (pct >= 100) bar.classList.add("over");
    });
  }

  // Initialize charts if Chart.js is present.
  // Expects canvas elements with data-chart containing JSON config.
  function initCharts() {
    if (typeof Chart === "undefined") return;
    const canvases = $$("canvas[data-chart]");
    canvases.forEach((c) => {
      try {
        const cfg = JSON.parse(c.dataset.chart);
        // Keep charts small and simple — user provides config object compatible with Chart.js
        // Provide default responsive settings
        cfg.options = cfg.options || {};
        cfg.options.responsive = true;
        new Chart(c.getContext("2d"), cfg);
      } catch (err) {
        // invalid JSON or chart config
        // eslint-disable-next-line no-console
        console.warn("Invalid chart config for canvas", c, err);
      }
    });
  }

  // Wire up simple UI actions (logout link for non-SPA)
  function initLogout() {
    const logout = $(".js-logout");
    if (!logout) return;
    logout.addEventListener("click", (e) => {
      // when logout is a link to /auth/logout, let it proceed - otherwise try POST
      if (logout.dataset.method && logout.dataset.method.toLowerCase() === "post") {
        e.preventDefault();
        fetch(logout.href || logout.dataset.url, {
          method: "POST",
          headers: jsonHeaders(),
        })
          .then((r) => {
            if (r.ok) location.reload();
            else showAlert("Logout failed", "danger");
          })
          .catch(() => showAlert("Logout failed", "danger"));
      }
    });
  }

  // Entry point
  function init() {
    initSidebarToggle();
    initFormValidation();
    initDeleteConfirm();
    initBudgetProgress();
    initCharts();
    initLogout();
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", init);
  } else {
    init();
  }

  // Expose small API for debugging / manual calls
  window.PinkLedgerUI = {
    showAlert,
    formatCurrency,
    initCharts,
    initBudgetProgress,
  };
})();
