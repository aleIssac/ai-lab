/** 验证「整个文件批量加注释」：Ctrl+Alt+Shift+C */
const { chromium } = require("playwright-core");
const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const URL = "http://localhost:8080";
const PASSWORD = process.env.CODE_SERVER_PASSWORD;
if (!PASSWORD) {
  console.error("请先设置环境变量 CODE_SERVER_PASSWORD（code-server 登录密码）再运行");
  process.exit(1);
}
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
  await page.keyboard.type("test.py", { delay: 60 });
  await sleep(1500);
  await page.keyboard.press("Enter");
  await sleep(5000);

  await page.locator(".editor-group-container .monaco-editor").first().click();
  await sleep(800);
  await page.keyboard.press("Control+Home");
  await sleep(300);

  await page.keyboard.press("Control+Alt+Shift+c");
  await sleep(2000);
  const t = await page.evaluate(() => {
    const el = document.querySelector(".notifications-toasts");
    return el ? el.innerText.replace(/\s+/g, " ").slice(0, 160) : "(无通知)";
  });
  console.log("[1] 通知:", JSON.stringify(t));

  for (let i = 0; i < 40; i += 1) {
    await sleep(3000);
    const txt = await page.evaluate(() =>
      Array.from(document.querySelectorAll(".view-line")).map((n) => n.textContent).join("\n"));
    const hits = (txt.match(/Args|参数|返回|计算/g) || []).length;
    if (hits >= 4) {
      console.log(`[2] 第 ${(i + 1) * 3} 秒，检测到 ${hits} 处注释关键词`);
      break;
    }
  }
  const final = await page.evaluate(() => {
    const el = document.querySelector(".notifications-toasts");
    return el ? el.innerText.replace(/\s+/g, " ").slice(0, 160) : "";
  });
  console.log("[3] 结束通知:", JSON.stringify(final));
  await page.screenshot({ path: "docs/img/comment-batch.png" });
  logs.filter((l) => /AI Lab 注释/.test(l)).slice(-5).forEach((l) => console.log("   LOG:", l.slice(0, 160)));
  await browser.close();
})().catch((e) => { console.error("[fatal]", e); process.exit(1); });
