"use strict";

const config = JSON.parse(document.getElementById("site-config").textContent);
const root = document.documentElement;

const themeVariables = {
  background: "--bg",
  background_deep: "--bg-deep",
  card: "--card",
  text: "--text",
  heading: "--heading",
  primary: "--primary",
  primary_dark: "--primary-dark",
  secondary: "--secondary",
};
Object.entries(config.theme).forEach(([name, value]) => {
  if (themeVariables[name]) root.style.setProperty(themeVariables[name], value);
});

const screens = [...document.querySelectorAll(".screen")];
const progressDots = [...document.querySelectorAll(".progress-dot")];
const noButton = document.getElementById("no-button");
const yesButton = document.getElementById("yes-button");
const dodgeMessage = document.getElementById("dodge-message");
const scheduleForm = document.getElementById("schedule-form");
const dateInput = document.getElementById("date-input");
const timeInput = document.getElementById("time-input");
const foodOptions = [...document.querySelectorAll(".food-option")];
const foodNext = document.getElementById("food-next");
const feeButton = document.getElementById("fee-button");
const restartButton = document.getElementById("restart-button");

const state = {
  step: 0,
  selectedDate: "",
  selectedTime: "",
  selectedFood: "",
  feeAmount: null,
  feeCurrency: "USD",
  feeSymbol: config.fee.currency_symbol,
  feeToken: "",
  dodgeCount: 0,
};

function todayInLocalTime() {
  const now = new Date();
  now.setMinutes(now.getMinutes() - now.getTimezoneOffset());
  return now.toISOString().slice(0, 10);
}

dateInput.min = todayInLocalTime();

function showStep(step) {
  const nextStep = Math.max(0, Math.min(step, screens.length - 1));
  state.step = nextStep;

  screens.forEach((screen, index) => {
    screen.classList.toggle("active", index === nextStep);
    screen.setAttribute("aria-hidden", index === nextStep ? "false" : "true");
  });

  progressDots.forEach((dot, index) => {
    dot.classList.toggle("active", index === nextStep);
    dot.classList.toggle("complete", index < nextStep);
  });

  if (nextStep !== 0) resetNoButton();
  if (nextStep === 4) updateReadyMessage();
  if (nextStep === 5 && state.feeAmount === null) loadFee();
  if (nextStep === 6) updateSummary();

  window.scrollTo({ top: 0, behavior: "smooth" });
  const heading = screens[nextStep].querySelector("h1, h2");
  if (heading) {
    heading.setAttribute("tabindex", "-1");
    heading.focus({ preventScroll: true });
  }
}

function resetNoButton() {
  noButton.style.position = "";
  noButton.style.left = "";
  noButton.style.top = "";
  noButton.style.zIndex = "";
  noButton.style.transform = "";
}

function overlaps(rectA, rectB, padding = 18) {
  return !(
    rectA.right + padding < rectB.left ||
    rectA.left - padding > rectB.right ||
    rectA.bottom + padding < rectB.top ||
    rectA.top - padding > rectB.bottom
  );
}

function dodgeNoButton(event) {
  if (state.step !== 0) return;
  if (event?.cancelable) event.preventDefault();

  state.dodgeCount += 1;
  const messages = config.proposal.dodge_messages;
  dodgeMessage.textContent = messages[(state.dodgeCount - 1) % messages.length];

  const buttonRect = noButton.getBoundingClientRect();
  const yesRect = yesButton.getBoundingClientRect();
  const margin = 14;
  const maxLeft = Math.max(margin, window.innerWidth - buttonRect.width - margin);
  const maxTop = Math.max(margin, window.innerHeight - buttonRect.height - margin);
  let left = margin;
  let top = margin;

  for (let attempt = 0; attempt < 30; attempt += 1) {
    const candidateLeft = margin + Math.random() * Math.max(1, maxLeft - margin);
    const candidateTop = margin + Math.random() * Math.max(1, maxTop - margin);
    const candidate = {
      left: candidateLeft,
      top: candidateTop,
      right: candidateLeft + buttonRect.width,
      bottom: candidateTop + buttonRect.height,
    };
    if (!overlaps(candidate, yesRect, 28)) {
      left = candidateLeft;
      top = candidateTop;
      break;
    }
  }

  noButton.style.position = "fixed";
  noButton.style.zIndex = "40";
  noButton.style.left = `${Math.round(left)}px`;
  noButton.style.top = `${Math.round(top)}px`;
  noButton.style.transform = `rotate(${Math.round(Math.random() * 10 - 5)}deg)`;
}

["pointerenter", "pointerdown", "focus", "click"].forEach((eventName) => {
  noButton.addEventListener(eventName, dodgeNoButton, { passive: false });
});

yesButton.addEventListener("click", () => {
  launchConfetti();
  showStep(1);
});

document.querySelectorAll(".next-button").forEach((button) => {
  button.addEventListener("click", () => showStep(state.step + 1));
});

