/* ==========================================================================
   Mini-LMS — session helper
   - Fetches /api/me once per page load
   - Mirrors email into sessionStorage for api.js
   - Updates the shared topbar user chip
   - Injects a Logout button if the topbar doesn't already have one
   - Redirects to /login when <body data-auth="required"> and unauthenticated
   - Redirects away from /login when already authenticated
   - NEW: role gate — a page with data-role="student|lecturer|admin"
     only accepts callers whose role matches. Mismatched role (e.g. an
     admin opening a student page) is redirected to their own home.
   Served from: src/ui/js/session.js
   ========================================================================== */

(function (global) {
  'use strict';

  const EMAIL_KEY = 'minilms.email';

  // Maps data-role="…" on <body> to the exact role string returned by
  // the /api/me endpoint. `guest` intentionally has no mapping — public
  // pages (login, mock-sso) accept any authenticated role.
  const PAGE_ROLE_TO_USER_ROLE = {
    student:  'Student',
    lecturer: 'Lecturer',
    admin:    'Admin',
  };

  let currentUser = null;
  let ready = null;

  function roleHome(role) {
    if (role === 'Lecturer') return '/ui/html/instructor-quizzes.html';
    if (role === 'Student')  return '/ui/html/student-dashboard.html';
    if (role === 'Admin')    return '/ui/html/admin-accounts.html';
    return '/login';
  }

  function fetchMe() {
    return fetch('/api/me', { headers: { Accept: 'application/json' } })
      .then((res) => (res.ok ? res.json() : null))
      .catch(() => null);
  }

  function initials(name) {
    if (!name) return '?';
    const parts = String(name).trim().split(/\s+/);
    if (parts.length === 1) return parts[0][0].toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }

  function updateUserChip(user) {
    const chip = document.querySelector('.topbar .user-chip');
    if (!chip) return;

    const nameEl   = chip.querySelector('.user-chip__name');
    const roleEl   = chip.querySelector('.user-chip__role');
    const avatarEl = chip.querySelector('.user-chip__avatar');

    if (nameEl)   nameEl.textContent   = user.full_name || user.email;
    if (roleEl)   roleEl.textContent   = user.role;
    if (avatarEl) avatarEl.textContent = initials(user.full_name || user.email);

    chip.setAttribute('title', user.email);
    if (user.role) chip.setAttribute('data-role', String(user.role).toLowerCase());
  }

  function buildLogoutButton() {
    const btn = document.createElement('a');
    btn.className = 'btn btn--ghost btn--sm js-logout-btn';
    btn.href = '#';
    btn.textContent = 'Logout';
    btn.addEventListener('click', (event) => {
      event.preventDefault();
      logout();
    });
    return btn;
  }

  function insertIntoTopbar(topbar) {
    if (topbar.querySelector('.js-logout-btn')) return;
    const btn = buildLogoutButton();
    const chip = topbar.querySelector('.user-chip');
    if (chip && chip.parentNode) {
      chip.parentNode.insertBefore(btn, chip.nextSibling);
    } else {
      topbar.appendChild(btn);
    }
  }

  function injectLogoutButton() {
    const topbar = document.querySelector('.topbar');
    if (topbar) {
      insertIntoTopbar(topbar);
      return;
    }
    const observer = new MutationObserver((_mutations, obs) => {
      const tb = document.querySelector('.topbar');
      if (!tb) return;
      obs.disconnect();
      insertIntoTopbar(tb);
    });
    observer.observe(document.body, { childList: true, subtree: true });
  }

  function removeLogoutButton() {
    const btn = document.querySelector('.topbar .js-logout-btn');
    if (btn) btn.remove();
  }

  /* ---------------- page-role gate (Fix B) ------------------------- */

  function pageRequiresWrongRole(user) {
    const pageRole = document.body.dataset.role;
    const expected = PAGE_ROLE_TO_USER_ROLE[pageRole];
    if (!expected) return false;                 // guest page → any role OK
    if (!user.role) return true;                 // no role → treat as mismatch
    return user.role !== expected;
  }

  function init() {
    if (ready) return ready;

    ready = fetchMe().then((user) => {
      currentUser = user;

      if (user && user.email) {
        try { sessionStorage.setItem(EMAIL_KEY, user.email); } catch (e) { /* ignore */ }

        const path = window.location.pathname;

        // Already signed in and visiting /login or /mock-sso → home.
        if (path === '/login' || path === '/mock-sso/authorize') {
          window.location.href = roleHome(user.role);
          return user;
        }

        // Role gate: e.g. an Admin opening a student page.
        if (pageRequiresWrongRole(user)) {
          window.location.href = roleHome(user.role);
          return user;
        }

        try {
          updateUserChip(user);
          injectLogoutButton();
        } catch (err) {
          console.error('Session: failed to update top bar', err);
        }
      } else {
        removeLogoutButton();

        const required = document.body.dataset.auth === 'required';
        const path = window.location.pathname;
        const isAuthPage =
          path === '/login' ||
          path === '/mock-sso/authorize' ||
          path === '/auth/callback';

        if (required && !isAuthPage) {
          window.location.href = '/login';
        }
      }

      return user;
    });

    return ready;
  }

  function user() { return currentUser; }

  async function logout() {
    try { await fetch('/api/auth/logout', { method: 'POST' }); } catch (e) { /* ignore */ }
    try { sessionStorage.removeItem(EMAIL_KEY); } catch (e) { /* ignore */ }
    currentUser = null;
    removeLogoutButton();
    window.location.href = '/login';
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      if (currentUser) injectLogoutButton();
    });
  } else {
    setTimeout(() => { if (currentUser) injectLogoutButton(); }, 0);
  }

  global.Session = { init, user, logout };
})(window);