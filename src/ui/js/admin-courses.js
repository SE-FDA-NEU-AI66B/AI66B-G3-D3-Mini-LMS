/* ==========================================================================
   Mini-LMS — admin courses page controller
   Lists courses; opens a roster modal with lecturer + enrolled students.
   Served from: src/ui/js/admin-courses.js
   ========================================================================== */

(function () {
  'use strict';

  const { Api, esc, fmtDateTime } = window.MiniLMS;

  const alertArea   = document.getElementById('alert-area');
  const listArea    = document.getElementById('list-area');
  const summaryEl   = document.getElementById('courses-summary');
  const refreshBtn  = document.getElementById('refresh-btn');

  const modal       = document.getElementById('roster-modal');
  const modalBackdrop = document.getElementById('modal-backdrop');
  const modalClose  = document.getElementById('modal-close');
  const rosterTitle = document.getElementById('roster-title');
  const rosterSub   = document.getElementById('roster-sub');
  const rosterBody  = document.getElementById('roster-body');

  /* ------------------------------ alerts ---------------------------- */

  function showAlert(kind, message) {
    alertArea.innerHTML =
      `<div class="alert alert--${kind}" role="alert"><div>${esc(message)}</div></div>`;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function clearAlert() { alertArea.innerHTML = ''; }

  /* ------------------------------ badges ---------------------------- */

  function statusBadge(status) {
    const klass = status === 'Active' ? 'badge--active' : 'badge--disabled';
    return `<span class="badge ${klass}"><span class="badge__dot"></span>${esc(status)}</span>`;
  }

  function roleBadge(role) {
    const klass =
      role === 'Admin'    ? 'badge--admin'    :
      role === 'Lecturer' ? 'badge--lecturer' :
                            'badge--student';
    return `<span class="badge ${klass}"><span class="badge__dot"></span>${esc(role)}</span>`;
  }

  /* --------------------------- four states -------------------------- */

  function renderLoading() {
    summaryEl.textContent = 'Loading…';
    listArea.innerHTML =
      `<div class="state">` +
        `<span class="spinner" aria-hidden="true"></span>` +
        `<div class="state__title u-mt-2">Loading courses…</div>` +
      `</div>`;
  }

  function renderError(err) {
    summaryEl.textContent = 'Could not load courses.';
    listArea.innerHTML =
      `<div class="state">` +
        `<div class="state__title">Could not load courses</div>` +
        `<div>${esc(err.message)}</div>` +
        `<div class="state__actions">` +
          `<button class="btn btn--ghost" type="button" id="retry-btn">Try again</button>` +
        `</div>` +
      `</div>`;
    const retry = document.getElementById('retry-btn');
    if (retry) retry.addEventListener('click', load);
  }

  function renderEmpty() {
    summaryEl.textContent = 'No courses yet.';
    listArea.innerHTML =
      `<div class="state">` +
        `<div class="state__title">No courses</div>` +
        `<div>Once an administrator creates courses, they will appear here.</div>` +
      `</div>`;
  }

  function renderList(data) {
    summaryEl.textContent = `Showing ${data.count} course(s).`;
    if (!data.courses || data.courses.length === 0) return renderEmpty();

    const rows = data.courses.map(c => `
      <tr>
        <td class="num">${c.course_id}</td>
        <td>${esc(c.code)}</td>
        <td>${esc(c.name)}</td>
        <td>
          ${esc(c.lecturer_name || '')}
          <div class="u-text-sm u-text-muted">${esc(c.lecturer_email || '')}</div>
        </td>
        <td class="num">${c.student_count}</td>
        <td class="u-text-right">
          <button class="btn btn--ghost btn--sm" type="button"
                  data-action="view-roster" data-cid="${c.course_id}">
            View roster
          </button>
        </td>
      </tr>`).join('');

    listArea.innerHTML =
      `<div class="table-wrap">` +
        `<table class="table">` +
          `<thead><tr>` +
            `<th class="num">ID</th><th>Code</th><th>Name</th>` +
            `<th>Lecturer</th><th class="num">Students</th>` +
            `<th style="text-align:right;">Actions</th>` +
          `</tr></thead>` +
          `<tbody>${rows}</tbody>` +
        `</table>` +
      `</div>`;
  }

  /* ------------------------------ load ------------------------------ */

  async function load() {
    clearAlert();
    renderLoading();
    try {
      const data = await Api.get('/api/admin/courses');
      renderList(data);
    } catch (err) {
      renderError(err);
    }
  }

  /* ------------------------------ modal ----------------------------- */

  function openModal() {
    modal.style.display = 'flex';
    modalBackdrop.classList.add('is-open');
  }

  function closeModal() {
    modal.style.display = 'none';
    modalBackdrop.classList.remove('is-open');
  }

  function renderRosterError(err) {
    rosterBody.innerHTML =
      `<div class="state">` +
        `<div class="state__title">Could not load roster</div>` +
        `<div>${esc(err.message)}</div>` +
      `</div>`;
  }

  function renderRoster(data) {
    rosterTitle.textContent = `${data.code} — ${data.name}`;
    rosterSub.textContent   = `Course #${data.course_id}`;

    let lecturerHTML;
    if (data.lecturer) {
      lecturerHTML = `
        <div class="card" style="box-shadow:none; margin-bottom:12px;">
          <div class="card__body">
            <div class="u-flex u-justify-between u-items-center">
              <div>
                <div><strong>${esc(data.lecturer.full_name)}</strong> ${roleBadge('Lecturer')}</div>
                <div class="u-text-sm u-text-muted">${esc(data.lecturer.email)}</div>
              </div>
              ${statusBadge(data.lecturer.status)}
            </div>
          </div>
        </div>`;
    } else {
      lecturerHTML = `<p class="u-text-muted">No lecturer assigned.</p>`;
    }

    const studentRows = data.students.length === 0
      ? `<div class="state">No students enrolled.</div>`
      : `<div class="table-wrap">
          <table class="table">
            <thead><tr>
              <th class="num">ID</th><th>Email</th><th>Name</th>
              <th>Role</th><th>Enrollment</th><th>Enrolled</th>
            </tr></thead>
            <tbody>
              ${data.students.map(s => `
                <tr>
                  <td class="num">${s.user_id}</td>
                  <td>${esc(s.email)}</td>
                  <td>${esc(s.full_name)}</td>
                  <td>${roleBadge(s.role || 'Student')}</td>
                  <td>${statusBadge(s.status)}</td>
                  <td class="num">${esc(fmtDateTime(s.enrolled_at))}</td>
                </tr>`).join('')}
            </tbody>
          </table>
        </div>`;

    rosterBody.innerHTML =
      `<div class="u-text-sm u-text-muted" style="text-transform:uppercase;
                                                  letter-spacing:.06em;">
         Lecturer
       </div>
       ${lecturerHTML}

       <div class="u-text-sm u-text-muted u-mt-4" style="text-transform:uppercase;
                                                        letter-spacing:.06em;">
         Enrolled users (${data.students.length})
       </div>
       ${studentRows}`;
  }

  async function openRoster(courseId) {
    rosterTitle.textContent = 'Course roster';
    rosterSub.textContent   = `Course #${courseId}`;
    rosterBody.innerHTML =
      `<div class="state">` +
        `<span class="spinner" aria-hidden="true"></span>` +
        `<div class="state__title u-mt-2">Loading roster…</div>` +
      `</div>`;
    openModal();
    try {
      const data = await Api.get(`/api/admin/courses/${courseId}/roster`);
      renderRoster(data);
    } catch (err) {
      renderRosterError(err);
    }
  }

  /* ----------------------------- handlers --------------------------- */

  refreshBtn.addEventListener('click', load);
  modalClose.addEventListener('click', closeModal);
  modalBackdrop.addEventListener('click', closeModal);

  document.addEventListener('click', (event) => {
    const btn = event.target.closest('button[data-action="view-roster"]');
    if (btn) openRoster(Number(btn.dataset.cid));
  });

  /* ------------------------------ boot ------------------------------ */

  load();
})();