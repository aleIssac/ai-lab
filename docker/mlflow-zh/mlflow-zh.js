/*
 * MLflow 中文界面补丁
 * 原理：注入到 MLflow 自带 UI 的 index.html，用 MutationObserver 把“界面文字”替换成中文。
 * 原则：
 *   1) 只替换字典里精确匹配的字符串 —— Run 名、参数、指标值、实验名不会误伤
 *   2) 保留 MLflow / GPT / AUC 等专有名词
 *   3) 图表内部（canvas / SVG 刻度）不在替换范围
 */
(function () {
  "use strict";

  var D = {
    /* ---- 顶栏 / 侧边栏 ---- */
    "MODEL TRAINING": "模型训练",
    "Home": "首页",
    "Experiments": "实验",
    "Models": "模型",
    "Prompts": "提示词",
    "Traces": "调用链",
    "Model registry": "模型注册表",
    "Docs": "文档",
    "Settings": "设置",
    "Help": "帮助",

    /* ---- 首页 ---- */
    "Welcome to MLflow": "欢迎使用 MLflow",
    "Information about UI telemetry": "关于界面使用数据的收集",
    "MLflow collects usage data to improve the product. To confirm your preferences, please visit the settings page in the navigation sidebar. To learn more about what data is collected, please visit the documentation.":
      "MLflow 会收集使用数据以改进产品。如需确认是否开启，请到左侧导航栏的「设置」页面调整；想了解具体收集了哪些数据，请查阅官方文档。",
    "Getting started": "快速上手",
    "Recent Experiments": "最近的实验",
    "View all": "查看全部",
    "Name": "名称",
    "Time created": "创建时间",
    "Last modified": "最后修改",
    "Description": "描述",
    "Tags": "标签",
    "Add tags": "添加标签",
    "New to MLflow?": "第一次用 MLflow？",
    "Tracing": "链路追踪",
    "Capture and debug LLM interactions and agent workflows.": "捕获并调试大模型交互与智能体工作流。",
    "Evaluation": "评估",
    "AI Gateway": "AI 网关",
    "Unified API for multiple LLM providers with rate limiting.": "为多家模型服务提供统一接口，并支持限流。",
    "Model Training": "模型训练",
    "Track experiments with parameters, metrics, and artifacts.": "用参数、指标和产物记录每一次实验。",
    "How do I get started with MLflow?": "怎么开始用 MLflow？",
    "What should I know about MLflow?": "使用 MLflow 需要先了解什么？",
    "Explain how MLflow Tracing works.": "讲讲 MLflow 的链路追踪是怎么工作的。",

    /* ---- 实验 / Runs ---- */
    "Runs": "运行记录",
    "Run": "运行",
    "Run Name": "运行名称",
    "Created": "创建时间",
    "Duration": "耗时",
    "Source": "来源",
    "Metrics": "指标",
    "Params": "参数",
    "Artifacts": "产物",
    "Overview": "概览",
    "Usage": "用量",
    "Quality": "质量",
    "Tool calls": "工具调用",
    "All time": "全部时间",
    "State: Active": "状态：活跃",
    "State: All": "状态：全部",
    "Lifecycle Stage": "生命周期",
    "Columns": "列",
    "Group by": "分组",
    "Sort": "排序",
    "Filter": "筛选",
    "Views": "视图",
    "New run": "新建运行",
    "Create run": "新建运行",
    "Show more columns": "显示更多列",
    "Detect Issues": "检测问题",
    "No data available for the selected time range": "所选时间范围内暂无数据",
    "Latency": "延迟",
    "Errors": "错误",
    "Token Usage": "Token 用量",
    "Tokens per Trace": "每次调用的 Token 数",
    "Cost Breakdown": "成本明细",
    "Total Cost": "总成本",
    "Model": "模型",
    "Provider": "服务商",
    "No cost data available": "暂无成本数据",
    "Cost Over Time": "成本随时间变化",
    "Time Unit:": "时间粒度：",
    "Day": "按天",
    "Last 7 days": "最近 7 天",
    "Search": "搜索",
    "Parameters": "参数",
    "Configuration": "配置",
    "Chart": "图表",
    "Table": "表格",
    "X-axis:": "横轴：",
    "Y-axis:": "纵轴：",
    "Delete": "删除",
    "Rename": "重命名",
    "Compare": "对比",
    "Notes": "备注",
    "Dataset": "数据集",
    "Version": "版本",
    "Status": "状态",
    "Owner": "负责人",
    "Stage": "阶段",
    "Latest Version": "最新版本",
    "Registered Models": "已注册模型",
    "Models": "模型",
    "Loading...": "加载中…",
    "Loading": "加载中",
    "Cancel": "取消",
    "Save": "保存",
    "Close": "关闭",
    "Back": "返回",
    "Next": "下一步",
    "Previous": "上一步",
    "Download": "下载",
    "Copy": "复制",
    "Refresh": "刷新",
    "Show": "显示",
    "Hide": "隐藏",
    "All": "全部",
    "None": "无",
    "Select": "选择",
    "Selected": "已选择",
    "Apply": "应用",
    "Reset": "重置",
    "Clear": "清除",
    "Details": "详情",
    "Summary": "摘要",
    "Start Time": "开始时间",
    "End Time": "结束时间",
    "Inputs": "输入",
    "Outputs": "输出",
    "Source Run": "来源运行",
    "Logged Model": "已记录模型",
    "Experiment": "实验",
    "Experiment Name": "实验名称",
    "Create": "创建",
    "Create Experiment": "新建实验",
    "No experiments found": "没有找到实验",
    "No runs found": "没有找到运行记录",

    /* ---- 补充：首页卡片 / 实验列表 / Runs 工具条 ---- */
    "Beta": "测试版",
    "New": "新",
    "documentation": "文档",
    "Getting Started": "快速上手",
    "Measure and compare LLM quality with built-in and custom scorers.": "用内置或自定义评分器评估模型质量。",
    "Version control and manage prompts with aliases across teams.": "版本化管理提示词，按别名共享。",
    "Ask questions about your experiments, traces, evaluations, and more.": "就实验、调用链、评估等内容直接提问。",
    "Observability": "可观测性",
    "Prompts & versions": "提示词与版本",
    "Training runs": "训练运行",
    "State:": "状态：",
    "Active": "活跃",
    "Datasets": "数据集",
    "Hide run": "隐藏运行",
    "Pin run": "置顶运行",
    "Compare the selected runs.": "对比选中的运行。",
    "Which run performed best?": "哪次运行效果最好？",
    "What parameters differ between runs?": "不同运行之间的参数有什么差异？",
    "Latest version": "最新版本",
    "Aliased versions": "带别名的版本",
    "Created by": "创建者",
    "Create model": "新建模型",
    "Flexible, governed deployments with the new Model Registry UI": "全新的模型注册表界面：灵活部署，且可治理",
    "Model Aliases": "模型别名",
    "Model Tags": "模型标签",
    "Learn more": "了解更多",
    "Try it now": "立即试用",
    "How do I create a new experiment?": "怎么新建一个实验？",
    "How do I organize my experiments?": "怎么整理我的实验？",
    "Show me my recent experiments.": "看看我最近的实验。",
    /* ---- 补充二：导航项 / 工具条零散词 ---- */
    "State": "状态",
    "Sort": "排序",
    "Sort:": "排序：",
    "Sessions": "会话",
    "Judges": "评审器",
    "Review": "审查",
    "Evaluation runs": "评估运行",
    "Playground": "试验场",
    "Agent versions": "智能体版本",
    "MCP registry": "MCP 注册表",
    "Ask a question...": "提个问题…",
    "Start Demo": "开始演示",
    "Page": "页",
    "Explore MLflow's core features with pre-populated sample data including traces, evaluations, and prompts.":
      "用预置示例数据（调用链、评估、提示词）快速体验核心功能。",
    "MLflow collects usage data to improve the product. To confirm your preferences, please visit the settings page in the navigation sidebar. To learn more about what data is collected, please visit the":
      "MLflow 会收集使用数据以改进产品。如需确认是否开启，请到左侧导航栏的「设置」页面调整；想了解具体收集了哪些数据，请访问",
    /* ---- 评审器（Judges）页 ---- */
    "Add a judge to your experiment to measure your GenAI app quality": "给实验加一个评审器，衡量生成式 AI 应用的质量",
    "Choose from a selection of built-in LLM judges or create your own custom code-based judge.":
      "可以从内置的大模型评审器中挑选，也可以自己写一个代码评审器。",
    "Choose from a selection of built-in LLM judges or create your own custom code based judge.":
      "可以从内置的大模型评审器中挑选，也可以自己写一个代码评审器。",
    "Page Not Found": "页面不存在",
    "Go back to the home page.": "返回首页。",
    "New LLM judge": "新建大模型评审器",
    "New custom code judge": "新建代码评审器",
    "Judges": "评审器",
    "Add judge": "添加评审器",
    /* ---- 时间相对量（会被正则兜住，这里放几个常见的） ---- */
    "a few seconds ago": "几秒前",
    "yesterday": "昨天"
  };

  /* 带数字/变量的句子用正则 */
  var RX = [
    [/^(\d+) seconds? ago$/, function (m) { return m[1] + " 秒前"; }],
    [/^(\d+) minutes? ago$/, function (m) { return m[1] + " 分钟前"; }],
    [/^(\d+) hours? ago$/, function (m) { return m[1] + " 小时前"; }],
    [/^(\d+) days? ago$/, function (m) { return m[1] + " 天前"; }],
    [/^(\d+) months? ago$/, function (m) { return m[1] + " 个月前"; }],
    [/^(\d+) years? ago$/, function (m) { return m[1] + " 年前"; }],
    [/^(\d+)\s*-\s*(\d+)\s+of\s+(\d+)$/, function (m) { return "第 " + m[1] + "–" + m[2] + " 条，共 " + m[3] + " 条"; }],
    [/^(\d+)\s*\/\s*page$/i, function (m) { return "每页 " + m[1] + " 条"; }],
    [/^(\d+) matching runs$/i, function (m) { return "共 " + m[1] + " 条匹配的运行"; }],
    [/^Sort:[ ]*(.+)$/i, function (m) { return "排序：" + m[1]; }],
    [/^Show more columns \((\d+) total\)$/, function (m) { return "显示更多列（共 " + m[1] + " 列）"; }],
    [/^Show (\d+) more$/, function (m) { return "再显示 " + m[1] + " 个"; }],
    [/^(\d+) runs?$/, function (m) { return m[1] + " 条运行"; }],
    [/^(\d+) models?$/, function (m) { return m[1] + " 个模型"; }],
    /* 2026-10-19 08:01:02 PM -> 2026-10-19 20:01 */
    [/^(\d{1,2})\/(\d{1,2})\/(\d{4}), (\d{1,2}):(\d{2}):(\d{2}) ?(AM|PM)$/, function (m) {
      var h = parseInt(m[4], 10) % 12;
      if (m[7] === "PM") h += 12;
      var p = function (n) { return (n < 10 ? "0" : "") + n; };
      return m[3] + "-" + p(+m[1]) + "-" + p(+m[2]) + " " + p(h) + ":" + m[5];
    }]
  ];

  var SKIP_TAGS = { SCRIPT: 1, STYLE: 1, NOSCRIPT: 1, TEXTAREA: 1, CODE: 1, PRE: 1 };

  /* 保留原文：不翻译，且不受大小写兜底影响 */
  var KEEP = { "GenAI": 1, "GENAI": 1, "Model training": 1 };

  var DL = {};
  Object.keys(D).forEach(function (k) {
    DL[k.toLowerCase().replace(/\s+/g, " ")] = D[k];
  });

  function translate(text) {
    var t = text.trim();
    if (!t) return null;
    if (Object.prototype.hasOwnProperty.call(KEEP, t)) return null;
    if (Object.prototype.hasOwnProperty.call(D, t)) return D[t];
    var norm = t.replace(/\u00a0/g, " ").replace(/\s+/g, " ").toLowerCase();
    if (Object.prototype.hasOwnProperty.call(DL, norm)) return DL[norm];
    for (var i = 0; i < RX.length; i++) {
      var m = t.match(RX[i][0]);
      if (m) return RX[i][1](m);
    }
    return null;
  }

  function walk(root) {
    if (!root || root.nodeType !== 1 && root.nodeType !== 9) return;
    var walker = document.createTreeWalker(root, NodeFilter.SHOW_TEXT, {
      acceptNode: function (n) {
        if (!n.nodeValue || !n.nodeValue.trim()) return NodeFilter.FILTER_REJECT;
        var p = n.parentElement;
        if (!p || SKIP_TAGS[p.tagName]) return NodeFilter.FILTER_REJECT;
        if (p.closest && p.closest("[data-zh-skip]")) return NodeFilter.FILTER_REJECT;
        return NodeFilter.FILTER_ACCEPT;
      }
    });
    var nodes = [];
    while (walker.nextNode()) nodes.push(walker.currentNode);
    for (var i = 0; i < nodes.length; i++) {
      var n = nodes[i];
      var out = translate(n.nodeValue);
      if (out !== null && out !== n.nodeValue) {
        var lead = n.nodeValue.match(/^\s*/)[0];
        var tail = n.nodeValue.match(/\s*$/)[0];
        n.nodeValue = lead + out + tail;
      }
    }
    /* placeholder / title / aria-label */
    var els = root.querySelectorAll ? root.querySelectorAll("[placeholder],[title],[aria-label]") : [];
    for (var j = 0; j < els.length; j++) {
      ["placeholder", "title", "aria-label"].forEach(function (attr) {
        var v = els[j].getAttribute(attr);
        if (!v) return;
        var tv = translate(v);
        if (tv !== null) els[j].setAttribute(attr, tv);
      });
    }
  }


  var timer = null;
  function schedule() {
    if (timer) return;
    timer = setTimeout(function () {
      timer = null;
      walk(document.body);
    }, 60);
  }

  function start() {
    walk(document.body);
    new MutationObserver(schedule).observe(document.body, {
      childList: true,
      subtree: true,
      characterData: true
    });
    /* 路由切换后再补一遍 */
    window.addEventListener("hashchange", schedule);
    setInterval(schedule, 1500);
  }

  if (document.readyState === "loading") {
    document.addEventListener("DOMContentLoaded", start);
  } else {
    start();
  }
})();
