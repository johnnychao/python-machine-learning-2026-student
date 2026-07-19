const fs = require("node:fs");
const path = require("node:path");

const baseUrl = process.argv[2] || "http://127.0.0.1:8765";
const playwrightModule = process.argv[3] || "playwright";
const { chromium } = require(playwrightModule);

const repoRoot = path.resolve(__dirname, "..");
const outputDir = path.join(repoRoot, "output", "playwright");
fs.mkdirSync(outputDir, { recursive: true });

const notebookFiles = [
  "00_colab_ready.ipynb",
  "01_cnn_pet_story.ipynb",
  "02_rnn_message_story.ipynb",
  "03_style_transfer_story.ipynb",
  "04_rl_strategy_story.ipynb",
];
const notebookRoot = "notebooks/ai_solution_practicum";
const repoSlug = "johnnychao/python-machine-learning-2026-student";
const expectedColabHrefs = notebookFiles.map((file) => `https://colab.research.google.com/github/${repoSlug}/blob/main/${notebookRoot}/${file}`);
const expectedDownloadHrefs = notebookFiles.map((file) => `https://raw.githubusercontent.com/${repoSlug}/main/${notebookRoot}/${file}`);
const prohibitedFontPattern = /DFKai-SB|BiauKai|KaiTi|標楷體/i;
const checks = [];

function check(name, passed, detail) {
  checks.push({ name, status: passed ? "pass" : "fail", detail });
}

