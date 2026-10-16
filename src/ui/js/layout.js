/* ==========================================================================
   Mini-LMS — shared layout renderer
   FROZEN — do not edit without explicit team approval.
   Vanilla ES2018+, no build step, no dependencies.
   Served from: src/ui/js/layout.js
   ========================================================================== */

(function (global) {
  'use strict';

  /* ---------------------------------------------------------------- */
  /* Role and navigation definitions                                   */
  /* ---------------------------------------------------------------- */

  const ROLES = {
    guest:    'guest',
    student:  'student',
    lecturer: 'lecturer',
    admin:    'admin',
  };

  const ROLE_LABEL = {
    guest:    'Guest',
    student:  'Student',
    lecturer: 'Lecturer',
    admin:    'Administrator',
  };

  const NAV = {
    guest: [],
    student: [
      { id: 'dashboard', label: 'Dashboard',  href: '/dashboard',
        icon: '<path d="M4 6h16M4 12h16M4 18h10"/>' },
      { id: 'results',   label: 'My results', href: '/results',
        icon: '<path d="M4 19V5M4 19h16M8 15l3-4 3 2 4-6"/>' },
    ],
    lecturer: [
      { id: 'quizzes', label: 'My quizzes', href: '/instructor/quizzes',
        icon: '<path d="M4 4h16v12H4zM8 20h8M12 16v4"/>' },
    ],
    admin: [
      { id: 'courses',  label: 'Courses',  href: '/admin/courses',
        icon: '<path d="M4 6h16M4 12h16M4 18h10"/>' },
      { id: 'accounts', label: 'Accounts', href: '/admin/accounts',
        icon: '<circle cx="12" cy="8" r="3.5"/><path d="M4.5 20c0-3.6 3.4-6.5 7.5-6.5s7.5 2.9 7.5 6.5"/>' },
    ],
  };

  /* ---------------------------------------------------------------- */
  /* Helpers                                                            */
  /* ---------------------------------------------------------------- */

  function el(tag, attrs, html) {
    const node = document.createElement(tag);
    if (attrs) {
      for (const k in attrs) {
        if (k === 'class') node.className = attrs[k];
        else if (k.startsWith('data-')) node.setAttribute(k, attrs[k]);
        else node.setAttribute(k, attrs[k]);
      }
    }
    if (html != null) node.innerHTML = html;
    return node;
  }

  function initials(name) {
    if (!name) return '?';
    const parts = name.trim().split(/\s+/);
    if (parts.length === 1) return parts[0][0].toUpperCase();
    return (parts[0][0] + parts[parts.length - 1][0]).toUpperCase();
  }

  function escapeHtml(text) {
    return String(text)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  /* ---------------------------------------------------------------- */
  /* Renderers                                                          */
  /* ---------------------------------------------------------------- */

  function renderTopBar(cfg) {
    const role = cfg.role || ROLES.guest;
    const sub  = cfg.brandSub ? `<span class="topbar__sub">/ ${escapeHtml(cfg.brandSub)}</span>` : '';

    const rolePill = role === ROLES.guest ? '' :
      `<span class="topbar__role">${escapeHtml(ROLE_LABEL[role])}</span>`;

    const userChip = role === ROLES.guest ? '' : `
      <div class="user-chip" data-role="${role}" title="${escapeHtml(cfg.userEmail || '')}">
        <div class="user-chip__avatar">${escapeHtml(initials(cfg.userName))}</div>
        <div class="user-chip__meta">
          <span class="user-chip__name">${escapeHtml(cfg.userName || '')}</span>
          <span class="user-chip__role">${escapeHtml(ROLE_LABEL[role])}</span>
        </div>
      </div>`;

    return `
      <header class="topbar" role="banner">
        <button class="topbar__menu-btn" type="button"
                aria-label="Toggle navigation"
                data-action="toggle-sidebar">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="2">
            <path d="M4 6h16M4 12h16M4 18h16"/>
          </svg>
        </button>

        <a class="topbar__brand" href="/">
          <span class="topbar__mark">L</span>
          ${escapeHtml(cfg.brandName || 'Mini-LMS')}
          ${sub}
        </a>

        <div class="topbar__spacer"></div>
        ${rolePill}
        ${userChip}
      </header>
    `;
  }

  function renderSidebar(cfg) {
    const role = cfg.role || ROLES.guest;
    const items = NAV[role] || [];
    if (items.length === 0) return '';

    const groupTitle = cfg.sidebarTitle ||
      (role === ROLES.admin ? 'Administration' :
       role === ROLES.lecturer ? 'Teaching' :
       role === ROLES.student ? 'Learning' : '');

    const links = items.map(item => {
      const active = cfg.active === item.id ? ' is-active' : '';
      const current = cfg.active === item.id ? ' aria-current="page"' : '';
      return `
        <a class="sidebar__item${active}" href="${item.href}"${current}>
          <svg class="sidebar__icon" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="2" aria-hidden="true">
            ${item.icon}
          </svg>
          ${escapeHtml(item.label)}
        </a>`;
    }).join('');

    return `
      <aside class="sidebar" id="app-sidebar" aria-label="Primary navigation">
        ${groupTitle ? `<div class="sidebar__group">${escapeHtml(groupTitle)}</div>` : ''}
        ${links}
      </aside>
      <div class="sidebar-backdrop" data-action="close-sidebar"></div>
    `;
  }

  function renderFooter(cfg) {
    return `
      <footer class="footer" role="contentinfo">
        <div class="footer__inner">
          <div>© ${new Date().getFullYear()} Mini-LMS · NEU · FDA</div>
          <div>
            <a href="/docs">API docs</a> ·
            <a href="/health">Health</a> ·
            <a href="/about">About</a>
          </div>
        </div>
      </footer>`;
  }

  /* ---------------------------------------------------------------- */
  /* Wiring                                                            */
  /* ---------------------------------------------------------------- */

  function wireInteractions(root) {
    root.addEventListener('click', (event) => {
      const action = event.target.closest('[data-action]');
      if (!action) return;
      const name = action.dataset.action;

      if (name === 'toggle-sidebar') {
        const sb = document.getElementById('app-sidebar');
        const bd = root.querySelector('.sidebar-backdrop');
        if (sb) sb.classList.toggle('is-open');
        if (bd) bd.classList.toggle('is-open');
      }
      if (name === 'close-sidebar') {
        const sb = document.getElementById('app-sidebar');
        const bd = root.querySelector('.sidebar-backdrop');
        if (sb) sb.classList.remove('is-open');
        if (bd) bd.classList.remove('is-open');
      }
    });

    window.addEventListener('resize', () => {
      if (window.innerWidth > 900) {
        const sb = document.getElementById('app-sidebar');
        const bd = root.querySelector('.sidebar-backdrop');
        if (sb) sb.classList.remove('is-open');
        if (bd) bd.classList.remove('is-open');
      }
    });
  }

  /* ---------------------------------------------------------------- */
  /* Public API                                                        */
  /* ---------------------------------------------------------------- */

  function init(cfg) {
    cfg = Object.assign({
      role:         document.body.dataset.role || ROLES.guest,
      userName:     document.body.dataset.userName || '',
      userEmail:    document.body.dataset.userEmail || '',
      active:       document.body.dataset.active || '',
      brandName:    'Mini-LMS',
      brandSub:     document.body.dataset.brandSub || '',
      sidebarTitle: document.body.dataset.sidebarTitle || '',
    }, cfg || {});

    const mount = cfg.mount || document.body;

    // --- Top bar ---------------------------------------------------
    const topbarHTML = renderTopBar(cfg);
    const existingTopbar = mount.querySelector('.topbar');
    if (existingTopbar) existingTopbar.outerHTML = topbarHTML;
    else mount.insertAdjacentHTML('afterbegin', topbarHTML);

    // --- Sidebar ---------------------------------------------------
    const shell = mount.querySelector('.app-body');
    if (shell) {
      const sidebarHTML = renderSidebar(cfg);
      const existingSidebar = shell.querySelector('.sidebar');
      if (existingSidebar) {
        existingSidebar.outerHTML = sidebarHTML;
      } else {
        shell.insertAdjacentHTML('afterbegin', sidebarHTML);
      }
    }

    // --- Footer ----------------------------------------------------
    const existingFooter = mount.querySelector('.footer');
    if (!existingFooter) {
      mount.insertAdjacentHTML('beforeend', renderFooter(cfg));
    }

    // --- Interactions ---------------------------------------------
    wireInteractions(mount);

    return { role: cfg.role, active: cfg.active };
  }

  global.Layout = {
    ROLES,
    ROLE_LABEL,
    NAV,
    init,
    el,
    escapeHtml,
    initials,
  };
})(window);