/**
 * 在 code-server 的 Node.js 进程启动时删除全局 navigator。
 *
 * 背景：
 *   Node.js 21+ 引入了全局 navigator 对象，而 VS Code 1.141 内置的是 Node 24。
 *   很多扩展（Continue、通义灵码等）用「是否存在 navigator」判断自己是否跑在浏览器里，
 *   现在被误判成 Web 环境，于是走了浏览器分支，在 Node 里崩溃或功能失效。
 *
 * 现象：
 *   - 报错 PendingMigrationError: navigator is now a global in nodejs
 *   - Continue 的 Tab 补全有请求有返回，但编辑器不渲染 ghost text
 *
 * 用法：
 *   NODE_OPTIONS="--require /home/coder/project/docker/fix-navigator.js"
 */

try {
  Object.defineProperty(globalThis, "navigator", {
    value: undefined,
    configurable: true,
    writable: true,
  });
  if (globalThis.navigator === undefined) {
    // 静默成功即可，不要往 stdout 打日志，避免污染 code-server 输出
  }
} catch (err) {
  // 忽略：某些 Node 版本 navigator 不可配置
}
