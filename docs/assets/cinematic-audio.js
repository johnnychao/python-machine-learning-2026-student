(function () {
  "use strict";

  const CONFIG = Object.freeze({
    masterGain: 0.032,
    fadeInSeconds: 1.6,
    fadeOutSeconds: 0.28,
    noiseSeconds: 4,
    sceneFilterHz: 520,
    filterModulationHz: 55,
    lfoHz: 0.035,
    tones: Object.freeze([
      { frequency: 73.42, gain: 0.34, detune: -3 },
      { frequency: 110, gain: 0.18, detune: 2 },
      { frequency: 146.83, gain: 0.06, detune: -2 },
    ]),
  });

  const controls = Array.from(document.querySelectorAll("[data-sound-toggle]"));
  const status = document.querySelector("#sound-status");
  const AudioContextClass = window.AudioContext || window.webkitAudioContext;

  if (!controls.length || !status) return;

  let context = null;
  let master = null;
  let sourceNodes = [];
  let allNodes = new Set();
  let userEnabled = false;
  let needsGesture = false;
  let disposed = false;
  let transitionToken = 0;
  let fadeTimer = 0;
  let graphBuilds = 0;

  function labelsFor(mode, control) {
    const isHeader = control.id === "sound-toggle";
    const labels = {
      off: isHeader ? "配樂：關閉" : "播放電影配樂",
      starting: "配樂啟動中…",
      on: "配樂：播放中",
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
      control.setAttribute("aria-label", pressed ? "暫停電影氛圍背景配樂" : visibleLabel);
      if (label) label.textContent = visibleLabel;
      if (mode === "starting") control.setAttribute("aria-busy", "true");
      else control.removeAttribute("aria-busy");
    });

    if (message) status.textContent = message;
  }

  if (!AudioContextClass) {
    controls.forEach((control) => { control.disabled = true; });
    setUi("unsupported", "此瀏覽器不支援 Web Audio 背景配樂。");
    return;
  }

  function createContext() {
    try {
      return new AudioContextClass({ latencyHint: "playback" });
    } catch (error) {
      return new AudioContextClass();
    }
  }

  function createNoiseBuffer(audioContext) {
    const length = Math.floor(audioContext.sampleRate * CONFIG.noiseSeconds);
    const buffer = audioContext.createBuffer(1, length, audioContext.sampleRate);
    const samples = buffer.getChannelData(0);
    let seed = 0x51f15e;

    for (let index = 0; index < samples.length; index += 1) {
      seed ^= seed << 13;
      seed ^= seed >>> 17;
      seed ^= seed << 5;
      samples[index] = ((seed >>> 0) / 4294967295) * 2 - 1;
    }

    return buffer;
  }

  function registerNode(node) {
    allNodes.add(node);
    return node;
  }

  function registerSource(node) {
    sourceNodes.push(node);
    allNodes.add(node);
    return node;
  }

  function ensureGraph() {
    if (context && context.state !== "closed") return;

    context = createContext();
    sourceNodes = [];
    allNodes = new Set();

    const now = context.currentTime;
    const mix = registerNode(context.createGain());
    const sceneFilter = registerNode(context.createBiquadFilter());
    const compressor = registerNode(context.createDynamicsCompressor());
    master = registerNode(context.createGain());

    sceneFilter.type = "lowpass";
    sceneFilter.frequency.setValueAtTime(CONFIG.sceneFilterHz, now);
    sceneFilter.Q.setValueAtTime(0.45, now);

    compressor.threshold.setValueAtTime(-24, now);
    compressor.knee.setValueAtTime(18, now);
    compressor.ratio.setValueAtTime(4, now);
    compressor.attack.setValueAtTime(0.08, now);
    compressor.release.setValueAtTime(0.8, now);
    master.gain.setValueAtTime(0, now);

    CONFIG.tones.forEach((tone) => {
      const oscillator = registerSource(context.createOscillator());
      const gain = registerNode(context.createGain());
      oscillator.type = "sine";
      oscillator.frequency.setValueAtTime(tone.frequency, now);
      oscillator.detune.setValueAtTime(tone.detune, now);
      gain.gain.setValueAtTime(tone.gain, now);
      oscillator.connect(gain).connect(mix);
    });

    const noise = registerSource(context.createBufferSource());
    const noiseHighPass = registerNode(context.createBiquadFilter());
    const noiseLowPass = registerNode(context.createBiquadFilter());
    const noiseGain = registerNode(context.createGain());
    noise.buffer = createNoiseBuffer(context);
    noise.loop = true;
    noiseHighPass.type = "highpass";
    noiseHighPass.frequency.setValueAtTime(65, now);
    noiseLowPass.type = "lowpass";
    noiseLowPass.frequency.setValueAtTime(360, now);
    noiseGain.gain.setValueAtTime(0.04, now);
    noise.connect(noiseHighPass).connect(noiseLowPass).connect(noiseGain).connect(mix);

    const lfo = registerSource(context.createOscillator());
    const modulationDepth = registerNode(context.createGain());
    lfo.type = "sine";
    lfo.frequency.setValueAtTime(CONFIG.lfoHz, now);
    modulationDepth.gain.setValueAtTime(CONFIG.filterModulationHz, now);
    lfo.connect(modulationDepth).connect(sceneFilter.frequency);

    mix.connect(sceneFilter).connect(compressor).connect(master).connect(context.destination);
    sourceNodes.forEach((source) => source.start(now));
    graphBuilds += 1;
  }

  function cancelFadeTimer() {
    if (!fadeTimer) return;
    window.clearTimeout(fadeTimer);
    fadeTimer = 0;
  }

  function rampMaster(target, seconds) {
    if (!context || !master) return;
    const now = context.currentTime;
    const parameter = master.gain;
    const current = parameter.value;
    parameter.cancelScheduledValues(now);
    parameter.setValueAtTime(current, now);
    parameter.linearRampToValueAtTime(Math.min(Math.max(target, 0), 0.06), now + seconds);
  }

  function setMasterImmediately(value) {
    if (!context || !master) return;
    const now = context.currentTime;
    master.gain.cancelScheduledValues(now);
    master.gain.setValueAtTime(value, now);
  }

  async function resumeAudio() {
    const token = ++transitionToken;
    cancelFadeTimer();
    if (disposed || !userEnabled || document.hidden) return;

    try {
      ensureGraph();
      if (context.state !== "running") await context.resume();
      if (token !== transitionToken || disposed || !userEnabled || document.hidden) return;
      needsGesture = false;
      rampMaster(CONFIG.masterGain, CONFIG.fadeInSeconds);
      setUi("on", "電影氛圍背景配樂已播放，音量偏低。");
    } catch (error) {
      if (token !== transitionToken || disposed) return;
      userEnabled = false;
      needsGesture = true;
      setUi("error", "瀏覽器未能啟動背景配樂，請點一下重試。");
    }
  }

  function softSuspend() {
    const token = ++transitionToken;
    cancelFadeTimer();
    if (!context || !master) return;

    if (context.state !== "running") {
      setMasterImmediately(0);
      return;
    }

    rampMaster(0, CONFIG.fadeOutSeconds);
    fadeTimer = window.setTimeout(() => {
      fadeTimer = 0;
      if (token !== transitionToken || disposed || !context) return;
      context.suspend().catch(() => undefined);
    }, CONFIG.fadeOutSeconds * 1000 + 40);
  }

  function hardSuspend() {
    ++transitionToken;
    cancelFadeTimer();
    setMasterImmediately(0);
    if (context?.state === "running") context.suspend().catch(() => undefined);
  }

  function handleToggle() {
    if (userEnabled && needsGesture) {
      setUi("starting", "正在恢復背景配樂。");
      void resumeAudio();
      return;
    }

    if (userEnabled) {
      userEnabled = false;
      needsGesture = false;
      setUi("off", "背景配樂已靜音。");
      softSuspend();
      return;
    }

    userEnabled = true;
    needsGesture = false;
    setUi("starting", "正在啟動背景配樂。");
    void resumeAudio();
  }

  function handleVisibilityChange() {
    if (!document.hidden || !userEnabled) return;
    needsGesture = true;
    setUi("paused", "分頁已隱藏，背景配樂已暫停；返回後請點一下繼續。");
    hardSuspend();
  }

  function destroy() {
    if (disposed) return;
    disposed = true;
    userEnabled = false;
    ++transitionToken;
    cancelFadeTimer();

    controls.forEach((control) => control.removeEventListener("click", handleToggle));
    document.removeEventListener("visibilitychange", handleVisibilityChange);
    sourceNodes.forEach((source) => {
      try { source.stop(); } catch (error) { /* Node 已停止。 */ }
    });
    allNodes.forEach((node) => {
      try { node.disconnect(); } catch (error) { /* Node 已斷線。 */ }
    });

    const closingContext = context;
    context = null;
    master = null;
    sourceNodes = [];
    allNodes.clear();
    if (closingContext?.state !== "closed") closingContext.close().catch(() => undefined);
  }

  function handlePageHide(event) {
    if (userEnabled) {
      needsGesture = true;
      setUi("paused", "頁面已離開，背景配樂已暫停；返回後請點一下繼續。");
    }
    hardSuspend();
    if (!event.persisted) destroy();
  }

  controls.forEach((control) => control.addEventListener("click", handleToggle));
  document.addEventListener("visibilitychange", handleVisibilityChange);
  window.addEventListener("pagehide", handlePageHide);
  setUi("off", "背景配樂未播放。");

  window.storyAudio = Object.freeze({
    destroy,
    getState: function () {
      return {
        userEnabled,
        needsGesture,
        contextState: context?.state || "not-created",
        graphBuilds,
        sourceCount: sourceNodes.length,
      };
    },
  });
}());
