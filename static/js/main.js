/* Main JS for Transport & Umzugshilfe Alex */

// ---------- Cookie consent & Google Analytics ----------
(() => {
  const CONSENT_KEY = "cookie-consent-v1";
  const GA_ID = window.GA_MEASUREMENT_ID;

  const banner = document.getElementById("cookieBanner");
  const acceptButton = document.getElementById("cookieAccept");
  const rejectButton = document.getElementById("cookieReject");
  const settingsButton = document.getElementById("cookieSettings");
  const title = document.getElementById("cookieTitle");
  const text = document.getElementById("cookieText");
  const privacyLink = document.getElementById("cookiePrivacyLink");

  if (!banner || !acceptButton || !rejectButton) return;

  const language = (document.documentElement.lang || "de")
    .toLowerCase()
    .split("-")[0];

  const messages = {
    de: {
      title: "Datenschutzeinstellungen",
      text: "Wir verwenden optionale Analyse-Cookies von Google Analytics, um die Nutzung unserer Website zu verstehen. Sie können zustimmen oder ablehnen.",
      privacy: "Mehr erfahren",
      accept: "Alle akzeptieren",
      reject: "Ablehnen"
    },
    ru: {
      title: "Настройки конфиденциальности",
      text: "Мы используем необязательные аналитические файлы cookie Google Analytics, чтобы понимать, как используется сайт. Вы можете согласиться или отказаться.",
      privacy: "Подробнее",
      accept: "Принять все",
      reject: "Отклонить"
    },
    en: {
      title: "Privacy settings",
      text: "We use optional Google Analytics cookies to understand how our website is used. You can accept or reject them.",
      privacy: "Learn more",
      accept: "Accept all",
      reject: "Reject"
    }
  };

  const copy = messages[language] || messages.de;

  title.textContent = copy.title;
  text.textContent = copy.text;
  privacyLink.textContent = copy.privacy;
  acceptButton.textContent = copy.accept;
  rejectButton.textContent = copy.reject;

  const readChoice = () => {
    try {
      return localStorage.getItem(CONSENT_KEY);
    } catch (_) {
      return null;
    }
  };

  const saveChoice = (choice) => {
    try {
      localStorage.setItem(CONSENT_KEY, choice);
    } catch (_) {}
  };

  const updateConsent = (value) => {
    if (typeof window.gtag !== "function") return;

    window.gtag("consent", "update", {
      analytics_storage: value,
      ad_storage: "denied",
      ad_user_data: "denied",
      ad_personalization: "denied"
    });
  };

  const loadAnalytics = () => {
    if (!GA_ID || window.__googleAnalyticsLoaded) return;

    window.__googleAnalyticsLoaded = true;

    updateConsent("granted");

    window.gtag("js", new Date());
    window.gtag("config", GA_ID, {
      anonymize_ip: true
    });

    const script = document.createElement("script");

    script.async = true;
    script.src =
      "https://www.googletagmanager.com/gtag/js?id=" +
      encodeURIComponent(GA_ID);

    document.head.appendChild(script);
  };

  const deleteAnalyticsCookies = () => {
    document.cookie.split(";").forEach((cookie) => {
      const name = cookie.split("=")[0].trim();

      if (name === "_ga" || name.startsWith("_ga_")) {
        document.cookie =
          name + "=; Max-Age=0; path=/; SameSite=Lax";

        document.cookie =
          name +
          "=; Max-Age=0; path=/; domain=" +
          location.hostname +
          "; SameSite=Lax";
      }
    });
  };

  const hideBanner = () => {
    banner.hidden = true;
  };

  const showBanner = () => {
    banner.hidden = false;
    acceptButton.focus();
  };

  acceptButton.addEventListener("click", () => {
    saveChoice("accepted");
    loadAnalytics();
    hideBanner();
  });

  rejectButton.addEventListener("click", () => {
    saveChoice("rejected");
    updateConsent("denied");
    deleteAnalyticsCookies();
    hideBanner();
  });

  settingsButton?.addEventListener("click", showBanner);

  const savedChoice = readChoice();

  if (savedChoice === "accepted") {
    loadAnalytics();
  } else if (savedChoice !== "rejected") {
    showBanner();
  }
})();

