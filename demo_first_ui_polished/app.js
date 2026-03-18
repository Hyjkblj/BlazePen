const shell = document.getElementById("demoShell");
const stage = document.getElementById("decisionStage");
const statusText = document.getElementById("statusText");
const pressureValue = document.getElementById("pressureValue");
const ghostCursor = document.getElementById("ghostCursor");
const choices = Array.from(document.querySelectorAll(".choice-card"));

let activeIndex = 0;
let confirmedIndex = null;

function applyChoiceVisuals(index) {
  stage.classList.toggle("is-left", index === 0);
  stage.classList.toggle("is-right", index === 1);
  stage.style.setProperty("--beam-shift", index === 0 ? "-5.5%" : "5.5%");

  choices.forEach((choice, choiceIndex) => {
    const isActive = choiceIndex === index;
    choice.classList.toggle("is-active", isActive);
    choice.style.opacity = isActive ? "1" : "0.76";

    if (window.innerWidth > 980) {
      if (choiceIndex === 0) {
        choice.style.transform = `translateY(-50%) scale(${isActive ? "1.04" : "0.98"})`;
      } else {
        choice.style.transform = `translateY(-50%) scale(${isActive ? "1.04" : "0.98"})`;
      }
    } else {
      const top = choiceIndex === 0 ? "34%" : "66%";
      choice.style.transform = `translate(-50%, -50%) scale(${isActive ? "1.03" : "0.97"})`;
      choice.style.top = top;
    }
  });
}

function setActiveChoice(index) {
  activeIndex = index;
  applyChoiceVisuals(index);

  if (confirmedIndex === null) {
    statusText.textContent = index === 0 ? "聚焦左侧" : "聚焦右侧";
    pressureValue.textContent = index === 0 ? "68%" : "82%";
  }
}

function confirmChoice(index) {
  confirmedIndex = index;
  stage.classList.add("is-confirmed");
  statusText.textContent = index === 0 ? "已锁定：能放弃" : "已锁定：我不知道";
  pressureValue.textContent = index === 0 ? "71%" : "87%";

  choices.forEach((choice, choiceIndex) => {
    const selected = choiceIndex === index;
    choice.classList.toggle("is-confirmed", selected);
    choice.style.opacity = selected ? "1" : "0.3";
    choice.style.filter = selected ? "saturate(1.16)" : "blur(0.8px)";
  });
}

function resetConfirmation() {
  confirmedIndex = null;
  stage.classList.remove("is-confirmed");
  choices.forEach((choice) => {
    choice.classList.remove("is-confirmed");
    choice.style.filter = "";
  });
  setActiveChoice(activeIndex);
}

function updateReticle(clientX, clientY) {
  const rect = stage.getBoundingClientRect();
  const x = ((clientX - rect.left) / rect.width) * 100;
  const y = ((clientY - rect.top) / rect.height) * 100;

  stage.style.setProperty("--reticle-x", `${Math.max(10, Math.min(90, x))}%`);
  stage.style.setProperty("--reticle-y", `${Math.max(18, Math.min(82, y))}%`);
  shell.style.setProperty("--cursor-x", `${clientX}px`);
  shell.style.setProperty("--cursor-y", `${clientY}px`);
}

choices.forEach((choice, index) => {
  choice.addEventListener("mouseenter", () => {
    if (confirmedIndex !== null) return;
    setActiveChoice(index);
  });

  choice.addEventListener("focus", () => {
    if (confirmedIndex !== null) return;
    setActiveChoice(index);
  });

  choice.addEventListener("click", () => {
    setActiveChoice(index);
    confirmChoice(index);
  });
});

stage.addEventListener("mousemove", (event) => {
  updateReticle(event.clientX, event.clientY);
  ghostCursor.style.opacity = "0.94";
});

stage.addEventListener("mouseleave", () => {
  ghostCursor.style.opacity = "0.42";
  stage.style.setProperty("--reticle-x", "50%");
  stage.style.setProperty("--reticle-y", "50%");
});

window.addEventListener("keydown", (event) => {
  const key = event.key.toLowerCase();

  if ((event.key === "ArrowLeft" || key === "a") && confirmedIndex === null) {
    setActiveChoice(0);
  }

  if ((event.key === "ArrowRight" || key === "d") && confirmedIndex === null) {
    setActiveChoice(1);
  }

  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    if (confirmedIndex === null) {
      confirmChoice(activeIndex);
    } else {
      resetConfirmation();
    }
  }

  if (event.key === "Escape") {
    resetConfirmation();
  }
});

setActiveChoice(0);
