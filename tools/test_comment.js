/**
 * 验证「一键加注释」：光标停在函数内 -> 命令面板执行 ailab.addComment -> 文件里出现中文注释
 *
 * 运行：
 *   NODE_PATH="C:/Users/Zeko/.workbuddy/binaries/node/workspace/node_modules" \
 *   node _tmp_test_comment.js
 */

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

  const ed = page.locator(".editor-group-container .monaco-editor").first();
  await ed.click();
  await sleep(800);
  // 光标停到函数体里（第 6 行附近），不选中任何东西
  await page.keyboard.press("Control+Home");
  for (let i = 0; i < 5; i += 1) { await page.keyboard.press("ArrowDown"); }
  await page.keyboard.press("End");
  await sleep(400);

  console.log("[1] 光标行:", await page.evaluate(() => {
    const s = document.querySelector(".statusbar")?.innerText || "";
    const m = s.match(/Ln\s*(\d+)/);
    return m ? m[1] : "?";
  }));

  // 用快捷键触发（同时验证 package.json 里的 keybinding 是否生效）
  await page.keyboard.press("Control+Alt+c");
  await sleep(1500);
  const notified = await page.evaluate(() => {
    const el = document.querySelector(".notifications-toasts");
    return el ? el.innerText.replace(/\s+/g, " ").slice(0, 200) : "(无通知)";
  });
  console.log("[2] 触发后通知:", JSON.stringify(notified));

  // 模型生成要十几秒，轮询页面上的通知/编辑器内容
  let done = false;
  for (let i = 0; i < 40; i += 1) {
    await sleep(3000);
    const txt = await page.evaluate(() =>
      Array.from(document.querySelectorAll(".view-line")).map((n) => n.textContent).join("\n")
    );
    if (txt.includes("参数") || txt.includes("返回") || txt.includes("说明") || txt.includes("Args")) {
      done = true;
      console.log(`[3] 第 ${(i + 1) * 3} 秒检测到注释内容`);
      break;
    }
  }
  console.log("[4] 是否检测到注释:", done);

  await page.evaluate(() => {});
  await page.screenshot({ path: "docs/img/comment-result.png" });
  const mine = logs.filter((l) => /AI Lab|注释/.test(l));
  mine.slice(-6).forEach((l) => console.log("   LOG:", l.slice(0, 200)));

  await browser.close();
})().catch((e) => { console.error("[fatal]", e); process.exit(1); });
