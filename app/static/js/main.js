/**
 * SmartDrive – Main JS
 * Theme · Sidebar · Dropdown · Alerts · Forms
 */
'use strict';

/* ── Theme provider ─────────────────────────────────────────── */
const Theme = (() => {
  const KEY = 'sd-theme';
  const root = document.documentElement;

  function get() {
    return localStorage.getItem(KEY) ||
      (matchMedia('(prefers-color-scheme: dark)').matches ? 'dark' : 'light');
  }

  function apply(t) {
    root.setAttribute('data-theme', t);
    localStorage.setItem(KEY, t);
    // Update all toggle buttons
    document.querySelectorAll('.js-theme-toggle').forEach(btn => {
      const icon = btn.querySelector('i');
      if (icon) {
        icon.className = t === 'dark' ? 'bi bi-sun' : 'bi bi-moon';
      }
      btn.setAttribute('title', t === 'dark' ? 'Switch to light mode' : 'Switch to dark mode');
    });
  }

  function toggle() { apply(get() === 'dark' ? 'light' : 'dark'); }
  function init()   { apply(get()); }

  return { init, toggle, get };
})();

/* ── Dropdown ───────────────────────────────────────────────── */
function initDropdowns() {
  document.querySelectorAll('[data-dropdown]').forEach(trigger => {
    const menuId = trigger.dataset.dropdown;
    const menu   = document.getElementById(menuId) || trigger.nextElementSibling;
    if (!menu) return;

    const parent = trigger.closest('.dropdown') || trigger.parentElement;

    trigger.addEventListener('click', e => {
      e.stopPropagation();
      const isOpen = parent.classList.contains('open');
      // Close all
      document.querySelectorAll('.dropdown.open').forEach(d => d.classList.remove('open'));
      if (!isOpen) parent.classList.add('open');
    });
  });

  document.addEventListener('click', () => {
    document.querySelectorAll('.dropdown.open').forEach(d => d.classList.remove('open'));
  });

  document.addEventListener('keydown', e => {
    if (e.key === 'Escape') {
      document.querySelectorAll('.dropdown.open').forEach(d => d.classList.remove('open'));
    }
  });
}

/* ── Sidebar (app shell) ────────────────────────────────────── */
function initSidebar() {
  const sidebar  = document.getElementById('appSidebar');
  const overlay  = document.getElementById('sidebarOverlay');
  const hamburger = document.querySelector('.hamburger');
  if (!sidebar) return;

  function open()  { sidebar.classList.add('open');  overlay && overlay.classList.add('open'); document.body.style.overflow = 'hidden'; }
  function close() { sidebar.classList.remove('open'); overlay && overlay.classList.remove('open'); document.body.style.overflow = ''; }

  hamburger && hamburger.addEventListener('click', () => sidebar.classList.contains('open') ? close() : open());
  overlay   && overlay.addEventListener('click', close);

  document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });
}

/* ── Mobile nav (public pages) ──────────────────────────────── */
function initMobileNav() {
  const btn     = document.querySelector('.js-mobile-nav-open');
  const close   = document.querySelector('.js-mobile-nav-close');
  const nav     = document.getElementById('mobileNav');
  const overlay = document.getElementById('mobileNavOverlay');
  if (!btn || !nav) return;

  function open()  { nav.classList.add('open');    overlay && overlay.classList.add('open');    document.body.style.overflow = 'hidden'; }
  function closeFn(){ nav.classList.remove('open'); overlay && overlay.classList.remove('open'); document.body.style.overflow = ''; }

  btn.addEventListener('click', open);
  close && close.addEventListener('click', closeFn);
  overlay && overlay.addEventListener('click', closeFn);
  document.addEventListener('keydown', e => { if (e.key === 'Escape') closeFn(); });
}

/* ── Alert dismiss ──────────────────────────────────────────── */
function initAlerts() {
  document.querySelectorAll('.js-flash-region .alert').forEach(el => {
    // Auto-dismiss after 6s
    setTimeout(() => dismissAlert(el), 6000);
  });

  document.addEventListener('click', e => {
    if (e.target.closest('.alert-close')) {
      dismissAlert(e.target.closest('.alert'));
    }
  });
}