scheduleForm.addEventListener("submit", (event) => {
  event.preventDefault();
  const error = document.getElementById("schedule-error");
  error.textContent = "";

  if (!dateInput.value || dateInput.value < dateInput.min) {
    error.textContent = "Please choose today or a future date.";
    dateInput.focus();
    return;
  }
  if (!timeInput.value) {
    error.textContent = "Please choose a time.";
    timeInput.focus();
    return;
  }

  state.selectedDate = dateInput.value;
  state.selectedTime = timeInput.value;
  showStep(3);
});

foodOptions.forEach((option) => {
  option.addEventListener("click", () => {
    state.selectedFood = option.dataset.food;
    foodOptions.forEach((item) => item.setAttribute("aria-checked", item === option ? "true" : "false"));
    foodNext.disabled = false;
    document.getElementById("food-error").textContent = "";
  });
});

foodNext.addEventListener("click", () => {
  if (!state.selectedFood) {
    document.getElementById("food-error").textContent = "Pick one delicious option first.";
    return;
  }
  showStep(4);
});

function formatDate(value) {
  return new Intl.DateTimeFormat(undefined, {
    weekday: "long",
    year: "numeric",
    month: "long",
    day: "numeric",
    timeZone: "UTC",
  }).format(new Date(`${value}T00:00:00Z`));
}

function formatTime(value) {
  const match = config.schedule.time_options.find((item) => item.value === value);
  return match ? match.label : value;
}

function updateReadyMessage() {
  const message = config.confirmation.message_template
    .replace("{time}", formatTime(state.selectedTime))
    .replace("{date}", formatDate(state.selectedDate));
  document.getElementById("ready-message").textContent = message;
}

async function loadFee() {
  feeButton.disabled = true;
  try {
    const response = await fetch("/api/fee", { headers: { Accept: "application/json" } });
    if (!response.ok) throw new Error("Fee service unavailable");
    const data = await response.json();
    state.feeAmount = data.amount;
    state.feeCurrency = data.currency;
    state.feeSymbol = data.symbol;
    state.feeToken = data.token;
  } catch (_error) {
    state.feeAmount = 499;
    state.feeCurrency = "USD";
    state.feeSymbol = config.fee.currency_symbol;
    state.feeToken = "offline-fallback";
  }

  const label = `${state.feeSymbol}${state.feeAmount}`;
  document.getElementById("fee-display").textContent = label;
  feeButton.textContent = config.fee.button_template
    .replace("{symbol}", state.feeSymbol)
    .replace("{amount}", state.feeAmount);
  feeButton.disabled = false;
}

feeButton.addEventListener("click", async () => {
  feeButton.disabled = true;
  feeButton.textContent = "confirming our totally official agreement...";

  let saved = false;
  try {
    const response = await fetch("/api/responses", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        "X-Requested-With": "ProposalWebsite",
      },
      body: JSON.stringify({
        selected_date: state.selectedDate,
        selected_time: state.selectedTime,
        food: state.selectedFood,
        fee_amount: state.feeAmount,
        fee_token: state.feeToken,
        accepted: true,
      }),
    });
    saved = response.ok;
  } catch (_error) {
    saved = false;
  }

  document.getElementById("save-status").textContent = saved
    ? "Your answer was saved successfully. 💗"
    : "Your date is set on this screen, but the server could not save a copy.";
  launchConfetti(90);
  showStep(6);
});

function updateSummary() {
  const summary = document.getElementById("date-summary");
  summary.replaceChildren();
  const lines = [
    ["When", `${formatDate(state.selectedDate)} at ${formatTime(state.selectedTime)}`],
    ["Food", state.selectedFood],
    ["Playful fee", `${state.feeSymbol}${state.feeAmount} (not real, obviously)`],
  ];

  lines.forEach(([label, value]) => {
    const row = document.createElement("div");
    const strong = document.createElement("strong");
    strong.textContent = `${label}: `;
    row.append(strong, document.createTextNode(value));
    summary.append(row);
  });
}

function launchConfetti(count = 70) {
  const container = document.getElementById("confetti");
  const colors = ["#d56891", "#f3b5c8", "#a976d2", "#f7c85e", "#7fc7a6"];
  for (let index = 0; index < count; index += 1) {
    const piece = document.createElement("i");
    piece.className = "confetti-piece";
    piece.style.left = `${Math.random() * 100}%`;
    piece.style.background = colors[index % colors.length];
    piece.style.animationDelay = `${Math.random() * 0.5}s`;
    piece.style.setProperty("--drift", `${Math.round(Math.random() * 180 - 90)}px`);
    container.append(piece);
    window.setTimeout(() => piece.remove(), 2400);
  }
}

restartButton.addEventListener("click", () => window.location.reload());

window.addEventListener("resize", () => {
  if (state.step === 0 && noButton.style.position === "fixed") dodgeNoButton();
});

showStep(0);
