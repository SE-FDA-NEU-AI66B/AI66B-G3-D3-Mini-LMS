/* ==========================================================================
   Mini-LMS — admin courses page controller
   ========================================================================== */

(function () {
  'use strict';

  const { Api, esc, fmtDateTime } = window.MiniLMS;

  // DOM Elements
  const alertArea   = document.getElementById('alert-area');
  const listArea    = document.getElementById('list-area');
  const summaryEl   = document.getElementById('courses-summary');
  const refreshBtn  = document.getElementById('refresh-btn');
  const newCourseBtn = document.getElementById('new-course-btn');

  // Course Modal
  const courseModal = document.getElementById('course-modal');
  const courseForm  = document.getElementById('course-form');
  const courseModalTitle = document.getElementById('course-modal-title');
  const courseModalClose = document.getElementById('course-modal-close');
  const courseModalCancel = document.getElementById('course-modal-cancel');
  const inputCode   = document.getElementById('course-code');
  const inputName   = document.getElementById('course-name');
  const selectLec   = document.getElementById('course-lecturer');
  const courseError = document.getElementById('course-error');
  const courseSaveBtn = document.getElementById('course-save-btn');

  // Roster Modal
  const rosterModal = document.getElementById('roster-modal');
  const modalBackdrop = document.getElementById('modal-backdrop');
  const modalClose  = document.getElementById('modal-close');
  const rosterTitle = document.getElementById('roster-title');
  const rosterSub   = document.getElementById('roster-sub');
  const rosterBody  = document.getElementById('roster-body');
  const rosterAlert = document.getElementById('roster-alert');

  // Add Student Modal
  const addBtn      = document.getElementById('add-student-btn');
  const addModal    = document.getElementById('add-student-modal');
  const addClose    = document.getElementById('add-student-close');
  const addCancel   = document.getElementById('add-student-cancel');
  const addForm     = document.getElementById('add-student-form');
  const addEmail    = document.getElementById('student-email');
  const addError    = document.getElementById('add-student-error');
  const addSaveBtn  = document.getElementById('add-student-save');

  let editingCourseId = null;
  let currentCourseId = null;
  let currentRoster   = null;

  /* ------------------------------ alerts ---------------------------- */

  function showAlert(kind, message) {
    alertArea.innerHTML = `<div class="alert alert--${kind}" role="alert"><div>${esc(message)}</div></div>`;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function clearAlert() { alertArea.innerHTML = ''; }

  function showRosterAlert(kind, message) {
    rosterAlert.innerHTML = `<div class="alert alert--${kind}" role="alert"><div>${esc(message)}</div></div>`;
  }

  function clearRosterAlert() { rosterAlert.innerHTML = ''; }

  /* ------------------------------ badges ---------------------------- */

  function statusBadge(status) {
    const klass = status === 'Active' ? 'badge--active' : 'badge--disabled';
    return `<span class="badge ${klass}"><span class="badge__dot"></span>${esc(status)}</span>`;
  }

  function roleBadge(role) {
    const klass = role === 'Admin' ? 'badge--admin' : role === 'Lecturer' ? 'badge--lecturer' : 'badge--student';
    return `<span class="badge ${klass}"><span class="badge__dot"></span>${esc(role)}</span>`;
  }

  /* --------------------------- list states -------------------------- */

  function renderLoading() {
    summaryEl.textContent = 'Loading…';
    listArea.innerHTML = `<div class="state"><span class="spinner"></span><div class="state__title u-mt-2">Loading courses…</div></div>`;
  }

  function renderError(err) {
    summaryEl.textContent = 'Could not load courses.';
    listArea.innerHTML = `<div class="state"><div class="state__title">Could not load courses</div><div>${esc(err.message)}</div></div>`;
    showAlert('danger', 'Failed to load courses: ' + err.message);
  }

  function renderEmpty() {
    summaryEl.textContent = 'No courses yet.';
    listArea.innerHTML = `<div class="state"><div class="state__title">No courses</div><div>Click "+ New course" to create one.</div></div>`;
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
          <div class="u-flex u-gap-2" style="justify-content:flex-end;">
            <button class="btn btn--ghost btn--sm" type="button" data-action="view-roster" data-cid="${c.course_id}">Roster</button>
            <button class="btn btn--ghost btn--sm" type="button" data-action="edit-course" data-cid="${c.course_id}">Edit</button>
            <button class="btn btn--danger btn--sm" type="button" data-action="delete-course" data-cid="${c.course_id}" data-code="${esc(c.code)}">Delete</button>
          </div>
        </td>
      </tr>`).join('');

    listArea.innerHTML = `
      <div class="table-wrap">
        <table class="table">
          <thead><tr>
            <th class="num">ID</th><th>Code</th><th>Name</th><th>Lecturer</th><th class="num">Students</th>
            <th style="text-align:right;">Actions</th>
          </tr></thead>
          <tbody>${rows}</tbody>
        </table>
      </div>`;
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

  /* -------------------------- Course Modal -------------------------- */

  async function loadLecturers() {
    selectLec.innerHTML = '<option value="">Loading...</option>';
    try {
      const data = await Api.get('/api/admin/accounts?role=Lecturer');
      selectLec.innerHTML = '<option value="">-- Select Lecturer --</option>' + 
        data.users.map(u => `<option value="${u.user_id}">${esc(u.full_name)} (${esc(u.email)})</option>`).join('');
    } catch (err) {
      selectLec.innerHTML = '<option value="">Error loading lecturers</option>';
    }
  }

  async function openCourseModal(course) {
    editingCourseId = course ? course.course_id : null;
    courseError.hidden = true;
    
    await loadLecturers();

    if (course) {
      courseModalTitle.textContent = `Edit Course: ${course.code}`;
      inputCode.value = course.code;
      inputName.value = course.name;
      selectLec.value = String(course.lecturer_id);
    } else {
      courseModalTitle.textContent = 'New Course';
      inputCode.value = '';
      inputName.value = '';
      selectLec.value = '';
    }

    courseModal.style.display = 'flex';
    modalBackdrop.classList.add('is-open');
  }

  function closeCourseModal() {
    courseModal.style.display = 'none';
    modalBackdrop.classList.remove('is-open');
    editingCourseId = null;
  }

  /* --------------------------- Roster Modal ------------------------- */

  function openRosterModal() {
    rosterModal.style.display = 'flex';
    modalBackdrop.classList.add('is-open');
  }

  function closeRosterModal() {
    rosterModal.style.display = 'none';
    modalBackdrop.classList.remove('is-open');
    clearRosterAlert();
    currentCourseId = null;
    currentRoster = null;
  }

  function renderRosterError(err) {
    rosterBody.innerHTML = `<div class="state"><div class="state__title">Could not load roster</div><div>${esc(err.message)}</div></div>`;
  }

  function renderRoster(data) {
    currentRoster = data;
    rosterTitle.textContent = `${data.code} — ${data.name}`;
    rosterSub.textContent   = `Course #${data.course_id}`;

    let lecturerHTML = data.lecturer ? `
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
      </div>` : `<p class="u-text-muted">No lecturer assigned.</p>`;

    const activeStudents = data.students.filter(s => s.status === 'Active');

    const studentRows = activeStudents.length === 0
      ? `<div class="state">No students enrolled.</div>`
      : `<div class="table-wrap">
          <table class="table">
            <thead><tr><th class="num">ID</th><th>Email</th><th>Name</th><th>Role</th><th>Enrollment</th><th>Enrolled</th><th style="text-align:right;">Actions</th></tr></thead>
            <tbody>
              ${activeStudents.map(s => `
                <tr>
                  <td class="num">${s.user_id}</td>
                  <td>${esc(s.email)}</td>
                  <td>${esc(s.full_name)}</td>
                  <td>${roleBadge(s.role || 'Student')}</td>
                  <td>${statusBadge(s.status)}</td>
                  <td class="num">${esc(fmtDateTime(s.enrolled_at))}</td>
                  <td class="u-text-right">
                    <button class="btn btn--danger btn--sm" type="button" data-action="remove-student" data-uid="${s.user_id}" data-email="${esc(s.email)}">Remove</button>
                  </td>
                </tr>`).join('')}
            </tbody>
          </table>
        </div>`;

    rosterBody.innerHTML = `
      <div class="u-text-sm u-text-muted" style="text-transform:uppercase; letter-spacing:.06em;">Lecturer</div>
      ${lecturerHTML}
      <div class="u-text-sm u-text-muted u-mt-4" style="text-transform:uppercase; letter-spacing:.06em;">${activeStudents.length} Enrolled Students</div>
      ${studentRows}`;
  }

  async function openRoster(courseId) {
    currentCourseId = courseId;
    clearRosterAlert();
    rosterTitle.textContent = 'Course roster';
    rosterSub.textContent   = `Course #${courseId}`;
    rosterBody.innerHTML    = `<div class="state"><span class="spinner"></span><div class="state__title u-mt-2">Loading roster…</div></div>`;
    openRosterModal();
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

  /* -------------------- Add Student Modal ------------------ */

  function openAddModal() {
    addEmail.value = '';
    addError.hidden = true;
    addModal.style.display = 'flex';
    setTimeout(() => addEmail.focus(), 0);
  }

  function closeAddModal() {
    addModal.style.display = 'none';
  }

  /* ----------------------------- events ----------------------------- */

  refreshBtn.addEventListener('click', load);
  newCourseBtn.addEventListener('click', () => openCourseModal(null));
  
  courseModalClose.addEventListener('click', closeCourseModal);
  courseModalCancel.addEventListener('click', closeCourseModal);
  modalClose.addEventListener('click', closeRosterModal);
  modalBackdrop.addEventListener('click', () => { closeCourseModal(); closeRosterModal(); });

  addBtn.addEventListener('click', openAddModal);
  addClose.addEventListener('click', closeAddModal);
  addCancel.addEventListener('click', closeAddModal);

  // Handle Course Form Submit (Create / Edit)
  courseForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    courseError.hidden = true;

    const code = inputCode.value.trim();
    const name = inputName.value.trim();
    const lecturer_id = Number(selectLec.value);

    if (!code) return showCourseError('Course code is required.');
    if (!name) return showCourseError('Course name is required.');
    if (!lecturer_id) return showCourseError('Please assign a lecturer.');

    const payload = { code, name, lecturer_id };

    courseSaveBtn.disabled = true;
    try {
      if (editingCourseId) {
        await Api.put(`/api/admin/courses/${editingCourseId}`, payload);
        showAlert('success', `Course "${code}" updated.`);
      } else {
        await Api.post('/api/admin/courses', payload);
        showAlert('success', `Course "${code}" created.`);
      }
      closeCourseModal();
      await load();
    } catch (err) {
      // Catch BR errors from backend (e.g., Duplicate code)
      showCourseError(err.message);
    } finally {
      courseSaveBtn.disabled = false;
    }
  });

  function showCourseError(msg) {
    courseError.hidden = false;
    courseError.textContent = msg;
  }

  // Handle Add Student Submit
  addForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    addError.hidden = true;
    const email = addEmail.value.trim().toLowerCase();

    if (!email || !email.includes('@')) return showAddError('A valid email is required.');

    addSaveBtn.disabled = true;
    try {
      await Api.post(`/api/admin/courses/${currentCourseId}/enrollments`, { student_email: email });
      closeAddModal();
      showRosterAlert('success', `Student "${email}" enrolled.`);
      await reloadRoster();
      await load();
    } catch (err) {
      showAddError(err.message);
    } finally {
      addSaveBtn.disabled = false;
    }
  });

  function showAddError(msg) {
    addError.hidden = false;
    addError.textContent = msg;
  }

  // Handle Table Actions (Roster, Edit, Delete, Remove Student)
  document.addEventListener('click', async (event) => {
    const rosterBtn = event.target.closest('button[data-action="view-roster"]');
    if (rosterBtn) {
      openRoster(Number(rosterBtn.dataset.cid));
      return;
    }

    const editBtn = event.target.closest('button[data-action="edit-course"]');
    if (editBtn) {
      const cid = Number(editBtn.dataset.cid);
      try {
        const course = await Api.get(`/api/admin/courses`).then(d => d.courses.find(x => x.course_id === cid));
        if (course) openCourseModal(course);
      } catch (err) {
        showAlert('danger', 'Failed to load course details: ' + err.message);
      }
      return;
    }

    const delBtn = event.target.closest('button[data-action="delete-course"]');
    if (delBtn) {
      const cid = Number(delBtn.dataset.cid);
      const code = delBtn.dataset.code;
      
      const warningMsg = `WARNING: HARD DELETE\n\n` +
                         `You are about to permanently delete the course "${code}".\n` +
                         `This will PERMANENTLY DESTROY all enrolled students, quizzes, and student grades/attempts associated with this course.\n\n` +
                         `This action CANNOT be undone. Are you absolutely sure?`;
                         
      if (!window.confirm(warningMsg)) return;

      delBtn.disabled = true;
      try {
        await Api.del(`/api/admin/courses/${cid}`);
        showAlert('success', `Course "${code}" and all associated data deleted.`);
        await load();
      } catch (err) {
        showAlert('danger', err.message);
        delBtn.disabled = false;
      }
      return;
    }

    const removeBtn = event.target.closest('button[data-action="remove-student"]');
    if (removeBtn) {
      const uid = removeBtn.dataset.uid;
      const email = removeBtn.dataset.email;
      if (!window.confirm(`Remove "${email}" from this course?`)) return;

      removeBtn.disabled = true;
      try {
        await Api.del(`/api/admin/courses/${currentCourseId}/enrollments/${uid}`);
        showRosterAlert('success', `Student "${email}" removed.`);
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