/**
 * 真机验证 Tab 补全（需求②）
 *
 * 用系统 Edge 打开 code-server，在 test.py 末尾输入 def avg(，
 * 统计幽灵文本节点数、截图，然后按 Tab 看是否落字。
 *
 * 运行（宿主机）：
 *   NODE_PATH="C:/Users/Zeko/.workbuddy/binaries/node/workspace/node_modules" \
 *   node tools/verify_tab_completion.js
 *
 * 输出：
 *   [1] 幽灵文本节点数   >= 1 表示界面画出来了
 *   [2] Tab 前的末几行   应是 def avg( 后面跟灰色文本
 *   [3] Tab 后的末几行   应出现 x, y): 和 return ...
 */

const { chromium } = require("playwright-core");
const EDGE = "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe";
const URL = "http://localhost:8080";
const PASSWORD = process.env.CODE_SERVER_PASSWORD;
if (!PASSWORD) {
  console.error("请先设置环境变量 CODE_SERVER_PASSWORD（code-server 登录密码）再运行");
  process.exit(1);
}
const SHOT = "D:/Zeko/Documents/WorkBuddy/服务器验收/docs/img";
const sleep = (ms) => new Promise((r) => setTimeout(r, ms));

(async () => {
  const browser = await chromium.launch({
    executablePath: EDGE, headless: false, args: ["--start-maximized"],
  });
  const ctx = await browser.newContext({ viewport: null });
  const page = await ctx.newPage();

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
  await page.keyboard.press("Control+End");
  await sleep(400);
  await page.keyboard.press("Enter");
  await page.keyboard.type("def avg(", { delay: 200 });
  await sleep(5000);

  const ghost = await page.evaluate(() => document.querySelectorAll("[class*='ghost']").length);
  await page.screenshot({ path: `${SHOT}/tab-补全-幽灵文本.png` });
  console.log("[1] 幽灵文本节点数:", ghost);

  const before = await page.evaluate(() =>
    Array.from(document.querySelectorAll(".view-line")).map((n) => n.textContent).slice(-4)
  );
  await page.keyboard.press("Tab");
  await sleep(1200);
  const after = await page.evaluate(() =>
    Array.from(document.querySelectorAll(".view-line")).map((n) => n.textContent).slice(-6)
  );
  await page.screenshot({ path: `${SHOT}/tab-补全-按Tab落字.png` });
  console.log("[2] Tab 前:", JSON.stringify(before));
  console.log("[3] Tab 后:", JSON.stringify(after));

  await browser.close();
})().catch((e) => { console.error("[fatal]", e); process.exit(1); });