function dismissAlert(el) {
  if (!el) return;
  el.style.transition = 'opacity 300ms, transform 300ms';
  el.style.opacity  = '0';
  el.style.transform = 'translateY(-6px)';
  setTimeout(() => el.remove(), 320);
}

/* ── Confirm forms ──────────────────────────────────────────── */
function initConfirm() {
  document.addEventListener('click', e => {
    const btn = e.target.closest('[data-confirm]');
    if (btn) {
      if (!confirm(btn.dataset.confirm)) e.preventDefault();
    }
  });
}

/* ── Password toggle ────────────────────────────────────────── */
function togglePw(inputId, btn) {
  const el = document.getElementById(inputId);
  if (!el) return;
  const show = el.type === 'password';
  el.type = show ? 'text' : 'password';
  const icon = btn.querySelector('i');
  if (icon) icon.className = show ? 'bi bi-eye-slash' : 'bi bi-eye';
}

/* ── Password strength ──────────────────────────────────────── */
function initPasswordStrength() {
  const pw = document.getElementById('password');
  const bar = document.getElementById('strengthFill');
  if (!pw || !bar) return;

  pw.addEventListener('input', () => {
    const v = pw.value;
    let score = 0;
    if (v.length >= 8) score++;
    if (/[A-Z]/.test(v)) score++;
    if (/[a-z]/.test(v)) score++;
    if (/\d/.test(v)) score++;
    if (/[^A-Za-z0-9]/.test(v)) score++;

    const pct   = (score / 5) * 100;
    const color = score <= 2 ? '#ef4444' : score === 3 ? '#f59e0b' : score === 4 ? '#22c55e' : '#15803d';
    bar.style.width    = pct + '%';
    bar.style.background = color;
  });
}

/* ── Date constraint (booking form) ────────────────────────── */
function initDateConstraints() {
  const today = new Date().toISOString().split('T')[0];
  const start = document.getElementById('start_date');
  const end   = document.getElementById('end_date');
  if (!start || !end) return;

  start.min = today;
  end.min   = today;

  start.addEventListener('change', () => {
    end.min = start.value;
    if (end.value && end.value <= start.value) end.value = '';
    updateCalc();
  });
  end.addEventListener('change', updateCalc);
}

/* ── Booking cost calculator ────────────────────────────────── */
function updateCalc() {
  const priceEl = document.getElementById('price_per_day_data');
  const daysEl  = document.getElementById('calc-days');
  const totalEl = document.getElementById('calc-total');
  if (!priceEl || !daysEl || !totalEl) return;

  const price = parseFloat(priceEl.dataset.price);
  const s = new Date(document.getElementById('start_date').value);
  const e = new Date(document.getElementById('end_date').value);

  if (!isNaN(s) && !isNaN(e) && e > s) {
    const days  = Math.max(1, Math.round((e - s) / 86400000));
    const total = days * price;
    daysEl.textContent  = `${days} day${days > 1 ? 's' : ''}`;
    totalEl.textContent = 'KES ' + total.toLocaleString('en-KE', { maximumFractionDigits: 0 });
  } else {
    daysEl.textContent  = '—';
    totalEl.textContent = '—';
  }
}

/* ── CSRF helper ────────────────────────────────────────────── */
function getCsrf() {
  const el = document.querySelector('[name="csrf_token"]') ||
             document.querySelector('meta[name="csrf-token"]');
  return el ? (el.value || el.getAttribute('content') || '') : '';
}

/* ── Init ───────────────────────────────────────────────────── */
document.addEventListener('DOMContentLoaded', () => {
  Theme.init();
  initDropdowns();
  initSidebar();
  initMobileNav();
  initAlerts();
  initConfirm();
  initPasswordStrength();
  initDateConstraints();

  // Theme toggle clicks
  document.querySelectorAll('.js-theme-toggle').forEach(btn => {
    btn.addEventListener('click', Theme.toggle);
  });

  // Tooltips (Bootstrap if loaded)
  if (window.bootstrap?.Tooltip) {
    document.querySelectorAll('[data-bs-toggle="tooltip"]').forEach(el => {
      new bootstrap.Tooltip(el, { trigger: 'hover' });
    });
  }
});

// Expose for inline use
window.togglePw  = togglePw;
window.getCsrf   = getCsrf;
window.updateCalc = updateCalc;
