/* ==========================================================================
   Mini-LMS — lecturer quiz editor page controller
   Serves both "create new quiz" and "edit existing quiz" modes.
   Served from: src/ui/js/instructor-quiz-edit.js
   ========================================================================== */

(function () {
  'use strict';

  const { Api, esc, toLocalInputValue } = window.MiniLMS;

  /* --------------------------- page state --------------------------- */

  const params = new URLSearchParams(window.location.search);
  const QUIZ_ID = params.get('quiz_id') ? Number(params.get('quiz_id')) : null;

  let currentQuiz = null;         // populated in edit mode
  let editingQuestionId = null;   // null = creating a new question

  /* --------------------------- element refs ------------------------- */

  const $ = (id) => document.getElementById(id);

  const els = {
    pageTitle:      $('page-title'),
    pageSub:        $('page-sub'),
    alertArea:      $('alert-area'),
    metaForm:       $('meta-form'),
    courseSelect:   $('course_id'),
    title:          $('title'),
    timeLimit:      $('time_limit_min'),
    dueAt:          $('due_at'),
    statusBadge:    $('status-badge'),
    saveMetaBtn:    $('save-meta-btn'),
    metaHint:       $('meta-hint'),
    questionsCard:  $('questions-card'),
    questionsArea:  $('questions-area'),
    addQuestionBtn: $('add-question-btn'),
    modal:          $('question-modal'),
    modalBackdrop:  $('modal-backdrop'),
    modalTitle:     $('modal-title'),
    modalClose:     $('modal-close'),
    modalCancel:    $('modal-cancel'),
    questionForm:   $('question-form'),
    qType:          $('q_type'),
    qPrompt:        $('q_prompt'),
    qAnswers:       $('q_answers'),
    mcqSection:     $('mcq-section'),
    shortSection:   $('short-section'),
    mcqOptions:     $('mcq-options'),
    questionError:  $('question-error'),
    questionSaveBtn:$('question-save-btn'),
    publishBtn:     $('publish-btn'),
  };

  /* ---------------------------- helpers ----------------------------- */

  function showAlert(kind, message) {
    els.alertArea.innerHTML =
      `<div class="alert alert--${kind}" role="alert"><div>${esc(message)}</div></div>`;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function clearAlert() { els.alertArea.innerHTML = ''; }

  function statusClass(s) {
    if (s === 'Published')   return 'badge--published';
    if (s === 'Unpublished') return 'badge--unpublished';
    return 'badge--draft';
  }

  function dateToLocalInput(d) {
    const p = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}` +
           `T${p(d.getHours())}:${p(d.getMinutes())}`;
  }

  function defaultDueAt() {
    const d = new Date();
    d.setDate(d.getDate() + 7);
    d.setHours(23, 59, 0, 0);
    return dateToLocalInput(d);
  }

  function editorUrl(quizId) {
    const email = encodeURIComponent(Api.getEmail());
    return `/ui/html/instructor-quiz-edit.html?quiz_id=${quizId}&email=${email}`;
  }

  /* ---------------------------- bootstrap --------------------------- */

  async function init() {
    try {
      await loadCourses();

      if (!els.courseSelect.value) {
        els.saveMetaBtn.disabled = true;
        showAlert('warning',
          'You have no courses assigned. Ask the administrator to assign you to a course.');
      }

      if (QUIZ_ID) {
        await loadQuiz();
      } else {
        prepareCreateForm();
      }
    } catch (err) {
      showAlert('danger', err.message);
    }
  }

  async function loadCourses() {
    const data = await Api.get('/api/instructor/courses');
    if (data.courses.length === 0) {
      els.courseSelect.innerHTML = '<option value="">(no courses assigned)</option>';
      return;
    }
    els.courseSelect.innerHTML = data.courses.map(c =>
      `<option value="${c.course_id}">${esc(c.code)} — ${esc(c.name)}</option>`
    ).join('');
  }

  function prepareCreateForm() {
    els.pageTitle.textContent = 'New quiz';
    els.pageSub.textContent   = 'Set the quiz details, then add questions.';
    els.dueAt.value           = defaultDueAt();
    els.statusBadge.hidden    = true;
    els.questionsCard.hidden  = true;
    els.saveMetaBtn.textContent = 'Create quiz';
    els.metaHint.textContent = 'Created as Draft. Add questions next.';
  }

  function updateStatusControls(status) {
    els.statusBadge.hidden    = false;
    els.statusBadge.className = 'badge ' + statusClass(status);
    els.statusBadge.textContent = status;

    if (status === 'Draft' || status === 'Unpublished') {
      els.publishBtn.hidden       = false;
      els.publishBtn.className    = 'btn btn--primary btn--sm';
      els.publishBtn.textContent  = status === 'Draft' ? 'Publish' : 'Re-publish';
      els.publishBtn.dataset.act  = 'publish';
    } else if (status === 'Published') {
      els.publishBtn.hidden       = false;
      els.publishBtn.className    = 'btn btn--ghost btn--sm';
      els.publishBtn.textContent  = 'Unpublish';
      els.publishBtn.dataset.act  = 'unpublish';
    } else {
      els.publishBtn.hidden = true;
    }
  }

  async function loadQuiz() {
    currentQuiz = await Api.get(`/api/instructor/quizzes/${QUIZ_ID}`);

    els.pageTitle.textContent = 'Edit quiz';
    els.pageSub.textContent   = `Quiz #${currentQuiz.quiz_id} · ${currentQuiz.course_code}`;
    els.courseSelect.value    = String(currentQuiz.course_id);
    els.courseSelect.disabled = true;      // course cannot change after creation
    els.title.value           = currentQuiz.title;
    els.timeLimit.value       = currentQuiz.time_limit_min;
    els.dueAt.value           = toLocalInputValue(currentQuiz.due_at);

    updateStatusControls(currentQuiz.status);

    els.questionsCard.hidden  = false;
    els.saveMetaBtn.textContent = 'Save changes';
    els.metaHint.textContent  = `Status: ${currentQuiz.status}`;

    renderQuestions(currentQuiz.questions);
  }

  /* -------------------------- metadata save ------------------------- */

  els.saveMetaBtn.addEventListener('click', async () => {
    clearAlert();

    const title     = els.title.value.trim();
    const timeLimit = Number(els.timeLimit.value);
    const dueAt     = els.dueAt.value;

    if (!title) {
      return showAlert('danger', 'Title is required.');
    }
    if (!Number.isInteger(timeLimit) || timeLimit < 5 || timeLimit > 120) {
      return showAlert('danger', 'Time limit must be between 5 and 120 minutes.');
    }
    if (!dueAt) {
      return showAlert('danger', 'Due date is required.');
    }

    els.saveMetaBtn.disabled = true;
    try {
      if (QUIZ_ID) {
        await Api.put(`/api/instructor/quizzes/${QUIZ_ID}`, {
          title,
          time_limit_min: timeLimit,
          due_at: dueAt,
        });
        await loadQuiz();
        showAlert('success', 'Quiz updated.');
      } else {
        const courseId = Number(els.courseSelect.value);
        if (!courseId) throw new Error('Please select a course.');

        const created = await Api.post('/api/instructor/quizzes', {
          course_id: courseId,
          title,
          time_limit_min: timeLimit,
          due_at: dueAt,
        });
        window.location.href = editorUrl(created.quiz_id);
        return;
      }
    } catch (err) {
      showAlert('danger', err.message);
    } finally {
      els.saveMetaBtn.disabled = false;
    }
  });

  els.publishBtn.addEventListener('click', async () => {
    const action = els.publishBtn.dataset.act;
    if (!action) return;
    const verb = action === 'publish' ? 'publish' : 'unpublish';

    if (!window.confirm(`Are you sure you want to ${verb} this quiz?`)) return;

    els.publishBtn.disabled = true;
    try {
      await Api.post(`/api/instructor/quizzes/${QUIZ_ID}/${action}`);
      await loadQuiz();
      showAlert('success',
        `Quiz ${action === 'publish' ? 'published' : 'unpublished'}.`);
    } catch (err) {
      showAlert('danger', err.message);
    } finally {
      els.publishBtn.disabled = false;
    }
  });

  /* ---------------------------- questions --------------------------- */

  function renderQuestions(questions) {
    if (!questions || questions.length === 0) {
      els.questionsArea.innerHTML =
        `<div class="state">` +
        `<div class="state__title">No questions yet</div>` +
        `<div>Add at least one question before publishing.</div>` +
        `</div>`;
      return;
    }

    const items = questions.map(questionCard).join('');
    els.questionsArea.innerHTML = `<div class="card__body">${items}</div>`;
  }

  function questionCard(q) {
    let body;
    if (q.question_type === 'MCQ') {
      const list = q.options.map(o => {
        const badge = o.is_correct
          ? ` <span class="badge badge--active"><span class="badge__dot"></span>correct</span>`
          : '';
        return `<li>${esc(o.label)}. ${esc(o.text)}${badge}</li>`;
      }).join('');
      body = `<ul style="margin:0;padding-left:20px;">${list}</ul>`;
    } else {
      body =
        `<div class="u-text-sm"><strong>Accepted:</strong> ` +
        q.accepted_answers.map(a => `<code>${esc(a)}</code>`).join(', ') +
        `</div>`;
    }

    return `
      <div class="card" style="margin-bottom:12px; box-shadow:none;">
        <div class="card__head">
          <div>
            <div class="card__title">Q${q.position}. ${esc(q.prompt)}</div>
            <div class="card__hint">${esc(q.question_type)} · ${q.points} point</div>
          </div>
          <div class="u-flex u-gap-2">
            <button class="btn btn--ghost btn--sm" type="button"
                    data-action="edit-question" data-qid="${q.question_id}">Edit</button>
            <button class="btn btn--danger btn--sm" type="button"
                    data-action="delete-question" data-qid="${q.question_id}">Delete</button>
          </div>
        </div>
        <div class="card__body">${body}</div>
      </div>`;
  }

  document.addEventListener('click', async (event) => {
    const editBtn = event.target.closest('button[data-action="edit-question"]');
    if (editBtn) {
      const qid = Number(editBtn.dataset.qid);
      const q = currentQuiz.questions.find(x => x.question_id === qid);
      if (q) openModal(q);
      return;
    }

    const delBtn = event.target.closest('button[data-action="delete-question"]');
    if (delBtn) {
      const qid = Number(delBtn.dataset.qid);
      if (!window.confirm('Delete this question?')) return;
      delBtn.disabled = true;
      try {
        await Api.del(`/api/instructor/quizzes/${QUIZ_ID}/questions/${qid}`);
        await loadQuiz();
        showAlert('success', 'Question deleted.');
      } catch (err) {
        showAlert('danger', err.message);
        delBtn.disabled = false;
      }
    }
  });

  els.addQuestionBtn.addEventListener('click', () => openModal(null));

  /* ------------------------------- modal ---------------------------- */

  function renderMcqOptions(existing) {
    const letters = ['A', 'B', 'C', 'D'];
    els.mcqOptions.innerHTML = letters.map((label, idx) => {
      const opt = (existing && existing[idx]) || { text: '', is_correct: false };
      return `
        <div class="u-flex u-items-center u-gap-3 u-mt-2">
          <label class="u-flex u-items-center u-gap-2" style="min-width:64px;">
            <input type="radio" name="mcq-correct" value="${idx}"
                   ${opt.is_correct ? 'checked' : ''} />
            <strong>${label}</strong>
          </label>
          <input class="input" type="text" data-opt-text="${idx}"
                 value="${esc(opt.text)}" placeholder="Option ${label}" />
        </div>`;
    }).join('');
  }

  function readMcqOptions() {
    const letters = ['A', 'B', 'C', 'D'];
    const checked = document.querySelector('input[name="mcq-correct"]:checked');
    const correctIdx = checked ? Number(checked.value) : -1;
    const opts = [];
    for (let i = 0; i < 4; i++) {
      const input = document.querySelector(`input[data-opt-text="${i}"]`);
      opts.push({
        label: letters[i],
        text: (input && input.value || '').trim(),
        is_correct: i === correctIdx,
      });
    }
    return opts;
  }

  function toggleTypeSections() {
    const t = els.qType.value;
    els.mcqSection.hidden   = t !== 'MCQ';
    els.shortSection.hidden = t !== 'SHORT';
  }

  function showQuestionError(msg) {
    els.questionError.hidden = false;
    els.questionError.textContent = msg;
  }

  function clearQuestionError() {
    els.questionError.hidden = true;
    els.questionError.textContent = '';
  }

  function openModal(question) {
    editingQuestionId = question ? question.question_id : null;
    els.modalTitle.textContent = question ? 'Edit question' : 'Add question';
    clearQuestionError();

    if (question) {
      els.qType.value = question.question_type;
      els.qType.disabled = true;              // server forbids type change
      els.qPrompt.value = question.prompt;
      if (question.question_type === 'MCQ') {
        renderMcqOptions(question.options);
      } else {
        els.qAnswers.value = (question.accepted_answers || []).join('\n');
        renderMcqOptions(null);
      }
    } else {
      els.qType.disabled = false;
      els.qType.value = 'MCQ';
      els.qPrompt.value = '';
      els.qAnswers.value = '';
      renderMcqOptions(null);
    }

    toggleTypeSections();
    els.modal.style.display = 'flex';
    els.modalBackdrop.classList.add('is-open');
  }

  function closeModal() {
    els.modal.style.display = 'none';
    els.modalBackdrop.classList.remove('is-open');
    editingQuestionId = null;
  }

  els.qType.addEventListener('change', toggleTypeSections);
  els.modalClose.addEventListener('click', closeModal);
  els.modalCancel.addEventListener('click', closeModal);
  els.modalBackdrop.addEventListener('click', closeModal);

  els.questionForm.addEventListener('submit', async (event) => {
    event.preventDefault();
    clearQuestionError();

    const type   = els.qType.value;
    const prompt = els.qPrompt.value.trim();

    if (!prompt) return showQuestionError('Prompt is required.');

    let payload;
    if (type === 'MCQ') {
      const options = readMcqOptions();
      if (options.some(o => !o.text)) {
        return showQuestionError('Every option needs text.');
      }
      if (!options.some(o => o.is_correct)) {
        return showQuestionError('Mark exactly one option as correct.');
      }
      payload = { question_type: 'MCQ', prompt, options };
    } else {
      const answers = els.qAnswers.value
        .split('\n').map(s => s.trim()).filter(Boolean);
      if (answers.length === 0) {
        return showQuestionError('Add at least one accepted answer.');
      }
      payload = { question_type: 'SHORT', prompt, accepted_answers: answers };
    }

    els.questionSaveBtn.disabled = true;
    try {
      if (editingQuestionId) {
        await Api.put(
          `/api/instructor/quizzes/${QUIZ_ID}/questions/${editingQuestionId}`,
          payload
        );
      } else {
        await Api.post(`/api/instructor/quizzes/${QUIZ_ID}/questions`, payload);
      }
      closeModal();
      await loadQuiz();
      showAlert('success', 'Question saved.');
    } catch (err) {
      showQuestionError(err.message);
    } finally {
      els.questionSaveBtn.disabled = false;
    }
  });

  /* ------------------------------- boot ----------------------------- */

  init();
})();