/* ==========================================================================
   Mini-LMS — mock SSO page controller
   Posts {email, password} to /mock-sso/authorize, then follows the
   returned redirect (which lands on /auth/callback).
   Served from: src/ui/js/mock-sso.js
   ========================================================================== */

(function () {
  'use strict';

  const { esc } = window.MiniLMS;

  const form      = document.getElementById('sso-form');
  const alertArea = document.getElementById('alert-area');
  const submitBtn = document.getElementById('submit-btn');
  const pwInput   = document.getElementById('password');
  const togglePw  = document.getElementById('toggle-pw');

  /* ------------------------ password visibility --------------------- */

  if (togglePw && pwInput) {
    togglePw.addEventListener('click', () => {
      const show = pwInput.type === 'password';
      pwInput.type = show ? 'text' : 'password';
      togglePw.textContent = show ? 'Hide' : 'Show';
      togglePw.setAttribute('aria-label', show ? 'Hide password' : 'Show password');
    });
  }

  /* ------------------------------ alerts ---------------------------- */

  function showAlert(kind, message) {
    alertArea.innerHTML =
      `<div class="alert alert--${kind}" role="alert"><div>${esc(message)}</div></div>`;
    window.scrollTo({ top: 0, behavior: 'smooth' });
  }

  function clearAlert() { alertArea.innerHTML = ''; }

  /* ------------------------------ submit ---------------------------- */

  form.addEventListener('submit', async (event) => {
    event.preventDefault();
    clearAlert();

    const email    = document.getElementById('email').value.trim();
    const password = pwInput.value;

    if (!email || !password) {
      return showAlert('danger', 'Enter both email and password.');
    }

    submitBtn.disabled = true;
    try {
      const res = await fetch('/mock-sso/authorize', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'Accept': 'application/json',
        },
        body: JSON.stringify({ email, password }),
      });

      const payload = await res.json().catch(() => ({}));
      if (!res.ok) {
        return showAlert('danger', payload.detail || `Sign-in failed (${res.status})`);
      }
      if (!payload.redirect) {
        return showAlert('danger', 'SSO returned no redirect target.');
      }
      window.location.href = payload.redirect;
    } catch (err) {
      showAlert('danger', 'Network error. Is the server running?');
    } finally {
      submitBtn.disabled = false;
    }
  });
})();