// ---------- Language selection ----------
(() => {
  document.querySelectorAll("[data-lang]").forEach((link) => {
    link.addEventListener("click", () => {
      try {
        localStorage.setItem(
          "site-language-selected",
          link.dataset.lang
        );
      } catch (_) {}
    });
  });

  // ---------- Burger menu ----------
  const button = document.getElementById("menuToggle");
  const menu = document.getElementById("mainmenu");

  if (button && menu) {
    const closeMenu = () => {
      button.setAttribute("aria-expanded", "false");
      menu.classList.remove("open");
    };

    button.addEventListener("click", () => {
      const isOpen =
        button.getAttribute("aria-expanded") === "true";

      button.setAttribute(
        "aria-expanded",
        String(!isOpen)
      );

      menu.classList.toggle("open", !isOpen);
    });

    menu.querySelectorAll("a").forEach((link) => {
      link.addEventListener("click", closeMenu);
    });

    document.addEventListener("keydown", (event) => {
      if (event.key === "Escape") {
        closeMenu();
      }
    });

    document.addEventListener("click", (event) => {
      const isOpen =
        button.getAttribute("aria-expanded") === "true";

      if (
        isOpen &&
        !menu.contains(event.target) &&
        !button.contains(event.target)
      ) {
        closeMenu();
      }
    });
  }

  // ---------- Smooth scrolling ----------
  document
    .querySelectorAll('a[href^="#"]')
    .forEach((link) => {
      link.addEventListener("click", (event) => {
        const id = link.getAttribute("href");

        if (!id || id === "#") return;

        const element = document.querySelector(id);

        if (!element) return;

        event.preventDefault();

        element.scrollIntoView({
          behavior: "smooth",
          block: "start"
        });
      });
    });

  // ---------- Contact form ----------
  const form = document.getElementById("contactForm");

  if (!form) return;

  const statusElement =
    document.getElementById("formStatus");

  const submitButton = form.querySelector(
    'button[type="submit"]'
  );

  const locale = (
    document.documentElement.lang || "de"
  )
    .toLowerCase()
    .split("-")[0];

  const messages = {
    sent: {
      de: "Gesendet! Wir melden uns bald.",
      en: "Sent! We will contact you shortly.",
      ru: "Отправлено! Мы свяжемся с вами."
    },
    check: {
      de: "Bitte prüfen Sie die Felder.",
      en: "Please check the fields.",
      ru: "Проверьте поля формы."
    },
    network: {
      de: "Netzwerkfehler.",
      en: "Network error.",
      ru: "Ошибка сети."
    },
    busy: {
      de: "Senden…",
      en: "Sending…",
      ru: "Отправляем…"
    },
    timeout: {
      de: "Zeitüberschreitung.",
      en: "Request timed out.",
      ru: "Превышено время ожидания."
    }
  };

  const translate = (key) => {
    return (
      messages[key]?.[locale] ||
      messages[key]?.de ||
      ""
    );
  };

  if (statusElement) {
    statusElement.setAttribute("role", "status");
    statusElement.setAttribute("aria-live", "polite");
  }

  let requestInProgress = false;

  form.addEventListener("submit", async (event) => {
    event.preventDefault();

    if (requestInProgress) return;

    form.querySelectorAll(".is-error").forEach((element) => {
      element.classList.remove("is-error");
    });

    if (statusElement) {
      statusElement.textContent =
        "✔ " + translate("busy");
    }

    form.setAttribute("aria-busy", "true");

    if (submitButton) {
      submitButton.disabled = true;
    }

    requestInProgress = true;

    const formData = new FormData(form);
    const controller = new AbortController();

    let requestTimedOut = false;

    const timeout = setTimeout(() => {
      requestTimedOut = true;
      controller.abort();
    }, 15000);

    try {
      const response = await fetch(form.action, {
        method: "POST",
        headers: {
          Accept: "application/json",
          "X-Requested-With": "fetch"
        },
        body: formData,
        signal: controller.signal,
        credentials: "same-origin"
      });

      clearTimeout(timeout);

      if (response.ok) {
        if (statusElement) {
          statusElement.textContent =
            "✔ " + translate("sent");
        }

        form.reset();
        statusElement?.focus();
      } else {
        let message =
          "⚠️ " + translate("check");

        try {
          const result = await response.json();

          if (
            result?.errors &&
            typeof result.errors === "object"
          ) {
            Object.keys(result.errors).forEach(
              (name) => {
                const input = form.querySelector(
                  `[name="${name}"]`
                );

                input?.classList.add("is-error");
              }
            );

            const firstError = Object.values(
              result.errors
            )[0];

            if (
              Array.isArray(firstError) &&
              firstError[0]
            ) {
              message +=
                " — " + String(firstError[0]);
            }
          }
        } catch (_) {}

        if (statusElement) {
          statusElement.textContent = message;
        }
      }
    } catch (_) {
      if (statusElement) {
        statusElement.textContent =
          "⚠️ " +
          translate(
            requestTimedOut
              ? "timeout"
              : "network"
          );
      }
    } finally {
      clearTimeout(timeout);
      form.removeAttribute("aria-busy");

      if (submitButton) {
        submitButton.disabled = false;
      }

      requestInProgress = false;
    }
  });

  // ---------- Email validation ----------
  const emailInput = form.querySelector(
    'input[name="email"]'
  );

  emailInput?.addEventListener("input", () => {
    emailInput.setCustomValidity("");

    if (
      emailInput.value &&
      !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(
        emailInput.value
      )
    ) {
      emailInput.setCustomValidity(
        "Bitte geben Sie eine gültige E-Mail-Adresse ein."
      );
    }
  });

  // ---------- Phone validation ----------
  const phoneInput = form.querySelector(
    'input[name="phone"]'
  );

  phoneInput?.addEventListener("input", () => {
    phoneInput.value = phoneInput.value.replace(
      /[^\d+\s()-]/g,
      ""
    );
  });
})();

