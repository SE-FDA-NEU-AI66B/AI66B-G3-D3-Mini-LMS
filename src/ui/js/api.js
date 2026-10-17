/* ==========================================================================
   Mini-LMS — API client
   Vanilla ES2018+, no build step, no dependencies.
   Served from: src/ui/js/api.js

   Temporary identity: the `email` query parameter, falling back to
   sessionStorage, falling back to a default lecturer. When real SSO
   sessions land, swap `getEmail()` for a cookie/session read — nothing
   else in the app needs to change.
   ========================================================================== */

(function (global) {
  'use strict';

  const DEFAULT_EMAIL = 'lanpt@univ.edu';
  const EMAIL_KEY     = 'minilms.email';

  function getEmail() {
    const params = new URLSearchParams(global.location.search);
    const fromUrl = params.get('email');
    if (fromUrl) {
      try { sessionStorage.setItem(EMAIL_KEY, fromUrl); } catch (e) { /* ignore */ }
      return fromUrl;
    }
    try {
      const stored = sessionStorage.getItem(EMAIL_KEY);
      if (stored) return stored;
    } catch (e) { /* ignore */ }
    return DEFAULT_EMAIL;
  }

  function buildUrl(path) {
    const url = new URL(path, global.location.origin);
    url.searchParams.set('email', getEmail());
    return url.toString();
  }

  function ApiError(message, status, payload) {
    const err = new Error(message);
    err.name = 'ApiError';
    err.status = status;
    err.payload = payload;
    return err;
  }

  async function request(method, path, body) {
    const opts = { method, headers: { Accept: 'application/json' } };
    if (body !== undefined) {
      opts.headers['Content-Type'] = 'application/json';
      opts.body = JSON.stringify(body);
    }

    let res;
    try {
      res = await fetch(buildUrl(path), opts);
    } catch (err) {
      throw ApiError('Network error. Is the server running?', 0);
    }

    let payload = null;
    const text = await res.text();
    if (text) {
      try { payload = JSON.parse(text); }
      catch (e) { payload = { detail: text }; }
    }

    if (!res.ok) {
      const msg =
        (payload && payload.detail) ||
        res.statusText ||
        ('Request failed with status ' + res.status);
      throw ApiError(String(msg), res.status, payload);
    }
    return payload;
  }

  function esc(s) {
    if (s == null) return '';
    return String(s)
      .replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  }

  function fmtDateTime(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d.getTime())) return iso;
    const p = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())} ` +
           `${p(d.getHours())}:${p(d.getMinutes())}`;
  }

  function toLocalInputValue(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    const p = n => String(n).padStart(2, '0');
    return `${d.getFullYear()}-${p(d.getMonth() + 1)}-${p(d.getDate())}` +
           `T${p(d.getHours())}:${p(d.getMinutes())}`;
  }

  global.MiniLMS = global.MiniLMS || {};
  global.MiniLMS.Api = {
    getEmail,
    get:  (p)    => request('GET', p),
    post: (p, b) => request('POST', p, b),
    put:  (p, b) => request('PUT', p, b),
    del:  (p)    => request('DELETE', p),
  };
  global.MiniLMS.esc = esc;
  global.MiniLMS.fmtDateTime = fmtDateTime;
  global.MiniLMS.toLocalInputValue = toLocalInputValue;
})(window);