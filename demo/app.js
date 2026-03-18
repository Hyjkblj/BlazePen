const shell = document.getElementById("demoShell");
const stage = document.getElementById("decisionStage");
const reticle = document.getElementById("reticle");
const statusText = document.getElementById("statusText");
const pressureValue = document.getElementById("pressureValue");
const ghostCursor = document.getElementById("ghostCursor");
const choices = Array.from(document.querySelectorAll(".choice-card"));

let activeIndex = 0;
let confirmedIndex = null;

function setActiveChoice(index) {
  activeIndex = index;
  stage.classList.toggle("is-left", index === 0);
  stage.classList.toggle("is-right", index === 1);
  stage.style.setProperty("--beam-shift", index === 0 ? "-7%" : "7%");

  choices.forEach((choice, choiceIndex) => {
    choice.classList.toggle("is-active", choiceIndex === index);
    choice.style.setProperty("--choice-scale", choiceIndex === index ? "1.05" : "0.96");
    choice.style.opacity = choiceIndex === index ? "1" : "0.72";
  });

  if (confirmedIndex === null) {
    statusText.textContent = index === 0 ? "聚焦左侧" : "聚焦右侧";
    pressureValue.textContent = index === 0 ? "68%" : "81%";
  }
}

function confirmChoice(index) {
  confirmedIndex = index;
  stage.classList.add("is-confirmed");
  statusText.textContent = index === 0 ? "已锁定：能放弃" : "已锁定：我不知道";

  choices.forEach((choice, choiceIndex) => {
    choice.classList.toggle("is-confirmed", choiceIndex === index);
    choice.style.opacity = choiceIndex === index ? "1" : "0.34";
    choice.style.filter = choiceIndex === index ? "saturate(1.18)" : "blur(0.5px)";
    choice.style.setProperty("--choice-scale", choiceIndex === index ? "1.08" : "0.92");
  });
}

function updateReticle(clientX, clientY) {
  const rect = stage.getBoundingClientRect();
  const x = ((clientX - rect.left) / rect.width) * 100;
  const y = ((clientY - rect.top) / rect.height) * 100;

  stage.style.setProperty("--reticle-x", `${Math.max(8, Math.min(92, x))}%`);
  stage.style.setProperty("--reticle-y", `${Math.max(18, Math.min(82, y))}%`);
  shell.style.setProperty("--cursor-x", `${clientX}px`);
  shell.style.setProperty("--cursor-y", `${clientY}px`);
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
  ghostCursor.style.opacity = "0.92";
});

stage.addEventListener("mouseleave", () => {
  ghostCursor.style.opacity = "0.45";
  stage.style.setProperty("--reticle-x", "50%");
  stage.style.setProperty("--reticle-y", "50%");
});

window.addEventListener("keydown", (event) => {
  if (event.key === "ArrowLeft" || event.key.toLowerCase() === "a") {
    if (confirmedIndex === null) {
      setActiveChoice(0);
    }
  }

  if (event.key === "ArrowRight" || event.key.toLowerCase() === "d") {
    if (confirmedIndex === null) {
      setActiveChoice(1);
    }
  }

  if (event.key === "Enter" || event.key === " ") {
    event.preventDefault();
    if (confirmedIndex === null) {
      confirmChoice(activeIndex);
    } else {
      confirmedIndex = null;
      stage.classList.remove("is-confirmed");
      choices.forEach((choice) => {
        choice.classList.remove("is-confirmed");
        choice.style.filter = "";
      });
      setActiveChoice(activeIndex);
    }
  }

  if (event.key === "Escape") {
    confirmedIndex = null;
    stage.classList.remove("is-confirmed");
    choices.forEach((choice) => {
      choice.classList.remove("is-confirmed");
      choice.style.filter = "";
    });
    statusText.textContent = "待选择";
    setActiveChoice(activeIndex);
  }
});

setActiveChoice(0);
