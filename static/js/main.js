/* Main JS for Transport & Umzugshilfe Alex */
(() => {
  // ---------- Burger menu (mobile) ----------
  const btn = document.getElementById('menuToggle');
  const menu = document.getElementById('mainmenu');
  if (btn && menu) {
    const close = () => {
      btn.setAttribute('aria-expanded','false');
      menu.classList.remove('open');
    };
    btn.addEventListener('click', () => {
      const ex = btn.getAttribute('aria-expanded') === 'true';
      btn.setAttribute('aria-expanded', String(!ex));
      menu.classList.toggle('open', !ex);
    });
    // закрывать меню по клику на пункт и по Esc
    menu.querySelectorAll('a').forEach(a => a.addEventListener('click', close));
    document.addEventListener('keydown', e => { if (e.key === 'Escape') close(); });

    // закрытие по клику на переключатели языка внутри меню (если есть)
    menu.querySelectorAll('.lang-inline a').forEach(a => a.addEventListener('click', close));
  }

  // ---------- Smooth scroll for in-page anchors ----------
  document.querySelectorAll('a[href^="#"]').forEach(a => {
    a.addEventListener('click', (e) => {
      const id = a.getAttribute('href');
      if (!id || id === '#') return;
      const el = document.querySelector(id);
      if (!el) return;
      e.preventDefault();
      el.scrollIntoView({ behavior: 'smooth', block: 'start' });
    });
  });

  // ---------- Contact form ----------
  const form = document.getElementById("contactForm");
  if (!form) return;

  const statusEl = document.getElementById("formStatus");
  const submitBtn = form.querySelector('button[type="submit"]');
  const locale = document.documentElement.lang || "ru";

  const M = {
    sent: { de: "Gesendet! Wir melden uns bald.", en: "Sent! We will contact you shortly.", ru: "Отправлено! Мы свяжемся с вами." },
    check:{ de: "Bitte prüfen Sie die Felder.",   en: "Please check the fields.",          ru: "Проверьте поля формы." },
    net:  { de: "Netzwerkfehler",                  en: "Network error",                     ru: "Сетевая ошибка" },
    busy: { de: "Senden…",                         en: "Sending…",                          ru: "Отправляем…" },
    timeout:{ de:"Zeitüberschreitung", en:"Request timed out", ru:"Превышен таймаут запроса" }
  };
  const t = (k)=> (M[k] && (M[k][locale] || M[k].ru)) || "";

  statusEl.setAttribute("role", "status");
  statusEl.setAttribute("aria-live", "polite");

  let inFlight = false;

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (inFlight) return;

    [...form.elements].forEach((el) => el.classList?.remove("is-error"));
    statusEl.textContent = "✔ " + t("busy");
    form.setAttribute("aria-busy", "true");
    if (submitBtn) submitBtn.disabled = true;
    inFlight = true;

    const data = new FormData(form);

    const controller = new AbortController();
    const timer = setTimeout(() => controller.abort("timeout"), 15000);

    try {
      const resp = await fetch(form.action, {
        method: "POST",
        headers: { Accept: "application/json", "X-Requested-With": "fetch" },
        body: data,
        signal: controller.signal,
        credentials: "same-origin"
      });
      clearTimeout(timer);

      if (resp.ok) {
        statusEl.textContent = "✔ " + t("sent");
        form.reset();
        statusEl.focus?.();
      } else {
        let msg = "⚠️ " + t("check");
        try {
          const json = await resp.json();
          if (json?.errors && typeof json.errors === "object") {
            Object.keys(json.errors).forEach((name) => {
              const el = form.querySelector(`[name="${name}"]`);
              if (el) el.classList.add("is-error");
            });
            const first = Object.values(json.errors)[0];
            if (Array.isArray(first) && first[0]) msg += " — " + String(first[0]);
          }
        } catch {}
        statusEl.textContent = msg;
      }
    } catch (err) {
      statusEl.textContent = "⚠️ " + (err === "timeout" ? t("timeout") : t("net"));
    } finally {
      form.removeAttribute("aria-busy");
      if (submitBtn) submitBtn.disabled = false;
      inFlight = false;
    }
  });

  // simple client-side helpers
  const emailInput = form.querySelector('input[name="email"]');
  const phoneInput = form.querySelector('input[name="phone"]');
  emailInput?.addEventListener("input", () => {
    emailInput.setCustomValidity("");
    if (emailInput.value && !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(emailInput.value)) {
      emailInput.setCustomValidity("Invalid email");
    }
  });
  phoneInput?.addEventListener("input", () => {
    phoneInput.value = phoneInput.value.replace(/[^\d+\s()-]/g, "");
  });
})();

// --- theme toggle (две кнопки: в шапке и в мобильном меню) ---
(() => {
  const root = document.documentElement;
  const buttons = Array.from(document.querySelectorAll('#themeToggle, #themeToggle2'));
  if(!buttons.length) return;

  const saved = localStorage.getItem('theme'); // 'light' | 'dark'
  if (saved === 'light' || saved === 'dark') root.dataset.theme = saved;

  const setIcons = () => buttons.forEach(btn => btn.textContent = (root.dataset.theme === 'dark') ? '☀️' : '🌙');
  setIcons();

  const toggle = () => {
    const next = (root.dataset.theme === 'dark') ? 'light' : 'dark';
    root.dataset.theme = next;
    localStorage.setItem('theme', next);
    setIcons();
  };

  buttons.forEach(btn => btn.addEventListener('click', toggle));
})();
// --- Leaflet Map: Bremen-Nord ---
(() => {
  const el = document.getElementById('map');
  if (!el || !window.L) return;

  const lat = 53.1736, lon = 8.6233; // Bremen-Nord
  const map = L.map(el, { scrollWheelZoom:false }).setView([lat, lon], 12);

  L.tileLayer('https://tile.openstreetmap.org/{z}/{x}/{y}.png', {
    maxZoom: 19,
    attribution: '© OpenStreetMap-Mitwirkende'
  }).addTo(map);

  L.marker([lat, lon])
    .addTo(map)
    .bindPopup('Bremen-Nord')
    .openPopup()
  // По желанию: отключить тач-скролл до первого тапа
  // map.touchZoom.disable(); map.dragging.disable();
  // el.addEventListener('click', () => { map.touchZoom.enable(); map.dragging.enable(); }, { once:true });
})();
