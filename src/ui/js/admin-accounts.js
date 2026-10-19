/* ==========================================================================
   Mini-LMS — admin accounts page controller (US06)
   List / create / update / delete user accounts.

   Password behaviour (reverted to "no display"):
   - Create: password is required, hashed server-side.
   - Edit:   password field is empty by default. Leave blank to keep
             the current password. Type a new one to replace it.
   Served from: src/ui/js/admin-accounts.js
   ========================================================================== */

(function () {
  'use strict';

  const { Api, esc, fmtDateTime } = window.MiniLMS;

  const alertArea    = document.getElementById('alert-area');
  const listArea     = document.getElementById('list-area');
  const summaryEl    = document.getElementById('accounts-summary');
  const refreshBtn   = document.getElementById('refresh-btn');
  const newAcctBtn   = document.getElementById('new-account-btn');
  const applyBtn     = document.getElementById('apply-filters');
  const clearBtn     = document.getElementById('clear-filters');

  const filterRole   = document.getElementById('filter-role');
  const filterStatus = document.getElementById('filter-status');
  const filterId     = document.getElementById('filter-id');
  const filterQ      = document.getElementById('filter-q');

  const modal        = document.getElementById('account-modal');
  const modalBackdrop = document.getElementById('modal-backdrop');
  const modalTitle   = document.getElementById('modal-title');
  const modalClose   = document.getElementById('modal-close');
  const modalCancel  = document.getElementById('modal-cancel');
  const form         = document.getElementById('account-form');
  const fEmail       = document.getElementById('acct-email');
  const fFullName    = document.getElementById('acct-fullname');
  const fPassword    = document.getElementById('acct-password');
  const fPwToggle    = document.getElementById('acct-password-toggle');
  const fPwReq       = document.getElementById('acct-password-req');
  const fPwHelp      = document.getElementById('acct-password-help');
  const fRole        = document.getElementById('acct-role');
  const fStatus      = document.getElementById('acct-status');
  const errorBox     = document.getElementById('account-error');
  const saveBtn      = document.getElementById('account-save-btn');

  let editingUserId = null;   // null = create mode

  /* ------------------------------ alerts ---------------------------- */

  function showAlert(kind, message) {
    alertArea.innerHTML =
      `<div class="alert alert--${kind}" role="alert"><div>${esc(message)}</div></div>`;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function clearAlert() { alertArea.innerHTML = ''; }

  /* ------------------------------ badges ---------------------------- */

  function roleBadge(role) {
    const klass =
      role === 'Admin'    ? 'badge--admin'    :
      role === 'Lecturer' ? 'badge--lecturer' :
                            'badge--student';
    return `<span class="badge ${klass}"><span class="badge__dot"></span>${esc(role)}</span>`;
  }

  function statusBadge(status) {
    const klass = status === 'Active' ? 'badge--active' : 'badge--disabled';
    return `<span class="badge ${klass}"><span class="badge__dot"></span>${esc(status)}</span>`;
  }

  /* --------------------------- four states -------------------------- */

  function renderLoading() {
    summaryEl.textContent = 'Loading…';
    listArea.innerHTML =
      `<div class="state">` +
        `<span class="spinner" aria-hidden="true"></span>` +
        `<div class="state__title u-mt-2">Loading accounts…</div>` +
      `</div>`;
  }

  function renderError(err) {
    summaryEl.textContent = 'Could not load accounts.';
    listArea.innerHTML =
      `<div class="state">` +
        `<div class="state__title">Could not load accounts</div>` +
        `<div>${esc(err.message)}</div>` +
        `<div class="state__actions">` +
          `<button class="btn btn--ghost" type="button" id="retry-btn">Try again</button>` +
        `</div>` +
      `</div>`;
    const retry = document.getElementById('retry-btn');
    if (retry) retry.addEventListener('click', load);
  }

  function renderEmpty() {
    summaryEl.textContent = 'No accounts match the current filters.';
    listArea.innerHTML =
      `<div class="state">` +
        `<div class="state__title">No accounts</div>` +
        `<div>Try relaxing the filters, or create a new account.</div>` +
      `</div>`;
  }

  function renderList(data) {
    summaryEl.textContent = `Showing ${data.count} account(s).`;

    if (!data.users || data.users.length === 0) return renderEmpty();

    const rows = data.users.map(u => `
      <tr>
        <td class="num">${u.user_id}</td>
        <td>${esc(u.email)}</td>
        <td>${esc(u.full_name)}</td>
        <td>${roleBadge(u.role)}</td>
        <td>${statusBadge(u.status)}</td>
        <td class="num">${esc(fmtDateTime(u.created_at))}</td>
        <td class="u-text-right">
          <div class="u-flex u-gap-2" style="justify-content:flex-end;">
            <button class="btn btn--ghost btn--sm" type="button"
                    data-action="edit" data-uid="${u.user_id}">Edit</button>
            <button class="btn btn--danger btn--sm" type="button"
                    data-action="delete" data-uid="${u.user_id}"
                    data-email="${esc(u.email)}">Delete</button>
          </div>
        </td>
      </tr>`).join('');

    listArea.innerHTML =
      `<div class="table-wrap">` +
        `<table class="table">` +
          `<thead><tr>` +
            `<th class="num">ID</th><th>Email</th><th>Full name</th>` +
            `<th>Role</th><th>Status</th><th>Created</th>` +
            `<th style="text-align:right;">Actions</th>` +
          `</tr></thead>` +
          `<tbody>${rows}</tbody>` +
        `</table>` +
      `</div>`;
  }

  /* ------------------------------ query ----------------------------- */

  function buildQuery() {
    const params = new URLSearchParams();
    if (filterRole.value)   params.set('role', filterRole.value);
    if (filterStatus.value) params.set('status', filterStatus.value);
    if (filterId.value)     params.set('user_id', filterId.value);
    if (filterQ.value.trim()) params.set('q', filterQ.value.trim());
    const qs = params.toString();
    return qs ? `?${qs}` : '';
  }

  async function load() {
    clearAlert();
    renderLoading();
    try {
      const data = await Api.get('/api/admin/accounts' + buildQuery());
      renderList(data);
    } catch (err) {
      renderError(err);
    }
  }

  /* ------------------------------ modal ----------------------------- */

  function resetPasswordVisibility() {
    fPassword.type = 'password';
    fPwToggle.textContent = 'Show';
    fPwToggle.setAttribute('aria-label', 'Show password');
  }

  function openModal(user) {
    editingUserId = user ? user.user_id : null;
    clearError();
    resetPasswordVisibility();
    fPassword.value = '';

    if (user) {
      modalTitle.textContent = `Edit account #${user.user_id}`;
      fEmail.value    = user.email;
      fFullName.value = user.full_name;
      fRole.value     = user.role;
      fStatus.value   = user.status;
      fPwReq.setAttribute('hidden', '');
      fPwHelp.textContent =
        'Leave blank to keep the current password. ' +
        'Type a new password to replace it (hashed with SHA-256).';
    } else {
      modalTitle.textContent = 'New account';
      fEmail.value    = '';
      fFullName.value = '';
      fRole.value     = 'Student';
      fStatus.value   = 'Active';
      fPwReq.removeAttribute('hidden');
      fPwHelp.textContent = 'Initial password. Hashed with SHA-256 before storage.';
    }

    modal.style.display = 'flex';
    modalBackdrop.classList.add('is-open');
    setTimeout(() => fEmail.focus(), 0);
  }

  function closeModal() {
    modal.style.display = 'none';
    modalBackdrop.classList.remove('is-open');
    editingUserId = null;
    fPassword.value = '';
    resetPasswordVisibility();
  }

  function showError(msg) {
    errorBox.hidden = false;
    errorBox.textContent = msg;
  }

  function clearError() {
    errorBox.hidden = true;
    errorBox.textContent = '';
  }

  fPwToggle.addEventListener('click', () => {
    const show = fPassword.type === 'password';
    fPassword.type = show ? 'text' : 'password';
    fPwToggle.textContent = show ? 'Hide' : 'Show';
    fPwToggle.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
  });

  /* ----------------------------- handlers --------------------------- */

  newAcctBtn.addEventListener('click', () => openModal(null));
  modalClose.addEventListener('click', closeModal);
  modalCancel.addEventListener('click', closeModal);
  modalBackdrop.addEventListener('click', closeModal);

  applyBtn.addEventListener('click', load);
  clearBtn.addEventListener('click', () => {
    filterRole.value = '';
    filterStatus.value = '';
    filterId.value = '';
    filterQ.value = '';
    load();
  });
  refreshBtn.addEventListener('click', load);

  [filterRole, filterStatus].forEach(el => el.addEventListener('change', load));

  document.addEventListener('click', async (event) => {
    const editBtn = event.target.closest('button[data-action="edit"]');
    if (editBtn) {
      const uid = Number(editBtn.dataset.uid);
      try {
        const user = await Api.get(`/api/admin/accounts/${uid}`);
        openModal(user);
      } catch (err) {
        showAlert('danger', err.message);
      }
      return;
    }

    const delBtn = event.target.closest('button[data-action="delete"]');
    if (delBtn) {
      const uid   = Number(delBtn.dataset.uid);
      const email = delBtn.dataset.email || `#${uid}`;
      if (!window.confirm(
        `Delete account "${email}"?\n\n` +
        `This cannot be undone. If the user still owns data ` +
        `(courses, quizzes, attempts, enrollments) the delete is blocked — ` +
        `disable the account instead.`
      )) return;

      delBtn.disabled = true;
      try {
        await Api.del(`/api/admin/accounts/${uid}`);
        showAlert('success', `Account "${email}" deleted.`);
        await load();
      } catch (err) {
        showAlert('danger', err.message);
        delBtn.disabled = false;
      }
    }
  });

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    clearError();

    const email    = fEmail.value.trim();
    const fullName = fFullName.value.trim();
    const password = fPassword.value;   // may be empty in edit mode = "keep current"
    const role     = fRole.value;
    const status   = fStatus.value;

    if (!email || !email.includes('@')) {
      return showError('A valid email is required.');
    }
    if (!fullName) {
      return showError('Full name is required.');
    }
    if (!editingUserId && !password) {
      return showError('Initial password is required when creating an account.');
    }

    const payload = {
      email,
      full_name: fullName,
      role,
      status,
    };
    if (password) payload.password = password;

    saveBtn.disabled = true;
    try {
      if (editingUserId) {
        await Api.patch(`/api/admin/accounts/${editingUserId}`, payload);
        showAlert('success', `Account "${email}" updated.`);
      } else {
        await Api.post('/api/admin/accounts', payload);
        showAlert('success', `Account "${email}" created.`);
      }
      closeModal();
      await load();
    } catch (err) {
      showError(err.message);
    } finally {
      saveBtn.disabled = false;
    }
  });

  /* ------------------------------ boot ------------------------------ */

  load();
})();