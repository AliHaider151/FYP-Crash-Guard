const cameraSelect = document.getElementById("camera");
const cameraDetails = document.getElementById("cameraDetails");
const layout = document.querySelector(".layout");
const startButton = document.getElementById("startButton");
const stopButton = document.getElementById("stopButton");
const statusText = document.getElementById("statusText");
const statusDot = document.getElementById("statusDot");
const message = document.getElementById("message");
const previewImage = document.getElementById("previewImage");
const placeholder = document.getElementById("placeholder");
const csrfToken = document.querySelector("[name=csrfmiddlewaretoken]").value;
let previewUrl = null;

function setRunning(running) {
  startButton.disabled = running;
  cameraSelect.disabled = running;
  stopButton.disabled = !running;
  if (!running) {
    previewImage.hidden = true;
    previewImage.removeAttribute("src");
    placeholder.hidden = false;
    if (previewUrl) {
      URL.revokeObjectURL(previewUrl);
      previewUrl = null;
    }
  }
}

function showStatus(state) {
  statusText.textContent = state.status;
  statusDot.classList.toggle("running", state.running);
  statusDot.classList.toggle("alert", state.status.includes("Accident"));
  setRunning(state.running);
  if (state.error) {
    message.textContent = state.error;
  } else if (!state.running && state.status !== "Status: Error") {
    message.textContent = "";
  }
}

async function refreshStatus() {
  try {
    const response = await fetch(layout.dataset.statusUrl);
    if (!response.ok) {
      throw new Error("Could not retrieve detection status.");
    }
    showStatus(await response.json());
  } catch (error) {
    message.textContent = error.message;
  }
}

async function postAction(url, data = {}) {
  const body = new URLSearchParams(data);
  const response = await fetch(url, {
    method: "POST",
    headers: {
      "Content-Type": "application/x-www-form-urlencoded",
      "X-CSRFToken": csrfToken,
    },
    body,
  });
  const result = await response.json();
  if (!response.ok) {
    throw new Error(result.error || "The detection request failed.");
  }
  return result;
}

cameraSelect.addEventListener("change", () => {
  const option = cameraSelect.selectedOptions[0];
  const location = option.dataset.location;
  const latitude = option.dataset.latitude;
  const longitude = option.dataset.longitude;
  const video = option.dataset.video;
  cameraDetails.innerHTML = "";
  for (const [value, strong] of [
    [location, true],
    [`${latitude}, ${longitude}`, false],
    [video, false],
  ]) {
    const line = document.createElement(strong ? "strong" : "span");
    line.textContent = value;
    cameraDetails.append(line);
  }
});

startButton.addEventListener("click", async () => {
  message.textContent = "";
  try {
    await postAction(layout.dataset.startUrl, { camera: cameraSelect.value });
    previewUrl = layout.dataset.previewUrl + "?t=" + Date.now();
    previewImage.src = previewUrl;
    previewImage.hidden = false;
    placeholder.hidden = true;
    await refreshStatus();
  } catch (error) {
    message.textContent = error.message;
    await refreshStatus();
  }
});

stopButton.addEventListener("click", async () => {
  message.textContent = "";
  try {
    await postAction(layout.dataset.stopUrl);
    await refreshStatus();
  } catch (error) {
    message.textContent = error.message;
  }
});

setInterval(refreshStatus, 1000);
refreshStatus();