async function inspectViewport(browser, label, viewport) {
  const context = await browser.newContext({ viewport, deviceScaleFactor: 1 });
  const page = await context.newPage();
  const consoleErrors = [];
  const pageErrors = [];
  const badResponses = [];
  const requestFailures = [];

  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("requestfailed", (request) => requestFailures.push(`${request.failure()?.errorText || "failed"} ${request.url()}`));
  page.on("response", (response) => {
    if (response.url().startsWith(baseUrl) && response.status() >= 400) {
      badResponses.push(`${response.status()} ${response.url()}`);
    }
  });

  const response = await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.waitForSelector("#story-list .story-card:nth-child(4)");

  const initialAudio = await page.evaluate(() => ({
    bodyState: document.body.dataset.sound,
    controls: Array.from(document.querySelectorAll("[data-sound-toggle]"), (control) => ({
      tag: control.tagName,
      type: control.getAttribute("type"),
      pressed: control.getAttribute("aria-pressed"),
      disabled: control.disabled,
    })),
    audioElements: document.querySelectorAll("audio").length,
    autoplayElements: document.querySelectorAll("audio[autoplay], video[autoplay]").length,
    engine: window.storyAudio?.getState() || null,
  }));

  const lazyImages = page.locator('img[loading="lazy"]');
  for (let index = 0; index < await lazyImages.count(); index += 1) {
    const image = lazyImages.nth(index);
    await image.scrollIntoViewIfNeeded();
    await image.evaluate((element) => element.decode().catch(() => undefined));
  }
  const revealItems = page.locator(".reveal");
  for (let index = 0; index < await revealItems.count(); index += 1) {
    await revealItems.nth(index).scrollIntoViewIfNeeded();
  }
  await page.keyboard.press("Home");

  const result = await page.evaluate(() => {
    const storyCards = Array.from(document.querySelectorAll("#story-list .story-card"));
    const images = Array.from(document.images).map((image) => ({
      src: image.getAttribute("src"),
      complete: image.complete,
      naturalWidth: image.naturalWidth,
      naturalHeight: image.naturalHeight,
    }));
    const rootStyle = getComputedStyle(document.documentElement);
    const skipLink = document.querySelector(".skip-link");
    const skipRect = skipLink?.getBoundingClientRect();
    const visibleOverflow = Array.from(document.body.querySelectorAll("*:not(.cinema-atmosphere):not(.cinema-atmosphere *):not([aria-hidden=\"true\"]):not([aria-hidden=\"true\"] *)"))
      .filter((element) => {
        const style = getComputedStyle(element);
        const rect = element.getBoundingClientRect();
        return style.display !== "none" && style.visibility !== "hidden" && rect.width > 1 && rect.height > 1;
      })
      .filter((element) => {
        const rect = element.getBoundingClientRect();
        return rect.left < -1 || rect.right > window.innerWidth + 1;
      })
      .slice(0, 12)
      .map((element) => {
        const rect = element.getBoundingClientRect();
        return `${element.tagName}.${element.className || ""}:${rect.left.toFixed(1)}..${rect.right.toFixed(1)}`;
      });
    const tapTargets = Array.from(document.querySelectorAll(".button, .sound-toggle"), (element) => {
      const rect = element.getBoundingClientRect();
      return { text: element.textContent.trim().slice(0, 28), width: rect.width, height: rect.height };
    });
    const fontFamilies = [document.body, document.querySelector("h1"), ...document.querySelectorAll("h2, h3")]
      .filter(Boolean)
      .map((element) => getComputedStyle(element).fontFamily);
    const effectStyle = getComputedStyle(document.querySelector(".film-grain"));

    return {
      title: document.title,
      h1: document.querySelector("h1")?.innerText.trim() || "",
      storyCount: storyCards.length,
      storyIds: storyCards.map((card) => card.id.replace("story-", "")),
      actLabels: storyCards.map((card) => card.dataset.act),
      storyPrimaryCounts: storyCards.map((card) => card.querySelectorAll(".story-actions .button--primary").length),
      colabHrefs: Array.from(document.querySelectorAll("#preflight-colab, .story-actions .button--primary"), (link) => link.href),
      downloadHrefs: Array.from(document.querySelectorAll("#preflight-local, .story-actions a[download]"), (link) => link.href),
      bodyText: document.body.innerText,
      bodyClass: document.body.className,
      sceneCount: document.querySelectorAll(".scene[data-scene]").length,
      atmosphere: Boolean(document.querySelector(".cinema-atmosphere .film-grain")),
      images,
      heroRatio: (() => {
        const rect = document.querySelector(".hero-visual > img").getBoundingClientRect();
        return Number((rect.width / rect.height).toFixed(3));
      })(),
      storyRatios: Array.from(document.querySelectorAll(".story-figure > img"), (image) => {
        const rect = image.getBoundingClientRect();
        return Number((rect.width / rect.height).toFixed(3));
      }),
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
      visibleOverflow,
      tapTargets,
      fontFamilies,
      effectAnimation: effectStyle.animationName,
      skipLink: {
        focused: document.activeElement === skipLink,
        bottom: skipRect?.bottom ?? null,
      },
      palette: {
        navy: rootStyle.getPropertyValue("--navy").trim(),
        slate: rootStyle.getPropertyValue("--slate").trim(),
        orange: rootStyle.getPropertyValue("--orange").trim(),
        mist: rootStyle.getPropertyValue("--mist").trim(),
      },
    };
  });

  check(`${label}:http`, response && response.ok(), response ? `${response.status()} ${response.url()}` : "no response");
  check(`${label}:stories`, result.storyCount === 4 && JSON.stringify(result.storyIds) === JSON.stringify(["cnn", "rnn", "style", "rl"]), JSON.stringify(result.storyIds));
  check(`${label}:acts`, JSON.stringify(result.actLabels) === JSON.stringify(["ACT I", "ACT II", "ACT III", "ACT IV"]), JSON.stringify(result.actLabels));
  check(`${label}:one_primary_cta_each`, result.storyPrimaryCounts.every((count) => count === 1), JSON.stringify(result.storyPrimaryCounts));
  check(`${label}:colab_links`, JSON.stringify(result.colabHrefs) === JSON.stringify(expectedColabHrefs) && new Set(result.colabHrefs).size === 5, JSON.stringify(result.colabHrefs));
  check(`${label}:download_links`, JSON.stringify(result.downloadHrefs) === JSON.stringify(expectedDownloadHrefs) && new Set(result.downloadHrefs).size === 5, JSON.stringify(result.downloadHrefs));
  check(`${label}:images_loaded`, result.images.every((image) => image.complete && image.naturalWidth > 0), JSON.stringify(result.images));
  check(`${label}:cinematic_frame_ratio`, result.heroRatio >= 1.73 && result.heroRatio <= 1.82 && result.storyRatios.every((ratio) => ratio >= 1.73 && ratio <= 1.82), JSON.stringify({ hero: result.heroRatio, stories: result.storyRatios }));
  check(`${label}:cinematic_structure`, result.bodyClass.includes("cinematic-site") && result.sceneCount >= 4 && result.atmosphere, JSON.stringify({ bodyClass: result.bodyClass, sceneCount: result.sceneCount, atmosphere: result.atmosphere }));
  check(`${label}:cinematic_effects`, result.effectAnimation !== "none", `film-grain animation=${result.effectAnimation}`);
  check(`${label}:no_horizontal_overflow`, result.scrollWidth <= result.clientWidth && result.visibleOverflow.length === 0, JSON.stringify({ root: `${result.scrollWidth}/${result.clientWidth}`, elements: result.visibleOverflow }));
  check(`${label}:tap_targets`, result.tapTargets.every((target) => target.height >= 43.5), JSON.stringify(result.tapTargets));
  check(`${label}:skip_link_hidden_until_focus`, !result.skipLink.focused && result.skipLink.bottom <= 0, JSON.stringify(result.skipLink));
  check(`${label}:no_old_day_label`, !/\bday[\s_-]*0?6\b|\bd6\b/i.test(result.bodyText), "visible text checked");
  check(`${label}:no_login_instruction`, !/(KAGGLE_API_TOKEN|kaggle\.json|Kaggle.{0,8}(Token|Secret))/i.test(result.bodyText), "visible text checked");
  check(`${label}:no_prohibited_font`, result.fontFamilies.every((family) => !prohibitedFontPattern.test(family)), JSON.stringify(result.fontFamilies));
  check(`${label}:brand_palette`, JSON.stringify(result.palette).toLowerCase() === JSON.stringify({ navy: "#2c3e50", slate: "#5d6d7e", orange: "#f39c12", mist: "#eaedef" }), JSON.stringify(result.palette));
  check(`${label}:audio_default_off`, initialAudio.bodyState === "off" && initialAudio.controls.length === 2 && initialAudio.controls.every((control) => control.tag === "BUTTON" && control.type === "button" && control.pressed === "false" && !control.disabled) && initialAudio.autoplayElements === 0 && initialAudio.engine?.contextState === "not-created" && initialAudio.engine?.graphBuilds === 0, JSON.stringify(initialAudio));

  await page.screenshot({
    path: path.join(outputDir, `cinematic-${label}.png`),
    fullPage: true,
  });
  await page.locator(".hero").screenshot({
    path: path.join(outputDir, `cinematic-${label}-hero.png`),
  });
  await page.locator("#story-list .story-card").first().screenshot({
    path: path.join(outputDir, `cinematic-${label}-first-act.png`),
  });

  await page.keyboard.press("Home");
  await page.keyboard.press("Tab");
  const firstFocus = await page.evaluate(() => ({
    tag: document.activeElement?.tagName,
    className: document.activeElement?.className,
    text: document.activeElement?.textContent?.trim(),
  }));
  check(`${label}:skip_link_focus`, firstFocus.className === "skip-link", JSON.stringify(firstFocus));

  if (label === "desktop") {
    const soundControl = page.locator("#sound-toggle");
    await soundControl.click();
    await page.waitForFunction(() => window.storyAudio?.getState().contextState === "running" && document.querySelector("#sound-toggle")?.getAttribute("aria-pressed") === "true");
    const onState = await page.evaluate(() => ({
      engine: window.storyAudio.getState(),
      pressed: Array.from(document.querySelectorAll("[data-sound-toggle]"), (control) => control.getAttribute("aria-pressed")),
      bodyState: document.body.dataset.sound,
    }));
    await soundControl.focus();
    await page.keyboard.press("Space");
    await page.waitForTimeout(420);
    const offState = await page.evaluate(() => ({
      engine: window.storyAudio.getState(),
      pressed: Array.from(document.querySelectorAll("[data-sound-toggle]"), (control) => control.getAttribute("aria-pressed")),
      bodyState: document.body.dataset.sound,
      focusId: document.activeElement?.id,
    }));
    check("desktop:audio_toggle", onState.engine.graphBuilds === 1 && onState.engine.sourceCount === 5 && onState.engine.userEnabled === true && onState.pressed.every((value) => value === "true") && onState.bodyState === "on" && offState.engine.graphBuilds === 1 && offState.engine.sourceCount === 5 && offState.engine.userEnabled === false && offState.engine.contextState === "suspended" && offState.pressed.every((value) => value === "false") && offState.bodyState === "off" && offState.focusId === "sound-toggle", JSON.stringify({ onState, offState }));
  }

  check(`${label}:console`, consoleErrors.length === 0 && pageErrors.length === 0, JSON.stringify({ consoleErrors, pageErrors }));
  check(`${label}:network`, badResponses.length === 0 && requestFailures.length === 0, JSON.stringify({ badResponses, requestFailures }));

  await context.close();
  return { label, viewport, title: result.title, h1: result.h1 };
}

