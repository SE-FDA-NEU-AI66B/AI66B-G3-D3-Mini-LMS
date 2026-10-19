/* ==========================================================================
   Mini-LMS — admin courses page controller
   Lists courses; opens a roster modal with lecturer + enrolled students.
   FULL CRUD for student enrollments + client-side BR enforcement.
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
  const rosterAlert = document.getElementById('roster-alert');

  const addBtn      = document.getElementById('add-student-btn');
  const addModal    = document.getElementById('add-student-modal');
  const addClose    = document.getElementById('add-student-close');
  const addCancel   = document.getElementById('add-student-cancel');
  const addForm     = document.getElementById('add-student-form');
  const addEmail    = document.getElementById('student-email');
  const addError    = document.getElementById('add-student-error');
  const addSaveBtn  = document.getElementById('add-student-save');

  let currentCourseId = null;
  let currentRoster   = null;  // lưu roster hiện tại để enforce BR phía client

  /* ------------------------------ alerts ---------------------------- */

  function showAlert(kind, message) {
    alertArea.innerHTML =
      `<div class="alert alert--${kind}" role="alert"><div>${esc(message)}</div></div>`;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function clearAlert() { alertArea.innerHTML = ''; }

  function showRosterAlert(kind, message) {
    rosterAlert.innerHTML =
      `<div class="alert alert--${kind}" role="alert"><div>${esc(message)}</div></div>`;
  }

  function clearRosterAlert() { rosterAlert.innerHTML = ''; }

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
    clearRosterAlert();
    currentCourseId = null;
    currentRoster = null;
  }

  function renderRosterError(err) {
    rosterBody.innerHTML =
      `<div class="state">` +
        `<div class="state__title">Could not load roster</div>` +
        `<div>${esc(err.message)}</div>` +
      `</div>`;
  }

  function renderRoster(data) {
    currentRoster = data;
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

    const activeStudents = data.students.filter(s => s.status === 'Active');

    const studentRows = activeStudents.length === 0
      ? `<div class="state">No students enrolled.</div>`
      : `<div class="table-wrap">
          <table class="table">
            <thead><tr>
              <th class="num">ID</th><th>Email</th><th>Name</th>
              <th>Role</th><th>Enrollment</th><th>Enrolled</th>
              <th style="text-align:right;">Actions</th>
            </tr></thead>
            <tbody>
              ${activeStudents.map(s => {
                // Chỉ cần nút Remove, không cần Restore
                const actionBtns = `
                  <button class="btn btn--danger btn--sm" type="button"
                          data-action="remove-student"
                          data-uid="${s.user_id}"
                          data-email="${esc(s.email)}">
                    Remove
                  </button>`;

                return `
                <tr>
                  <td class="num">${s.user_id}</td>
                  <td>${esc(s.email)}</td>
                  <td>${esc(s.full_name)}</td>
                  <td>${roleBadge(s.role || 'Student')}</td>
                  <td>${statusBadge(s.status)}</td>
                  <td class="num">${esc(fmtDateTime(s.enrolled_at))}</td>
                  <td class="u-text-right">${actionBtns}</td>
                </tr>`;
              }).join('')}
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
         ${activeStudents.length}
       </div>
       ${studentRows}`;
  }

  async function openRoster(courseId) {
    currentCourseId = courseId;
    clearRosterAlert();
    rosterTitle.textContent = 'Course roster';
    rosterSub.textContent   = `Course #${courseId}`;
    rosterBody.innerHTML =
      `<div class="state">` +
        `<span class="spinner" aria-hidden="true"></span>` +
        `<div class="state__title u-mt-2">Loading roster…</div>` +
      `</div>`;
    openModal();
    await reloadRoster();
  }

  async function reloadRoster() {
    if (!currentCourseId) return;
    clearRosterAlert();
    try {
      const data = await Api.get(`/api/admin/courses/${currentCourseId}/roster`);
      renderRoster(data);
    } catch (err) {
      renderRosterError(err);
    }
  }

  /* -------------------- Add Student Modal Handlers ------------------ */

  function openAddModal() {
    if (document.body.dataset.role !== 'admin') return;
    addEmail.value = '';
    addError.hidden = true;
    addError.textContent = '';
    addModal.style.display = 'flex';
    setTimeout(() => addEmail.focus(), 0);
  }

  function closeAddModal() {
    addModal.style.display = 'none';
  }

  addBtn.addEventListener('click', openAddModal);
  addClose.addEventListener('click', closeAddModal);
  addCancel.addEventListener('click', closeAddModal);

  // ============================================================
  // ENFORCE BRs Ở FRONTEND (trước khi gọi API):
  //   1. Email phải hợp lệ.
  //   2. Không được trùng với sinh viên đã có enrollment Active.
  //   3. Không được thêm user có role khác Student (nếu biết).
  //   4. Không thể add chính mình nếu đang là Admin (defensive).
  // ============================================================
  addForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    addError.hidden = true;
    const email = addEmail.value.trim().toLowerCase();

    // BR-validate #1: format
    if (!email || !email.includes('@')) {
      addError.hidden = false;
      addError.textContent = 'A valid email is required.';
      return;
    }

    // BR-validate #2: trùng với enrollment Active hiện có
    if (currentRoster && currentRoster.students) {
      const dup = currentRoster.students.find(
        s => s.email.toLowerCase() === email && s.status === 'Active'
      );
      if (dup) {
        addError.hidden = false;
        addError.textContent = `Student "${email}" is already enrolled in this course.`;
        return;
      }
    }

    // BR-validate #3: chặn nếu email là của Admin (không thể enroll Admin như Student)
    //   → cần tra cứu nhanh account. Nếu backend chưa có endpoint tìm, bỏ qua check này.
    try {
      const lookup = await Api.get(`/api/admin/accounts?q=${encodeURIComponent(email)}`);
      const match = lookup.users.find(u => u.email.toLowerCase() === email);
      if (match && match.role !== 'Student') {
        addError.hidden = false;
        addError.textContent =
          `"${email}" is a ${match.role}, not a Student. Only Student accounts can be enrolled.`;
        return;
      }
      if (match && match.status === 'Disabled') {
        addError.hidden = false;
        addError.textContent = `"${email}" is disabled. Enable the account first.`;
        return;
      }
    } catch (_e) {
      // nếu endpoint lookup lỗi, không block — backend vẫn sẽ enforce
    }

    addSaveBtn.disabled = true;
    try {
      await Api.post(`/api/admin/courses/${currentCourseId}/enrollments`, {
        student_email: email
      });

      closeAddModal();
      showRosterAlert('success', `Student "${email}" enrolled in this course. Student count updated.`);
      await reloadRoster();
      await load();
    } catch (err) {
      addError.hidden = false;
      addError.textContent = err.message;
    } finally {
      addSaveBtn.disabled = false;
    }
  });

  /* ----------------------------- handlers --------------------------- */

  refreshBtn.addEventListener('click', load);
  modalClose.addEventListener('click', closeModal);
  modalBackdrop.addEventListener('click', closeModal);

  document.addEventListener('click', async (event) => {
    const rosterBtn = event.target.closest('button[data-action="view-roster"]');
    if (rosterBtn) {
      openRoster(Number(rosterBtn.dataset.cid));
      return;
    }

    // ============================================================
    // DELETE: Remove (soft) — set status='Removed'
    // ============================================================
    const removeBtn = event.target.closest('button[data-action="remove-student"]');
    if (removeBtn) {
      const uid = removeBtn.dataset.uid;
      const email = removeBtn.dataset.email;

      if (!window.confirm(
        `Remove "${email}" from this course?\n\n` +
        `Their enrollment will be marked Removed. Past quiz attempts remain intact.`
      )) return;

      removeBtn.disabled = true;
      try {
        await Api.del(`/api/admin/courses/${currentCourseId}/enrollments/${uid}`);
        showRosterAlert('success', `Student "${email}" removed from this course. Student count updated.`);
        await reloadRoster();
        await load();
      } catch (err) {
        showRosterAlert('danger', err.message);
        removeBtn.disabled = false;
      }
      return;
    }
  });

  /* ------------------------------ boot ------------------------------ */

  load();
})();