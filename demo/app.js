const shell = document.getElementById("demoShell");
const stage = document.getElementById("decisionStage");
const statusText = document.getElementById("statusText");
const ghostCursor = document.getElementById("ghostCursor");
const choices = Array.from(document.querySelectorAll(".choice-card"));

const defaultReticle = {
  x: 50,
  y: 58,
};

let activeIndex = 1;
let confirmedIndex = null;

function clampIndex(index) {
  return Math.max(0, Math.min(choices.length - 1, index));
}

function setStageDirection(index) {
  stage.classList.remove("is-left", "is-center", "is-right");

  if (index === 0) {
    stage.classList.add("is-left");
    return;
  }

  if (index === choices.length - 1) {
    stage.classList.add("is-right");
    return;
  }

  stage.classList.add("is-center");
}

function syncChoicePresentation() {
  choices.forEach((choice, index) => {
    const isActive = index === activeIndex;
    const isConfirmed = index === confirmedIndex;

    choice.classList.toggle("is-active", isActive);
    choice.classList.toggle("is-confirmed", isConfirmed);
    choice.classList.toggle("is-dimmed", confirmedIndex !== null && !isConfirmed);

    if (confirmedIndex !== null) {
      choice.style.opacity = isConfirmed ? "1" : "0.28";
      choice.style.filter = isConfirmed ? "saturate(1.12)" : "blur(0.4px) saturate(0.76)";
      choice.style.setProperty("--choice-scale", isConfirmed ? "1.05" : "0.92");
      return;
    }

    choice.style.opacity = isActive ? "1" : index === 1 ? "0.78" : "0.7";
    choice.style.filter = isActive ? "saturate(1.08)" : "saturate(0.9)";
    choice.style.setProperty("--choice-scale", isActive ? (index === 1 ? "1.02" : "1.04") : "0.94");
  });
}

function setActiveChoice(index) {
  activeIndex = clampIndex(index);
  setStageDirection(activeIndex);

  const currentChoice = choices[activeIndex];
  stage.style.setProperty("--beam-shift", currentChoice.dataset.beamShift || "0%");

  syncChoicePresentation();

  if (confirmedIndex === null) {
    statusText.textContent = currentChoice.dataset.status || "聚焦中央主选项";
  }
}

function confirmChoice(index) {
  confirmedIndex = clampIndex(index);
  const currentChoice = choices[confirmedIndex];
  const title = currentChoice.querySelector(".choice-title")?.textContent?.trim() || "当前选项";

  stage.classList.add("is-confirmed");
  statusText.textContent = `已锁定：${title}`;

  setActiveChoice(confirmedIndex);
}

function clearConfirmation() {
  confirmedIndex = null;
  stage.classList.remove("is-confirmed");
  setActiveChoice(activeIndex);
}

function updateReticle(clientX, clientY) {
  const rect = stage.getBoundingClientRect();
  const xRatio = (clientX - rect.left) / rect.width - 0.5;
  const yRatio = (clientY - rect.top) / rect.height - 0.5;

  const reticleX = defaultReticle.x + xRatio * 8;
  const reticleY = defaultReticle.y + yRatio * 6;

  stage.style.setProperty("--reticle-x", `${Math.max(42, Math.min(58, reticleX))}%`);
  stage.style.setProperty("--reticle-y", `${Math.max(52, Math.min(64, reticleY))}%`);
  shell.style.setProperty("--cursor-x", `${clientX}px`);
  shell.style.setProperty("--cursor-y", `${clientY}px`);
}

function resetReticle() {
  stage.style.setProperty("--reticle-x", `${defaultReticle.x}%`);
  stage.style.setProperty("--reticle-y", `${defaultReticle.y}%`);
}

choices.forEach((choice, index) => {
  choice.addEventListener("mouseenter", () => {
    if (confirmedIndex !== null) {
      return;
    }

    setActiveChoice(index);
  });

  choice.addEventListener("focus", () => {
    if (confirmedIndex !== null) {
      return;
    }

    setActiveChoice(index);
  });

  choice.addEventListener("click", () => {
    setActiveChoice(index);
    confirmChoice(index);
  });
});

stage.addEventListener("mousemove", (event) => {
  updateReticle(event.clientX, event.clientY);
  ghostCursor.style.opacity = "0.88";
});

stage.addEventListener("mouseleave", () => {
  ghostCursor.style.opacity = "0.4";
  resetReticle();
});

window.addEventListener("keydown", (event) => {
  const key = event.key.toLowerCase();

  if ((event.key === "ArrowLeft" || key === "a") && confirmedIndex === null) {
    setActiveChoice(activeIndex - 1);
  }

  if ((event.key === "ArrowRight" || key === "d") && confirmedIndex === null) {
    setActiveChoice(activeIndex + 1);
  }

  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();

    if (confirmedIndex === null) {
      confirmChoice(activeIndex);
    } else {
      clearConfirmation();
    }
  }

  if (event.key === "Escape") {
    clearConfirmation();
  }
});

resetReticle();
setActiveChoice(activeIndex);
