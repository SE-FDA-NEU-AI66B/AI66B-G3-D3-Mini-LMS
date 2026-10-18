/* ==========================================================================
   Mini-LMS — session helper
   - Fetches /api/me once per page load
   - Mirrors email into sessionStorage for api.js
   - Updates the shared topbar user chip when the logged-in role/name
     differs from the page's static defaults
   - Injects a Logout button into the topbar. If the topbar has not been
     rendered yet (Layout.init may run on a later tick in some pages),
     a MutationObserver waits for it.
   - Redirects to /login when <body data-auth="required"> and unauthenticated
   - Redirects away from /login when already authenticated
   Served from: src/ui/js/session.js
   ========================================================================== */

(function (global) {
  'use strict';

  const EMAIL_KEY = 'minilms.email';

  let currentUser = null;
  let ready = null;

  function roleHome(role) {
    if (role === 'Lecturer') return '/ui/html/instructor-quizzes.html';
    if (role === 'Student')  return '/ui/html/student-dashboard.html';
    return '/docs';            // Admin / unknown
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

  /* --------------------------- logout button ------------------------ */

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
    if (topbar.querySelector('.js-logout-btn')) return;   // idempotent
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
    // Topbar not yet in the DOM — wait for it to appear.
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

  /* ------------------------------- init ----------------------------- */

  function init() {
    if (ready) return ready;

    ready = fetchMe().then((user) => {
      currentUser = user;

      if (user && user.email) {
        try { sessionStorage.setItem(EMAIL_KEY, user.email); } catch (e) { /* ignore */ }

        // Already signed in and visiting /login → send them home.
        const path = window.location.pathname;
        if (path === '/login' || path === '/mock-sso/authorize') {
          window.location.href = roleHome(user.role);
          return user;
        }

        try {
          updateUserChip(user);
          injectLogoutButton();
        } catch (err) {
          // Never let top-bar chrome break the page.
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

  /* ------------------- late-attach safety net ----------------------- */
  // If Layout.init() ever runs after Session.init()'s .then() (e.g. an
  // inline script that defer-loads), retry injection on the next task.

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', () => {
      if (currentUser) injectLogoutButton();
    });
  } else {
    setTimeout(() => { if (currentUser) injectLogoutButton(); }, 0);
  }

  global.Session = { init, user, logout };
})(window);