async function main() {
  const browser = await chromium.launch({ headless: true, args: ["--disable-gpu", "--autoplay-policy=user-gesture-required"] });
  try {
    const viewports = [];
    viewports.push(await inspectViewport(browser, "desktop", { width: 1440, height: 1000 }));
    viewports.push(await inspectViewport(browser, "mobile-360", { width: 360, height: 800 }));

    const reducedContext = await browser.newContext({
      viewport: { width: 1024, height: 768 },
      reducedMotion: "reduce",
    });
    const reducedPage = await reducedContext.newPage();
    await reducedPage.goto(baseUrl, { waitUntil: "networkidle" });
    await reducedPage.waitForSelector("#story-list .story-card:nth-child(4)");
    const reducedState = await reducedPage.evaluate(() => {
      const root = getComputedStyle(document.documentElement);
      const reveal = getComputedStyle(document.querySelector(".reveal"));
      const grain = getComputedStyle(document.querySelector(".film-grain"));
      const sweep = getComputedStyle(document.querySelector(".hero-visual"), "::after");
      return {
        mediaMatches: matchMedia("(prefers-reduced-motion: reduce)").matches,
        scrollBehavior: root.scrollBehavior,
        revealOpacity: reveal.opacity,
        revealTransform: reveal.transform,
        grainAnimation: grain.animationName,
        sweepAnimation: sweep.animationName,
        audioState: window.storyAudio?.getState() || null,
      };
    });
    check("reduced_motion", reducedState.mediaMatches && reducedState.scrollBehavior === "auto" && reducedState.revealOpacity === "1" && reducedState.revealTransform === "none" && reducedState.grainAnimation === "none" && reducedState.sweepAnimation === "none" && reducedState.audioState?.contextState === "not-created", JSON.stringify(reducedState));
    await reducedContext.close();

    const failed = checks.filter((item) => item.status === "fail");
    const report = {
      generatedAt: new Date().toISOString(),
      baseUrl,
      viewports,
      summary: { total: checks.length, passed: checks.length - failed.length, failed: failed.length },
      checks,
    };
    fs.writeFileSync(path.join(outputDir, "qa-report.json"), `${JSON.stringify(report, null, 2)}\n`, "utf8");
    console.log(JSON.stringify(report.summary));
    if (failed.length) {
      console.error(JSON.stringify(failed, null, 2));
      process.exitCode = 1;
    }
  } finally {
    await browser.close();
  }
}

main().catch((error) => {
  console.error(error);
  process.exitCode = 1;
});
