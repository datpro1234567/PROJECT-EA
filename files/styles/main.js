/**
 * main.js — X.509 CA System
 * Các tiện ích nhỏ: auto-dismiss flash, confirm dialogs, copy PEM.
 */

document.addEventListener('DOMContentLoaded', () => {

  // ── Auto-dismiss flash sau 5 giây ─────────────────────────────────────────
  document.querySelectorAll('.flash').forEach(el => {
    setTimeout(() => {
      el.style.transition = 'opacity 0.5s';
      el.style.opacity = '0';
      setTimeout(() => el.remove(), 500);
    }, 5000);
  });

  // ── Highlight row khi hover trên mobile ───────────────────────────────────
  document.querySelectorAll('.data-table tbody tr').forEach(row => {
    row.style.cursor = 'default';
  });

  // ── Tự động resize textarea code-area ─────────────────────────────────────
  document.querySelectorAll('.code-area').forEach(ta => {
    ta.style.minHeight = '120px';
  });

  // ── Xác nhận trước khi submit form nguy hiểm ──────────────────────────────
  // (Nếu button không có onclick confirm, thêm ở đây)
  document.querySelectorAll('[data-confirm]').forEach(btn => {
    btn.addEventListener('click', e => {
      if (!confirm(btn.dataset.confirm)) e.preventDefault();
    });
  });

  // ── Copy PEM to clipboard ──────────────────────────────────────────────────
  document.querySelectorAll('.code-area').forEach(ta => {
    const wrapper = ta.parentElement;
    const copyBtn = document.createElement('button');
    copyBtn.className = 'btn btn-ghost btn-xs';
    copyBtn.style.cssText = 'margin-top:0.5rem';
    copyBtn.textContent = '⎘ Sao chép PEM';
    copyBtn.type = 'button';
    copyBtn.addEventListener('click', () => {
      navigator.clipboard.writeText(ta.value || ta.textContent).then(() => {
        copyBtn.textContent = '✓ Đã sao chép!';
        setTimeout(() => copyBtn.textContent = '⎘ Sao chép PEM', 2000);
      });
    });
    wrapper.appendChild(copyBtn);
  });

  // ── Active nav link indicator (fallback) ──────────────────────────────────
  const path = window.location.pathname;
  document.querySelectorAll('.nav-links a').forEach(a => {
    if (a.getAttribute('href') === path) a.classList.add('active');
  });

});
