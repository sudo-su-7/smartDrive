/* SMART DRIVE — Main JavaScript */
"use strict";

// ── Auto-dismiss flash messages ─────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const alerts = document.querySelectorAll("#flash-messages .alert");
  alerts.forEach(alert => {
    setTimeout(() => {
      const bsAlert = bootstrap.Alert.getOrCreateInstance(alert);
      bsAlert.close();
    }, 6000);
  });
});

// ── Confirm delete / destructive actions ────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-confirm]").forEach(el => {
    el.addEventListener("click", e => {
      const msg = el.dataset.confirm || "Are you sure?";
      if (!confirm(msg)) e.preventDefault();
    });
  });
});

// ── Date range validation (booking form) ────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const startEl = document.getElementById("start_date");
  const endEl   = document.getElementById("end_date");
  const totalEl = document.getElementById("total-amount");
  const daysEl  = document.getElementById("total-days");
  const pricePerDay = parseFloat(document.getElementById("price_per_day_data")?.dataset.price || "0");

  function updateTotal() {
    if (!startEl || !endEl || !startEl.value || !endEl.value) return;
    const start = new Date(startEl.value);
    const end   = new Date(endEl.value);
    if (end <= start) {
      endEl.setCustomValidity("Return date must be after pick-up date.");
      if (totalEl) totalEl.textContent = "—";
      if (daysEl)  daysEl.textContent  = "—";
      return;
    }
    endEl.setCustomValidity("");
    const days = Math.max(Math.ceil((end - start) / (1000 * 60 * 60 * 24)), 1);
    const total = (days * pricePerDay).toFixed(2);
    if (daysEl)  daysEl.textContent  = `${days} day${days !== 1 ? "s" : ""}`;
    if (totalEl) totalEl.textContent = `KES ${Number(total).toLocaleString()}`;
  }

  // Set min date to today
  if (startEl) {
    const today = new Date().toISOString().split("T")[0];
    startEl.setAttribute("min", today);
    startEl.addEventListener("change", () => {
      if (endEl) endEl.setAttribute("min", startEl.value);
      updateTotal();
    });
  }
  if (endEl) endEl.addEventListener("change", updateTotal);
  updateTotal();
});

// ── Image preview on file input ─────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const imgInput = document.getElementById("image");
  const preview  = document.getElementById("image-preview");
  if (imgInput && preview) {
    imgInput.addEventListener("change", function () {
      const file = this.files[0];
      if (!file) return;
      const allowedTypes = ["image/png","image/jpeg","image/webp"];
      if (!allowedTypes.includes(file.type)) {
        alert("Only PNG, JPG, or WebP images are allowed.");
        this.value = "";
        return;
      }
      if (file.size > 5 * 1024 * 1024) {
        alert("Image must be under 5 MB.");
        this.value = "";
        return;
      }
      const reader = new FileReader();
      reader.onload = e => {
        preview.src = e.target.result;
        preview.classList.remove("d-none");
      };
      reader.readAsDataURL(file);
    });
  }
});

// ── Tooltip init ─────────────────────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const tooltips = document.querySelectorAll("[data-bs-toggle='tooltip']");
  tooltips.forEach(el => bootstrap.Tooltip.getOrCreateInstance(el));
});

// ── Password strength indicator ──────────────────────────────────────────────
document.addEventListener("DOMContentLoaded", () => {
  const pwField = document.getElementById("password");
  const strengthBar = document.getElementById("password-strength");
  if (!pwField || !strengthBar) return;

  pwField.addEventListener("input", () => {
    const pw = pwField.value;
    let score = 0;
    if (pw.length >= 8)  score++;
    if (/[A-Z]/.test(pw)) score++;
    if (/[a-z]/.test(pw)) score++;
    if (/\d/.test(pw))    score++;
    if (/[^A-Za-z0-9]/.test(pw)) score++;

    const colours = ["", "bg-danger", "bg-warning", "bg-info", "bg-primary", "bg-success"];
    const labels  = ["", "Very Weak", "Weak", "Fair", "Good", "Strong"];
    strengthBar.style.width = `${score * 20}%`;
    strengthBar.className = `progress-bar ${colours[score]}`;
    strengthBar.textContent = labels[score];
  });
});
