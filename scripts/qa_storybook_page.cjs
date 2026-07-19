const fs = require("node:fs");
const path = require("node:path");

const baseUrl = process.argv[2] || "http://127.0.0.1:8765";
const playwrightModule = process.argv[3] || "playwright";
const { chromium } = require(playwrightModule);

const repoRoot = path.resolve(__dirname, "..");
const outputDir = path.join(repoRoot, "output", "playwright");
fs.mkdirSync(outputDir, { recursive: true });

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

  page.on("console", (message) => {
    if (message.type() === "error") consoleErrors.push(message.text());
  });
  page.on("pageerror", (error) => pageErrors.push(error.message));
  page.on("response", (response) => {
    if (response.url().startsWith(baseUrl) && response.status() >= 400) {
      badResponses.push(`${response.status()} ${response.url()}`);
    }
  });

  const response = await page.goto(baseUrl, { waitUntil: "networkidle" });
  await page.waitForSelector("#story-list .story-card:nth-child(4)");

  const lazyImages = page.locator('img[loading="lazy"]');
  for (let index = 0; index < await lazyImages.count(); index += 1) {
    const image = lazyImages.nth(index);
    await image.scrollIntoViewIfNeeded();
    await image.evaluate((element) => element.decode().catch(() => undefined));
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
    return {
      title: document.title,
      h1: document.querySelector("h1")?.innerText.trim() || "",
      storyCount: storyCards.length,
      storyPrimaryCounts: storyCards.map((card) => card.querySelectorAll(".story-actions .button--primary").length),
      colabHrefs: Array.from(document.querySelectorAll("#preflight-colab, .story-actions .button--primary"), (link) => link.href),
      downloadHrefs: Array.from(document.querySelectorAll("#preflight-local, .story-actions a[download]"), (link) => link.href),
      bodyText: document.body.innerText,
      images,
      renderedStoryRatios: Array.from(
        document.querySelectorAll(".hero-visual > img, .story-figure > img"),
        (image) => {
          const rect = image.getBoundingClientRect();
          return Number((rect.width / rect.height).toFixed(3));
        },
      ),
      scrollWidth: document.documentElement.scrollWidth,
      clientWidth: document.documentElement.clientWidth,
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
  check(`${label}:stories`, result.storyCount === 4, `storyCount=${result.storyCount}`);
  check(`${label}:one_primary_cta_each`, result.storyPrimaryCounts.every((count) => count === 1), JSON.stringify(result.storyPrimaryCounts));
  check(`${label}:colab_links`, result.colabHrefs.length === 5 && result.colabHrefs.every((href) => href.startsWith("https://colab.research.google.com/github/")), JSON.stringify(result.colabHrefs));
  check(`${label}:download_links`, result.downloadHrefs.length === 5 && result.downloadHrefs.every((href) => href.startsWith("https://raw.githubusercontent.com/")), JSON.stringify(result.downloadHrefs));
  check(`${label}:images_loaded`, result.images.every((image) => image.complete && image.naturalWidth > 0), JSON.stringify(result.images));
  check(`${label}:storybook_image_ratio`, result.renderedStoryRatios.every((ratio) => ratio >= 1.30 && ratio <= 1.35), JSON.stringify(result.renderedStoryRatios));
  check(`${label}:no_horizontal_overflow`, result.scrollWidth <= result.clientWidth, `${result.scrollWidth}/${result.clientWidth}`);
  check(`${label}:skip_link_hidden_until_focus`, !result.skipLink.focused && result.skipLink.bottom <= 0, JSON.stringify(result.skipLink));
  check(`${label}:no_old_day_label`, !/\bday[\s_-]*0?6\b|\bd6\b/i.test(result.bodyText), "visible text checked");
  check(`${label}:no_login_instruction`, !/(KAGGLE_API_TOKEN|kaggle\.json|請.{0,8}登入.{0,8}Kaggle|Kaggle.{0,8}(Token|Secret))/i.test(result.bodyText), "visible text checked");
  check(`${label}:brand_palette`, JSON.stringify(result.palette).toLowerCase() === JSON.stringify({ navy: "#2c3e50", slate: "#5d6d7e", orange: "#f39c12", mist: "#eaedef" }), JSON.stringify(result.palette));
  check(`${label}:console`, consoleErrors.length === 0 && pageErrors.length === 0, JSON.stringify({ consoleErrors, pageErrors }));
  check(`${label}:local_assets`, badResponses.length === 0, JSON.stringify(badResponses));

  await page.screenshot({
    path: path.join(outputDir, `storybook-${label}.png`),
    fullPage: true,
  });
  await page.locator(".hero").screenshot({
    path: path.join(outputDir, `storybook-${label}-hero.png`),
  });
  await page.locator("#story-list .story-card").first().screenshot({
    path: path.join(outputDir, `storybook-${label}-first-story.png`),
  });

  await page.keyboard.press("Home");
  await page.keyboard.press("Tab");
  const firstFocus = await page.evaluate(() => ({
    tag: document.activeElement?.tagName,
    className: document.activeElement?.className,
    text: document.activeElement?.textContent?.trim(),
  }));
  check(`${label}:skip_link_focus`, firstFocus.className === "skip-link", JSON.stringify(firstFocus));

  await context.close();
  return { label, viewport, title: result.title, h1: result.h1 };
}

async function main() {
  const browser = await chromium.launch({ headless: true, args: ["--disable-gpu"] });
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
    const scrollBehavior = await reducedPage.evaluate(() => getComputedStyle(document.documentElement).scrollBehavior);
    check("reduced_motion:scroll_behavior", scrollBehavior === "auto", `scroll-behavior=${scrollBehavior}`);
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
