/** 验证 Ctrl+Alt+D 报错诊断 */
const { chromium } = require("playwright-core");
const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const URL = "http://localhost:8080";
const PASSWORD = "ai-lab-2026";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));
const logs = [];

(async () => {
  const browser = await chromium.launch({
    executablePath: EDGE, headless: false, args: ["--start-maximized"],
  });
  const ctx = await browser.newContext({ viewport: null });
  const page = await ctx.newPage();
  page.on("console", (m) => logs.push(m.text()));

  await page.goto(URL, { waitUntil: "domcontentloaded", timeout: 40000 });
  await sleep(3500);
  const pwd = page.locator('input[type="password"]');
  if (await pwd.count()) {
    await pwd.first().fill(PASSWORD);
    await pwd.first().press("Enter");
    await sleep(10000);
  }
  await page.bringToFront();

  await page.keyboard.press("Control+P");
  await sleep(1500);
  await page.keyboard.type("err_demo.py", { delay: 60 });
  await sleep(1500);
  await page.keyboard.press("Enter");
  await sleep(5000);

  await page.locator(".editor-group-container .monaco-editor").first().click();
  await sleep(800);
  // 选中最后 4 行（traceback 注释）
  await page.keyboard.press("Control+End");
  await sleep(300);
  for (let i = 0; i < 4; i += 1) { await page.keyboard.press("Shift+ArrowUp"); }
  await page.keyboard.press("Shift+End");
  await sleep(400);

  const before = await page.evaluate(() => document.querySelectorAll(".tab").length);
  console.log("[1] 触发前标签数:", before);

  await page.keyboard.press("Control+Alt+k");
  await sleep(2000);
  const toast = await page.evaluate(() => {
    const el = document.querySelector(".notifications-toasts");
    return el ? el.innerText.replace(/\s+/g, " ").slice(0, 120) : "(无通知)";
  });
  console.log("[2] 通知:", JSON.stringify(toast));

  let found = false;
  for (let i = 0; i < 30; i += 1) {
    await sleep(3000);
    const txt = await page.evaluate(() => {
      const editors = Array.from(document.querySelectorAll(".editor-group-container .monaco-editor"));
      return editors.map((e) => Array.from(e.querySelectorAll(".view-line")).map((n) => n.textContent).join("\n")).join("\n");
    });
    if (txt.includes("【类型】") && (txt.includes("【修复】"))) {
      found = true;
      console.log(`[3] 第 ${(i + 1) * 3} 秒出现四段式报告`);
      const snippet = txt.split("\n").filter((l) => l.includes("【") || l.includes("refresh") || l.includes("cuda")).slice(0, 8);
      console.log("[4] 报告片段:", JSON.stringify(snippet));
      break;
    }
  }
  console.log("[5] 是否生成报告:", found);
  const after = await page.evaluate(() => document.querySelectorAll(".tab").length);
  console.log("[6] 触发后标签数:", after);
  await page.screenshot({ path: "docs/img/diagnose-result.png" });
  logs.filter((l) => /AI Lab 诊断/.test(l)).slice(-3).forEach((l) => console.log("   LOG:", l.slice(0, 160)));
  await browser.close();
})().catch((e) => { console.error("[fatal]", e); process.exit(1); });
