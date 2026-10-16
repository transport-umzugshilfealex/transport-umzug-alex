/* Moving calculator: prices are calculated and validated by Flask. */
(() => {
  "use strict";
  const form = document.getElementById("movingCalculator");
  if (!form) return;
  const messages = JSON.parse(document.getElementById("calculatorMessages").textContent);
  const ui = (id) => document.getElementById(id);
  const panels = [...form.querySelectorAll("[data-step]")];
  const tabs = [...form.querySelectorAll("[data-step-tab]")];
  const field = (name) => form.elements.namedItem(name);
  const locale = document.documentElement.lang || "de";
  const number = new Intl.NumberFormat(locale, { maximumFractionDigits: 1 });
  const euros = new Intl.NumberFormat(locale, { style: "currency", currency: "EUR", minimumFractionDigits: 0, maximumFractionDigits: 2 });
  let step = 0;
  let acceptedData = null;
  let controller = null;
  let revision = 0;

  function showStep(index, focus = false) {
    step = index;
    panels.forEach((panel, i) => { panel.hidden = i !== step; });
    tabs.forEach((tab, i) => {
      if (i === step) tab.setAttribute("aria-current", "step");
      else tab.removeAttribute("aria-current");
      tab.classList.toggle("is-complete", i < step);
    });
    ui("calculatorBack").hidden = step === 0;
    ui("calculatorNext").hidden = step === panels.length - 1;
    ui("calculatorSubmit").hidden = step !== panels.length - 1;
    if (focus) {
      const target = panels[step].querySelector("input, select, textarea");
      target?.focus({ preventScroll: true });
      form.scrollIntoView({ behavior: "auto", block: "start" });
    }
  }

  function validateStep(index) {
    const inventoryMode = field("inventory_mode").value === "items";
    const inputs = [...panels[index].querySelectorAll("input, select, textarea")];
    const invalid = inputs.find((input) => {
      if (input.dataset.item && !inventoryMode) return false;
      return !input.checkValidity();
    });
    if (invalid) {
      showStep(index);
      invalid.classList.add("is-error");
      invalid.reportValidity();
      ui("calculatorStatus").textContent = messages.invalid;
      return false;
    }
    if (index === 2 && inventoryMode && ![...form.querySelectorAll("[data-item]")].some((input) => Number(input.value) > 0)) {
      showStep(index);
      ui("calculatorStatus").textContent = messages.empty_items;
      form.querySelector("[data-item]").focus();
      return false;
    }
    return true;
  }

  function updateSummary() {
    const distance = field("distance").value;
    ui("calculatorSummaryDistance").textContent = distance !== "" && field("distance").validity.valid ? number.format(Number(distance)) + " km" : "—";
    const rooms = field("rooms").value;
    const area = field("area").value;
    ui("calculatorSummaryHome").textContent = rooms && area ? `${rooms} ${messages.rooms} · ${area} m²` : "—";
    ui("calculatorSummaryTeam").textContent = messages.services[field("service").value];
    ui("calculatorInventory").hidden = field("inventory_mode").value !== "items";
  }

  function detach() {
    ui("contactCalculatorData").value = "";
    ui("contactCalculatorAttached").hidden = true;
  }

  function invalidate() {
    revision += 1;
    if (controller) controller.abort();
    controller = null;
    ui("calculatorSubmit").disabled = false;
    form.removeAttribute("aria-busy");
    const hadResult = acceptedData !== null;
    acceptedData = null;
    detach();
    ui("calculatorRequest").hidden = true;
    ui("calculatorEstimateDetails").hidden = true;
    ui("calculatorReview").hidden = true;
    ui("calculatorPrice").textContent = "—";
    ui("calculatorPriceCaption").textContent = hadResult ? messages.changed : messages.initial;
    ui("calculatorStatus").textContent = "";
    updateSummary();
  }

  function payload() {
    const data = {};
    for (const name of ["from_place", "to_place", "occupancy", "service", "inventory_mode", "other_items", "from_lift", "to_lift", "from_parking", "to_parking"]) {
      data[name] = field(name).value;
    }
    for (const name of ["distance", "rooms", "area", "from_floor", "to_floor"]) data[name] = Number(field(name).value);
    data.items = {};
    for (const input of form.querySelectorAll("[data-item]")) {
      data.items[input.dataset.item] = data.inventory_mode === "items" ? Number(input.value) : 0;
    }
    return data;
  }

  form.addEventListener("input", (event) => {
    event.target.classList.remove("is-error");
    invalidate();
  });
  form.addEventListener("change", invalidate);
  form.querySelectorAll("[data-counter]").forEach((button) => {
    button.addEventListener("click", () => {
      const input = ui("calc-item-" + button.dataset.counter);
      const current = Number(input.value) || 0;
      input.value = Math.min(Number(input.max), Math.max(0, current + Number(button.dataset.delta)));
      input.dispatchEvent(new Event("input", { bubbles: true }));
    });
  });
  ui("calculatorNext").addEventListener("click", () => {
    if (validateStep(step)) {
      ui("calculatorStatus").textContent = "";
      showStep(step + 1, true);
    }
  });
  ui("calculatorBack").addEventListener("click", () => showStep(step - 1, true));
  tabs.forEach((tab, index) => tab.addEventListener("click", () => {
    if (index > step) {
      for (let i = 0; i < index; i += 1) if (!validateStep(i)) return;
    }
    showStep(index, true);
  }));

  form.addEventListener("submit", async (event) => {
    event.preventDefault();
    if (step < panels.length - 1) {
      ui("calculatorNext").click();
      return;
    }
    if (controller) return;
    for (let i = 0; i < panels.length; i += 1) if (!validateStep(i)) return;
    const data = payload();
    const requestRevision = revision;
    const requestController = new AbortController();
    controller = requestController;
    const timeout = setTimeout(() => requestController.abort(), 20000);
    ui("calculatorSubmit").disabled = true;
    form.setAttribute("aria-busy", "true");
    ui("calculatorStatus").textContent = messages.busy;
    try {
      const response = await fetch(form.action, {
        method: "POST",
        headers: { "Content-Type": "application/json", "X-CSRFToken": field("csrf_token").value },
        body: JSON.stringify(data), signal: requestController.signal, credentials: "same-origin"
      });
      const result = await response.json();
      if (requestRevision !== revision) return;
      if (!response.ok || !result.ok) {
        const message = response.status === 429 ? messages.rate_limit : result.errors?.csrf_token ? messages.expired : messages.invalid;
        throw new Error(message);
      }
      const estimate = result.estimate;
      acceptedData = data;
      ui("calculatorPrice").textContent = estimate.price_low === null ? messages.on_request : euros.format(estimate.price_low) + " – " + euros.format(estimate.price_high);
      ui("calculatorPriceCaption").textContent = estimate.price_low === null ? messages.driver_note : messages.range;
      ui("calculatorVolume").textContent = "≈ " + number.format(estimate.volume_m3) + " m³";
      ui("calculatorTrips").textContent = number.format(estimate.trips);
      ui("calculatorHours").textContent = estimate.hours_low === null ? "—" : `${number.format(estimate.hours_low)}–${number.format(estimate.hours_high)} ${messages.hours}`;
      ui("calculatorEstimateDetails").hidden = false;
      ui("calculatorReview").hidden = !estimate.manual_review;
      ui("calculatorRequest").hidden = false;
      ui("calculatorStatus").textContent = "";
      ui("calculatorResultTitle").focus({ preventScroll: true });
      ui("calculatorResultTitle").scrollIntoView({ behavior: "auto", block: "center" });
    } catch (error) {
      if (requestRevision === revision) {
        ui("calculatorStatus").textContent = [messages.invalid, messages.expired, messages.rate_limit].includes(error.message) ? error.message : messages.network;
      }
    } finally {
      clearTimeout(timeout);
      if (controller === requestController) {
        controller = null;
        ui("calculatorSubmit").disabled = false;
        form.removeAttribute("aria-busy");
      }
    }
  });

  ui("calculatorRequest").addEventListener("click", () => {
    if (!acceptedData) return;
    ui("contactCalculatorData").value = JSON.stringify(acceptedData);
    ui("contactCalculatorNote").textContent = messages.attached;
    ui("contactCalculatorAttached").hidden = false;
    ui("kontakt").scrollIntoView({ behavior: "auto", block: "start" });
    ui("name").focus({ preventScroll: true });
  });
  ui("contactCalculatorRemove").addEventListener("click", detach);
  ui("contactForm").addEventListener("reset", detach);
  showStep(0);
  updateSummary();
  ui("calculatorInteractive").hidden = false;
})();
