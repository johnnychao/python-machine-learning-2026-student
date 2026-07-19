(function () {
  "use strict";

  const CONFIG = Object.freeze({
    targetVolume: 0.34,
    fadeInMs: 650,
    fadeOutMs: 240,
    title: "Snow Globe",
  });

  const controls = Array.from(document.querySelectorAll("[data-sound-toggle]"));
  const status = document.querySelector("#sound-status");
  const audio = document.querySelector("#cinematic-score");

  if (!controls.length || !status || !audio) return;

  let userEnabled = false;
  let needsGesture = false;
  let disposed = false;
  let transitionToken = 0;
  let fadeToken = 0;
  let fadeFrame = 0;
  let playAttempts = 0;

  function labelsFor(mode, control) {
    const isHeader = control.id === "sound-toggle";
    const labels = {
      off: isHeader ? "配樂：關閉" : "播放電影配樂",
      starting: "配樂載入中…",
      on: isHeader ? "配樂：播放中" : "暫停電影配樂",
      paused: "繼續電影配樂",
      error: "重試電影配樂",
      unsupported: "不支援配樂",
    };
    return labels[mode] || labels.off;
  }

  function setUi(mode, message) {
    const pressed = mode === "on";
    document.body.dataset.sound = mode;

    controls.forEach((control) => {
      const label = control.querySelector(".sound-label");
      const visibleLabel = labelsFor(mode, control);
      control.dataset.audioState = mode;
      control.setAttribute("aria-pressed", String(pressed));
      control.setAttribute("aria-label", pressed ? "暫停電影配樂 Snow Globe" : visibleLabel);
      if (label) label.textContent = visibleLabel;
      if (mode === "starting") control.setAttribute("aria-busy", "true");
      else control.removeAttribute("aria-busy");
    });

    if (message) status.textContent = message;
  }

  function cancelFade() {
    fadeToken += 1;
    if (!fadeFrame) return;
    window.cancelAnimationFrame(fadeFrame);
    fadeFrame = 0;
  }

  function fadeTo(target, duration, onComplete) {
    cancelFade();
    const token = fadeToken;
    const startVolume = audio.volume;
    const safeTarget = Math.min(Math.max(target, 0), 1);

    if (duration <= 0 || Math.abs(startVolume - safeTarget) < 0.001) {
      audio.volume = safeTarget;
      if (onComplete) onComplete();
      return;
    }

    const startedAt = performance.now();
    const step = (now) => {
      if (disposed || token !== fadeToken) return;
      const progress = Math.max(0, Math.min((now - startedAt) / duration, 1));
      audio.volume = startVolume + ((safeTarget - startVolume) * progress);

      if (progress < 1) {
        fadeFrame = window.requestAnimationFrame(step);
        return;
      }

      fadeFrame = 0;
      if (onComplete) onComplete();
    };

    fadeFrame = window.requestAnimationFrame(step);
  }

  function mediaErrorMessage() {
    const messages = {
      1: "配樂載入已中止，請再按一次重試。",
      2: "配樂下載失敗，請檢查網路後重試。",
      3: "瀏覽器無法解碼這個配樂檔案。",
      4: "此瀏覽器不支援 MP3 配樂。",
    };
    return messages[audio.error?.code] || "配樂暫時無法播放，請再按一次重試。";
  }

  function hardPause() {
    transitionToken += 1;
    cancelFade();
    audio.volume = 0;
    audio.pause();
  }

  function softPause() {
    const token = ++transitionToken;
    if (audio.paused) {
      cancelFade();
      audio.volume = 0;
      return;
    }

    fadeTo(0, CONFIG.fadeOutMs, () => {
      if (!disposed && token === transitionToken) audio.pause();
    });
  }

  async function startAudio() {
    const token = ++transitionToken;
    cancelFade();
    if (disposed || !userEnabled || document.hidden) return;

    if (audio.ended || (Number.isFinite(audio.duration) && audio.currentTime >= audio.duration - 0.25)) {
      audio.currentTime = 0;
    }

    audio.volume = 0;
    playAttempts += 1;

    try {
      await audio.play();
      if (disposed || token !== transitionToken || !userEnabled || document.hidden) {
        audio.pause();
        return;
      }

      needsGesture = false;
      setUi("on", `電影配樂〈${CONFIG.title}〉已播放。`);
      fadeTo(CONFIG.targetVolume, CONFIG.fadeInMs);
    } catch (error) {
      if (disposed || token !== transitionToken) return;
      userEnabled = false;
      needsGesture = error?.name === "NotAllowedError";
      audio.pause();
      setUi("error", needsGesture ? "瀏覽器需要你再按一次才能播放配樂。" : mediaErrorMessage());
    }
  }

  function handleToggle() {
    if (document.body.dataset.sound === "starting") {
      userEnabled = false;
      needsGesture = false;
      hardPause();
      setUi("off", "已取消載入電影配樂。");
      return;
    }

    if (userEnabled && !needsGesture && !audio.paused) {
      userEnabled = false;
      setUi("off", "電影配樂已暫停。再次播放會從原位置繼續。");
      softPause();
      return;
    }

    userEnabled = true;
    needsGesture = false;
    setUi("starting", `正在載入電影配樂〈${CONFIG.title}〉。`);
    void startAudio();
  }

  function handleVisibilityChange() {
    if (!document.hidden || !userEnabled) return;
    needsGesture = true;
    setUi("paused", "分頁已隱藏，電影配樂已暫停；返回後請點一下繼續。");
    hardPause();
  }

  function handleMediaError() {
    if (disposed) return;
    userEnabled = false;
    needsGesture = false;
    hardPause();
    setUi("error", mediaErrorMessage());
  }

  function handlePageHide(event) {
    if (userEnabled) {
      needsGesture = true;
      setUi("paused", "頁面已離開，電影配樂已暫停；返回後請點一下繼續。");
    }
    hardPause();
    if (!event.persisted) destroy();
  }

  function destroy() {
    if (disposed) return;
    disposed = true;
    userEnabled = false;
    hardPause();
    controls.forEach((control) => control.removeEventListener("click", handleToggle));
    document.removeEventListener("visibilitychange", handleVisibilityChange);
    window.removeEventListener("pagehide", handlePageHide);
    audio.removeEventListener("error", handleMediaError);
  }

  if (typeof audio.play !== "function" || audio.canPlayType("audio/mpeg") === "") {
    controls.forEach((control) => { control.disabled = true; });
    setUi("unsupported", "此瀏覽器不支援 MP3 電影配樂。你仍可正常使用所有教材入口。");
    return;
  }

  audio.loop = true;
  audio.volume = 0;
  controls.forEach((control) => control.addEventListener("click", handleToggle));
  document.addEventListener("visibilitychange", handleVisibilityChange);
  window.addEventListener("pagehide", handlePageHide);
  audio.addEventListener("error", handleMediaError);
  setUi("off", `電影配樂〈${CONFIG.title}〉預設關閉。`);

  window.storyAudio = Object.freeze({
    destroy,
    getState: function () {
      const source = audio.currentSrc || audio.querySelector("source")?.src || "";
      return {
        userEnabled,
        needsGesture,
        paused: audio.paused,
        ended: audio.ended,
        currentTime: audio.currentTime,
        duration: Number.isFinite(audio.duration) ? audio.duration : null,
        volume: audio.volume,
        loop: audio.loop,
        readyState: audio.readyState,
        networkState: audio.networkState,
        source,
        playAttempts,
      };
    },
  });
}());