// ---------- Theme toggle ----------
(() => {
  const root = document.documentElement;

  const buttons = Array.from(
    document.querySelectorAll(
      "#themeToggle, #themeToggle2"
    )
  );

  if (!buttons.length) return;

  try {
    const savedTheme =
      localStorage.getItem("theme");

    if (
      savedTheme === "light" ||
      savedTheme === "dark"
    ) {
      root.dataset.theme = savedTheme;
    }
  } catch (_) {}

  const updateIcons = () => {
    buttons.forEach((button) => {
      button.textContent =
        root.dataset.theme === "dark"
          ? "☀️"
          : "🌙";
    });
  };

  const toggleTheme = () => {
    const nextTheme =
      root.dataset.theme === "dark"
        ? "light"
        : "dark";

    root.dataset.theme = nextTheme;

    try {
      localStorage.setItem(
        "theme",
        nextTheme
      );
    } catch (_) {}

    updateIcons();
  };

  updateIcons();

  buttons.forEach((button) => {
    button.addEventListener(
      "click",
      toggleTheme
    );
  });
})();

// ---------- Leaflet map: Bremen-Nord ----------
(() => {
  const mapElement =
    document.getElementById("map");

  if (!mapElement || !window.L) return;

  const latitude = 53.1736;
  const longitude = 8.6233;

  const map = L.map(mapElement, {
    scrollWheelZoom: false
  }).setView(
    [latitude, longitude],
    12
  );

  L.tileLayer(
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
      maxZoom: 19,
      attribution:
        "© OpenStreetMap-Mitwirkende"
    }
  ).addTo(map);

  L.marker([latitude, longitude])
    .addTo(map)
    .bindPopup("Bremen-Nord")
    .openPopup();
})();