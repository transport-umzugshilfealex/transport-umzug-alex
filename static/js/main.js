/* Main JS for Transport & Umzugshilfe Alex */

// ---------- Cookie consent & Google Analytics ----------
(() => {
  const CONSENT_KEY = "cookie-consent-v1";
  const GA_ID = window.GA_MEASUREMENT_ID;

  const banner = document.getElementById("cookieBanner");
  const acceptButton = document.getElementById("cookieAccept");
  const rejectButton = document.getElementById("cookieReject");
  const settingsButton = document.getElementById("cookieSettings");
  if (!banner || !acceptButton || !rejectButton) return;

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
    if (!GA_ID) return;
    window["ga-disable-" + GA_ID] = false;
    updateConsent("granted");
    if (window.__googleAnalyticsLoaded) return;

    window.__googleAnalyticsLoaded = true;

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

        const parts = location.hostname.split(".");
        for (let index = 0; index < parts.length - 1; index += 1) {
          document.cookie = name + "=; Max-Age=0; path=/; domain=" +
            parts.slice(index).join(".") + "; SameSite=Lax";
        }
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
    if (GA_ID) window["ga-disable-" + GA_ID] = true;
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

// ---------- Navigation and contact form ----------
(() => {
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
          behavior: window.matchMedia("(prefers-reduced-motion: reduce)").matches ? "auto" : "smooth",
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
    email_invalid: {
      de: "Bitte geben Sie eine gültige E-Mail-Adresse ein.",
      en: "Please enter a valid email address.",
      ru: "Введите корректный адрес электронной почты."
    },
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
      de: "Keine Bestätigung erhalten. Bitte kontaktieren Sie uns telefonisch, bevor Sie erneut senden.",
      en: "No confirmation received. Please call us before sending again.",
      ru: "Подтверждение не получено. Позвоните нам перед повторной отправкой."
    },
    server: {
      de: "Die Nachricht konnte nicht gesendet werden. Bitte rufen Sie uns an.",
      en: "The message could not be sent. Please call us.",
      ru: "Не удалось отправить сообщение. Позвоните нам."
    },
    rate_limit: {
      de: "Zu viele Anfragen. Bitte versuchen Sie es später erneut.",
      en: "Too many requests. Please try again later.",
      ru: "Слишком много запросов. Попробуйте позже."
    },
    csrf_token: {
      de: "Bitte laden Sie die Seite neu und versuchen Sie es erneut.",
      en: "Please reload the page and try again.",
      ru: "Обновите страницу и попробуйте снова."
    },
    calculator_data: {
      de: "Bitte berechnen Sie Ihren Umzug erneut oder entfernen Sie die Umzugsdaten aus der Anfrage.",
      en: "Please recalculate your move or remove the moving details from your request.",
      ru: "Рассчитайте переезд заново или уберите данные переезда из заявки."
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
    }, 60000);

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
          "⚠️ " + translate(response.status === 429 ? "rate_limit" : response.status >= 500 ? "server" : "check");

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
              const specialError = ["server", "rate_limit", "csrf_token", "calculator_data"].find(
                (key) => Object.hasOwn(result.errors, key)
              );
              message = specialError
                ? "⚠️ " + translate(specialError)
                : message + " — " + String(firstError[0]);
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
        translate("email_invalid")
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

  if (!root.dataset.theme) {
    root.dataset.theme = window.matchMedia("(prefers-color-scheme: dark)").matches
      ? "dark" : "light";
  }

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
    scrollWheelZoom: false,
    zoomControl: false
  }).setView(
    [latitude, longitude],
    12
  );

  L.control.zoom({
    zoomInTitle: mapElement.dataset.zoomIn,
    zoomOutTitle: mapElement.dataset.zoomOut
  }).addTo(map);

  L.tileLayer(
    "https://tile.openstreetmap.org/{z}/{x}/{y}.png",
    {
      maxZoom: 19,
      attribution:
        '© <a href="https://www.openstreetmap.org/copyright">' + mapElement.dataset.contributors + "</a>"
    }
  ).addTo(map);

  L.circleMarker([latitude, longitude], {
    radius: 9,
    color: "#ffffff",
    weight: 2,
    fillColor: "#d62828",
    fillOpacity: 1
  })
    .addTo(map)
    .bindPopup("Bremen-Nord")
    .openPopup();
})();
