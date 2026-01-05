from typing import Dict, Any
from datetime import datetime
import json
import uuid
from pathlib import Path

from langgraph.graph import StateGraph, END
from langchain_core.messages import SystemMessage, HumanMessage, AIMessage
from langchain_core.callbacks.manager import adispatch_custom_event

from server.core.llm import get_llm
from server.kernel.skill_service import skill_service
from server.kernel.skill_integration import skill_injector
from .tools import generate_image_base64

from .schema import CourseOutline, LessonContent, OfflineCoursePackage
from .state import TutorialState

def analyze_intent(state: TutorialState):
    """
    分析用户意图。
    目前只是简单的透传，未来可以加入对用户输入意图的分类（如：生成大纲、修改特定章节等）。
    """
    return {"messages": [SystemMessage(content="Analyzing user request for tutorial generation...")]}

def _safe_json_for_script_tag(data: Any) -> str:
    """
    安全地将 Python 对象序列化为 JSON 字符串，用于嵌入 HTML <script> 标签。
    防止 XSS 攻击（如 </script>注入）。
    """
    raw = json.dumps(data, ensure_ascii=False)
    return raw.replace("</script>", "<\\/script>")

def _render_offline_course_html(course: OfflineCoursePackage) -> str:
    """
    渲染离线课程包的 HTML 内容。
    包含：
    1. 移动端优先的 CSS 样式 (Mobile First Design)。
    2. 单页应用 (SPA) 风格的交互逻辑 (Sidebar + Main)。
    3. 完整的课程内容 (大纲、课时、练习、测验)。
    4. 本地存储 (LocalStorage) 的进度管理逻辑。
    """
    payload = _safe_json_for_script_tag(course.model_dump())
    export_id = course.export_id
    title = course.outline.title
    return f"""<!doctype html>
<html lang="zh-CN">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>{title}</title>
  <style>
    :root {{
      --bg: #f3f4f6;
      --panel: #ffffff;
      --panel2: #ffffff;
      --text: #111827;
      --muted: #6b7280;
      --accent: #2563eb;
      --accent2: #16a34a;
      --border: #e5e7eb;
      --shadow: rgba(17, 24, 39, 0.08);
      --mono: ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, "Liberation Mono", "Courier New", monospace;
      --sans: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, "Apple Color Emoji", "Segoe UI Emoji";
      --safe-top: env(safe-area-inset-top);
      --safe-bottom: env(safe-area-inset-bottom);
    }}
    html, body {{ height: 100%; overflow: hidden; }}
    body {{
      margin: 0;
      background: var(--bg);
      color: var(--text);
      font-family: var(--sans);
      -webkit-tap-highlight-color: transparent;
    }}
    .app {{
      display: flex;
      width: 100%;
      height: 100%;
      overflow: hidden;
      position: relative;
    }}
    /* Mobile First: Sidebar is full screen list */
    .sidebar {{
      width: 100%;
      height: 100%;
      overflow-y: auto;
      background: var(--panel);
      position: absolute;
      top: 0;
      left: 0;
      z-index: 10;
      transition: transform 0.3s cubic-bezier(0.25, 1, 0.5, 1);
      padding-bottom: var(--safe-bottom);
    }}
    /* Mobile First: Main is full screen detail, hidden off-screen */
    .main {{
      width: 100%;
      height: 100%;
      overflow-y: auto;
      background: var(--bg);
      position: absolute;
      top: 0;
      left: 0;
      z-index: 20;
      transform: translateX(100%);
      transition: transform 0.3s cubic-bezier(0.25, 1, 0.5, 1);
      display: flex;
      flex-direction: column;
      padding-bottom: var(--safe-bottom);
    }}
    /* State: Show Detail */
    .app.show-detail .main {{
      transform: translateX(0);
    }}
    
    /* Desktop / Tablet Styles */
    @media (min-width: 768px) {{
      .app {{
        display: grid;
        grid-template-columns: 360px 1fr;
        position: static;
      }}
      .sidebar {{
        position: static;
        width: auto;
        transform: none !important;
        border-right: 1px solid var(--border);
        box-shadow: 0 6px 24px var(--shadow);
      }}
      .main {{
        position: static;
        width: auto;
        transform: none !important;
        padding: 24px 28px 40px;
      }}
      .mobile-nav-bar {{
        display: none !important;
      }}
    }}

    /* Common Components */
    .brand {{
      padding: 18px 18px 12px;
      padding-top: calc(18px + var(--safe-top));
      border-bottom: 1px solid var(--border);
      background: var(--panel);
      position: sticky;
      top: 0;
      z-index: 5;
    }}
    .title {{
      font-size: 18px;
      font-weight: 700;
      line-height: 1.25;
      margin: 0 0 6px;
    }}
    .subtitle {{
      margin: 0;
      font-size: 13px;
      color: var(--muted);
      line-height: 1.35;
    }}
    .actions {{
      display: flex;
      gap: 10px;
      padding: 12px 18px 16px;
      border-bottom: 1px solid var(--border);
      background: var(--panel);
    }}
    .btn {{
      appearance: none;
      border: 1px solid var(--border);
      background: #ffffff;
      color: var(--text);
      padding: 8px 14px; /* Larger touch target */
      border-radius: 10px;
      font-size: 14px;
      cursor: pointer;
      font-weight: 500;
    }}
    .btn:active {{ opacity: 0.7; }}
    .btn.primary {{
      border-color: rgba(37,99,235,0.25);
      background: rgba(37,99,235,0.08);
      color: #1d4ed8;
    }}
    .nav {{
      padding: 14px 10px 24px;
    }}
    .module {{
      margin: 10px 8px 14px;
      border: 1px solid var(--border);
      border-radius: 12px;
      overflow: hidden;
      background: #fff;
    }}
    .module-header {{
      padding: 12px 14px;
      background: #f9fafb;
      border-bottom: 1px solid var(--border);
    }}
    .module-title {{
      margin: 0 0 4px;
      font-weight: 700;
      font-size: 14px;
    }}
    .module-goal {{
      margin: 0;
      font-size: 12px;
      color: var(--muted);
      line-height: 1.35;
    }}
    .lesson-list {{
      list-style: none;
      padding: 0;
      margin: 0;
    }}
    .lesson-item {{
      display: flex;
      gap: 12px;
      align-items: center;
      padding: 14px 14px;
      border-bottom: 1px solid var(--border);
      cursor: pointer;
      transition: background 0.2s;
    }}
    .lesson-item:active {{ background: #f3f4f6; }}
    .lesson-item:last-child {{ border-bottom: none; }}
    .pill {{
      font-size: 11px;
      color: var(--muted);
      border: 1px solid var(--border);
      padding: 2px 8px;
      border-radius: 999px;
      white-space: nowrap;
    }}
    .lesson-meta {{ min-width: 0; flex: 1; }}
    .lesson-title {{
      margin: 0 0 4px;
      font-size: 15px;
      font-weight: 600;
      line-height: 1.35;
    }}
    .lesson-obj {{
      margin: 0;
      font-size: 13px;
      color: var(--muted);
      line-height: 1.35;
      display: -webkit-box;
      -webkit-line-clamp: 2;
      -webkit-box-orient: vertical;
      overflow: hidden;
    }}
    .status {{
      width: 12px;
      height: 12px;
      border-radius: 999px;
      border: 2px solid var(--border);
      background: #ffffff;
      flex: 0 0 auto;
    }}
    .status.done {{
      background: #16a34a;
      border-color: #16a34a;
    }}
    .status.active {{
      background: #2563eb;
      border-color: #2563eb;
    }}
    
    /* Content Area Styles */
    .mobile-nav-bar {{
      display: flex;
      align-items: center;
      padding: 12px 16px;
      padding-top: calc(12px + var(--safe-top));
      background: #fff;
      border-bottom: 1px solid var(--border);
      position: sticky;
      top: 0;
      z-index: 100;
      gap: 12px;
    }}
    .back-btn {{
      background: none;
      border: none;
      font-size: 24px;
      padding: 4px 8px;
      cursor: pointer;
      color: var(--text);
      margin-left: -8px;
    }}
    .page-title {{
      font-size: 16px;
      font-weight: 700;
      white-space: nowrap;
      overflow: hidden;
      text-overflow: ellipsis;
    }}
    
    .content-wrapper {{
      padding: 16px;
    }}
    @media (min-width: 768px) {{
      .content-wrapper {{ padding: 0; }}
    }}

    .card {{
      border: 1px solid var(--border);
      border-radius: 14px;
      background: #ffffff;
      box-shadow: 0 4px 12px var(--shadow);
      padding: 16px;
      margin-bottom: 16px;
    }}
    .h1 {{
      margin: 0 0 12px;
      font-size: 22px;
      font-weight: 800;
      line-height: 1.2;
    }}
    .muted {{
      color: var(--muted);
      font-size: 13px;
      line-height: 1.45;
      margin: 0;
    }}
    .section-title {{
      margin: 0 0 10px;
      font-size: 16px;
      font-weight: 700;
    }}
    .para {{
      margin: 0 0 12px;
      color: var(--text);
      font-size: 15px;
      line-height: 1.6;
      white-space: pre-wrap;
    }}
    .list {{
      margin: 0;
      padding-left: 20px;
      color: var(--text);
      font-size: 15px;
      line-height: 1.6;
    }}
    .tag {{
      display: inline-block;
      margin: 4px 6px 0 0;
      border: 1px solid var(--border);
      color: var(--muted);
      border-radius: 999px;
      padding: 4px 12px;
      font-size: 13px;
      background: #f9fafb;
    }}
    .quiz-q {{
      padding: 14px;
      border: 1px solid var(--border);
      border-radius: 12px;
      background: #f9fafb;
      margin: 12px 0;
    }}
    .quiz-q h4 {{
      margin: 0 0 10px;
      font-size: 15px;
      font-weight: 700;
      line-height: 1.4;
    }}
    .opt {{
      display: flex;
      gap: 10px;
      align-items: flex-start;
      margin: 10px 0;
      font-size: 15px;
      line-height: 1.4;
      color: var(--text);
      padding: 8px;
      background: #fff;
      border-radius: 8px;
      border: 1px solid transparent;
    }}
    .opt:active {{ background: #f3f4f6; }}
    .result {{
      margin-top: 12px;
      font-size: 14px;
      line-height: 1.5;
      white-space: pre-wrap;
      background: #fff;
      padding: 10px;
      border-radius: 8px;
      border: 1px solid var(--border);
    }}
    textarea {{
      width: 100%;
      min-height: 120px;
      resize: vertical;
      border-radius: 12px;
      border: 1px solid var(--border);
      background: #ffffff;
      color: var(--text);
      padding: 12px;
      font-family: var(--sans);
      font-size: 15px;
      line-height: 1.5;
      outline: none;
      box-sizing: border-box;
    }}
    textarea:focus {{ border-color: var(--accent); }}
    .footer {{
      margin-top: 24px;
      padding: 0 16px 24px;
      color: var(--muted);
      font-size: 12px;
      line-height: 1.5;
      text-align: center;
    }}
  </style>
</head>
<body>
  <div class="app">
    <aside class="sidebar">
      <div class="brand">
        <p class="title" id="courseTitle"></p>
        <p class="subtitle" id="courseMeta"></p>
      </div>
      <div class="actions">
        <button class="btn primary" id="btnExportProgress">导出学习记录</button>
        <button class="btn" id="btnResetProgress">重置进度</button>
      </div>
      <nav class="nav" id="nav"></nav>
    </aside>
    <main class="main">
      <div class="mobile-nav-bar">
        <button class="back-btn" id="btnBack">←</button>
        <div class="page-title" id="mobileTitle">课程内容</div>
      </div>
      <div class="content-wrapper">
        <div id="content"></div>
        <div class="footer">
          <div>离线教程包 ID：<span style="font-family: var(--mono)">{export_id}</span></div>
          <div>学习记录仅保存在本地浏览器（LocalStorage），可导出为 JSON 备份。</div>
        </div>
      </div>
    </main>
  </div>

  <script>
    window.__COURSE_PACKAGE__ = {payload};
  </script>
  <script>
    (function() {{
      const pkg = window.__COURSE_PACKAGE__;
      const exportId = pkg.export_id;
      const storageKey = "seer_tutorial_progress_" + exportId;

      function loadProgress() {{
        try {{
          const raw = localStorage.getItem(storageKey);
          if (!raw) return {{
            activeLessonId: null,
            completed: {{}},
            mcqAttempts: {{}},
            shortAnswers: {{}}
          }};
          const obj = JSON.parse(raw);
          if (!obj || typeof obj !== "object") throw new Error("bad progress");
          return {{
            activeLessonId: obj.activeLessonId || null,
            completed: obj.completed || {{}},
            mcqAttempts: obj.mcqAttempts || {{}},
            shortAnswers: obj.shortAnswers || {{}}
          }};
        }} catch (e) {{
          return {{
            activeLessonId: null,
            completed: {{}},
            mcqAttempts: {{}},
            shortAnswers: {{}}
          }};
        }}
      }}

      function saveProgress(p) {{
        localStorage.setItem(storageKey, JSON.stringify(p));
      }}

      function downloadJson(filename, data) {{
        const blob = new Blob([JSON.stringify(data, null, 2)], {{ type: "application/json;charset=utf-8" }});
        const url = URL.createObjectURL(blob);
        const a = document.createElement("a");
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        a.remove();
        URL.revokeObjectURL(url);
      }}

      const progress = loadProgress();

      const courseTitleEl = document.getElementById("courseTitle");
      const courseMetaEl = document.getElementById("courseMeta");
      courseTitleEl.textContent = pkg.outline.title;
      courseMetaEl.textContent = `主题：${{pkg.outline.topic}} · 预计：${{pkg.outline.total_estimated_hours}} 小时`;

      const navEl = document.getElementById("nav");
      const contentEl = document.getElementById("content");
      const app = document.querySelector(".app");
      const mobileTitle = document.getElementById("mobileTitle");

      function setActiveLesson(lessonId) {{
        progress.activeLessonId = lessonId;
        saveProgress(progress);
        renderNav();
        renderLesson(lessonId);
        if (app) app.classList.add("show-detail");
        if (mobileTitle && pkg.lessons[lessonId]) {{
          mobileTitle.textContent = pkg.lessons[lessonId].title;
        }}
      }}

      const btnBack = document.getElementById("btnBack");
      if (btnBack) {{
        btnBack.addEventListener("click", () => {{
          if (app) app.classList.remove("show-detail");
        }});
      }}

      function markCompleted(lessonId, done) {{
        progress.completed[lessonId] = !!done;
        saveProgress(progress);
        renderNav();
      }}

      function renderNav() {{
        navEl.innerHTML = "";
        pkg.outline.modules.forEach((m) => {{
          const module = document.createElement("div");
          module.className = "module";

          const mh = document.createElement("div");
          mh.className = "module-header";
          const mt = document.createElement("p");
          mt.className = "module-title";
          mt.textContent = m.title;
          const mg = document.createElement("p");
          mg.className = "module-goal";
          mg.textContent = m.goal;
          mh.appendChild(mt);
          mh.appendChild(mg);
          module.appendChild(mh);

          const ul = document.createElement("ul");
          ul.className = "lesson-list";

          m.lessons.forEach((l) => {{
            const li = document.createElement("li");
            li.className = "lesson-item";

            const st = document.createElement("span");
            st.className = "status";
            const isActive = progress.activeLessonId === l.id;
            if (isActive) st.classList.add("active");
            if (progress.completed[l.id]) st.classList.add("done");
            li.appendChild(st);

            const meta = document.createElement("div");
            meta.className = "lesson-meta";
            const lt = document.createElement("p");
            lt.className = "lesson-title";
            lt.textContent = l.title;
            const lo = document.createElement("p");
            lo.className = "lesson-obj";
            lo.textContent = l.objective;
            meta.appendChild(lt);
            meta.appendChild(lo);
            li.appendChild(meta);

            const pill = document.createElement("span");
            pill.className = "pill";
            pill.textContent = `${{l.estimated_minutes}}m`;
            li.appendChild(pill);

            li.addEventListener("click", () => setActiveLesson(l.id));
            ul.appendChild(li);
          }});

          module.appendChild(ul);
          navEl.appendChild(module);
        }});
      }}

      function createCard(title) {{
        const card = document.createElement("div");
        card.className = "card";
        const h = document.createElement("p");
        h.className = "section-title";
        h.textContent = title;
        card.appendChild(h);
        return card;
      }}

      function addParagraph(parent, text) {{
        const p = document.createElement("p");
        p.className = "para";
        p.textContent = text || "";
        parent.appendChild(p);
      }}

      function addList(parent, items) {{
        const ul = document.createElement("ul");
        ul.className = "list";
        (items || []).forEach((it) => {{
          const li = document.createElement("li");
          li.textContent = it;
          ul.appendChild(li);
        }});
        parent.appendChild(ul);
      }}

      function renderLesson(lessonId) {{
        contentEl.innerHTML = "";
        const lesson = pkg.lessons[lessonId];
        if (!lesson) {{
          const card = document.createElement("div");
          card.className = "card";
          const h = document.createElement("p");
          h.className = "h1";
          h.textContent = "请选择一个课时开始学习";
          card.appendChild(h);
          const p = document.createElement("p");
          p.className = "muted";
          p.textContent = "左侧目录中点击课时。学习记录保存在本地，可导出。";
          card.appendChild(p);
          contentEl.appendChild(card);
          return;
        }}

        const head = document.createElement("div");
        head.className = "card";
        const h1 = document.createElement("p");
        h1.className = "h1";
        h1.textContent = lesson.title;
        head.appendChild(h1);

        if (lesson.image_base64) {{
          const img = document.createElement("img");
          img.src = "data:image/png;base64," + lesson.image_base64;
          img.alt = lesson.image_prompt || "Lesson Illustration";
          img.style.display = "block";
          img.style.maxWidth = "100%";
          img.style.height = "auto";
          img.style.borderRadius = "8px";
          img.style.marginTop = "16px";
          img.style.marginBottom = "8px";
          img.style.border = "1px solid var(--border)";
          head.appendChild(img);
        }}

        const topActions = document.createElement("div");
        topActions.className = "actions";
        topActions.style.padding = "0";
        topActions.style.borderBottom = "none";
        topActions.style.marginTop = "10px";
        const btnDone = document.createElement("button");
        btnDone.className = "btn primary";
        btnDone.textContent = progress.completed[lessonId] ? "标记为未完成" : "标记为完成";
        btnDone.addEventListener("click", () => {{
          const next = !progress.completed[lessonId];
          markCompleted(lessonId, next);
          btnDone.textContent = next ? "标记为未完成" : "标记为完成";
        }});
        topActions.appendChild(btnDone);
        head.appendChild(topActions);
        contentEl.appendChild(head);

        const c1 = createCard("类比解释（Feynman）");
        addParagraph(c1, lesson.feynman_analogy);
        contentEl.appendChild(c1);

        const c2 = createCard("白话解释（讲给 12 岁孩子）");
        addParagraph(c2, lesson.plain_explanation);
        contentEl.appendChild(c2);

        const c3 = createCard("关键术语");
        if (lesson.key_terms && lesson.key_terms.length) {{
          const wrap = document.createElement("div");
          (lesson.key_terms || []).forEach((t) => {{
            const span = document.createElement("span");
            span.className = "tag";
            span.textContent = t;
            wrap.appendChild(span);
          }});
          c3.appendChild(wrap);
        }} else {{
          addParagraph(c3, "本课没有额外术语。");
        }}
        contentEl.appendChild(c3);

        const c4 = createCard("常见误解与纠偏");
        if (lesson.common_misconceptions && lesson.common_misconceptions.length) {{
          addList(c4, lesson.common_misconceptions);
        }} else {{
          addParagraph(c4, "本课没有列出常见误解。");
        }}
        contentEl.appendChild(c4);

        const c5 = createCard("例子");
        if (lesson.examples && lesson.examples.length) {{
          addList(c5, lesson.examples);
        }} else {{
          addParagraph(c5, "本课没有例子。");
        }}
        contentEl.appendChild(c5);

        const c6 = createCard("练习");
        if (lesson.exercises && lesson.exercises.length) {{
          (lesson.exercises || []).forEach((ex, idx) => {{
            const q = document.createElement("div");
            q.className = "quiz-q";
            const h4 = document.createElement("h4");
            h4.textContent = `练习 ${{idx + 1}}：${{ex.prompt}}`;
            q.appendChild(h4);
            if (ex.hints && ex.hints.length) {{
              const p = document.createElement("div");
              p.className = "result";
              p.style.color = "var(--muted)";
              p.textContent = "提示：\\n- " + ex.hints.join("\\n- ");
              q.appendChild(p);
            }}
            const p2 = document.createElement("div");
            p2.className = "result";
            p2.style.color = "var(--muted)";
            p2.textContent = "参考要点：\\n" + (ex.expected || "");
            q.appendChild(p2);
            c6.appendChild(q);
          }});
        }} else {{
          addParagraph(c6, "本课没有练习。");
        }}
        contentEl.appendChild(c6);

        const c7 = createCard("成果校验");
        const ck = lesson.checkpoint || {{ pass_score: 70, mcq: [], short_answer: [] }};
        const meta = document.createElement("p");
        meta.className = "muted";
        meta.textContent = `建议及格线：${{ck.pass_score}}/100。选择题可自动评分；简答题请对照要点自评。`;
        c7.appendChild(meta);

        if (ck.mcq && ck.mcq.length) {{
          const mcqWrap = document.createElement("div");
          ck.mcq.forEach((qq, qi) => {{
            const box = document.createElement("div");
            box.className = "quiz-q";
            const h4 = document.createElement("h4");
            h4.textContent = `选择题 ${{qi + 1}}：${{qq.question}}`;
            box.appendChild(h4);

            const name = `mcq_${{lessonId}}_${{qi}}`;
            qq.options.forEach((opt, oi) => {{
              const label = document.createElement("label");
              label.className = "opt";
              const input = document.createElement("input");
              input.type = "radio";
              input.name = name;
              input.value = String(oi);
              label.appendChild(input);
              const span = document.createElement("span");
              span.textContent = opt;
              label.appendChild(span);
              box.appendChild(label);
            }});

            const btn = document.createElement("button");
            btn.className = "btn primary";
            btn.textContent = "评分";
            const res = document.createElement("div");
            res.className = "result";
            btn.addEventListener("click", () => {{
              const chosen = box.querySelector(`input[name="${{name}}"]:checked`);
              const chosenIdx = chosen ? Number(chosen.value) : -1;
              const correct = chosenIdx === qq.answer_index;
              res.textContent = (correct ? "正确。" : "不正确。") + "\\n解析：" + (qq.rationale || "");
              progress.mcqAttempts[lessonId] = progress.mcqAttempts[lessonId] || {{}};
              progress.mcqAttempts[lessonId][String(qi)] = {{
                chosenIndex: chosenIdx,
                correct: correct,
                timestamp: Date.now()
              }};
              saveProgress(progress);
            }});
            box.appendChild(btn);
            box.appendChild(res);
            mcqWrap.appendChild(box);
          }});
          c7.appendChild(mcqWrap);
        }}

        if (ck.short_answer && ck.short_answer.length) {{
          ck.short_answer.forEach((sq, si) => {{
            const box = document.createElement("div");
            box.className = "quiz-q";
            const h4 = document.createElement("h4");
            h4.textContent = `简答题 ${{si + 1}}：${{sq.question}}`;
            box.appendChild(h4);

            const ta = document.createElement("textarea");
            ta.placeholder = "在这里写下你的回答（建议用自己的话复述，并给出例子）";
            const saved = progress.shortAnswers[lessonId] && progress.shortAnswers[lessonId][String(si)];
            if (saved && typeof saved.answer === "string") ta.value = saved.answer;
            box.appendChild(ta);

            const btnSave = document.createElement("button");
            btnSave.className = "btn primary";
            btnSave.textContent = "保存回答";
            btnSave.addEventListener("click", () => {{
              progress.shortAnswers[lessonId] = progress.shortAnswers[lessonId] || {{}};
              progress.shortAnswers[lessonId][String(si)] = {{
                answer: ta.value,
                timestamp: Date.now()
              }};
              saveProgress(progress);
            }});
            box.appendChild(btnSave);

            if (sq.key_points && sq.key_points.length) {{
              const kp = document.createElement("div");
              kp.className = "result";
              kp.style.color = "var(--muted)";
              kp.textContent = "参考要点：\\n- " + sq.key_points.join("\\n- ");
              box.appendChild(kp);
            }}
            if (sq.rubric && sq.rubric.length) {{
              const rb = document.createElement("div");
              rb.className = "result";
              rb.style.color = "var(--muted)";
              rb.textContent = "自评清单：\\n- " + sq.rubric.join("\\n- ");
              box.appendChild(rb);
            }}
            c7.appendChild(box);
          }});
        }}

        contentEl.appendChild(c7);
      }}

      document.getElementById("btnExportProgress").addEventListener("click", () => {{
        const latest = loadProgress();
        downloadJson(`seer_tutorial_progress_${{exportId}}.json`, {{
          export_id: exportId,
          course_title: pkg.outline.title,
          exported_at: new Date().toISOString(),
          progress: latest
        }});
      }});

      document.getElementById("btnResetProgress").addEventListener("click", () => {{
        localStorage.removeItem(storageKey);
        location.reload();
      }});

      renderNav();
      const firstLesson = (() => {{
        for (const m of pkg.outline.modules) {{
          if (m.lessons && m.lessons.length) return m.lessons[0].id;
        }}
        return null;
      }})();
      const initial = progress.activeLessonId || firstLesson;
      if (initial) setActiveLesson(initial);
      else renderLesson(null);
    }})();
  </script>
</body>
</html>"""

async def generate_offline_course_package(state: TutorialState):
    """
    生成离线教程包的核心逻辑。
    流程：
    1. 检索相关技能 (RAG)。
    2. 生成课程大纲 (CourseOutline)。
    3. 遍历大纲，逐节生成课时内容 (LessonContent)。
    4. 渲染为单个 HTML 文件。
    5. 保存记录并返回下载链接。
    """
    from loguru import logger

    messages = state.get("messages", [])
    last_user_msg = next((m for m in reversed(messages) if isinstance(m, HumanMessage)), None)
    query = last_user_msg.content if last_user_msg else "Generate a learning plan"

    # 1. 检索技能 (已由 SkillInjector 注入)
    skills_context = state.get("skills_context", "")
    used_ids = state.get("used_skill_ids", [])
    
    # 这里的 skills_context 已经是格式化好的 Prompt 字符串
    if not skills_context:
        logger.info("No specific skills found for this task.")

    export_id = str(uuid.uuid4())
    tenant_id = state.get("tenant_id") or "default_tenant"
    user_id = state.get("user_id")

    llm_outline = get_llm(temperature=0.2)
    outline_prompt = f"""你是 Richard Feynman 风格的首席学习顾问。

你要为用户生成一个可执行的学习教程包，最终会被渲染成离线 HTML，用户可以按课时一步步学习并做成果校验。

硬性要求：
1) 先输出课程大纲（CourseOutline），大纲要拆成模块与课时，课时粒度可学习（建议 15-45 分钟/课）。
2) 每个课时必须能独立学习：有类比解释、白话解释、关键术语、常见误解、例子、练习、成果校验。
3) 成果校验必须包含可本地自动评分的选择题（含正确答案索引和解析），以及简答题（含参考要点+自评清单）。
4) 输出必须是结构化数据（严格匹配 schema），不要输出多余文本。

高优先级技能（必须遵守）：
{skills_context}

用户需求：
{query}
"""

    # 2. 生成大纲
    try:
        outline_llm = llm_outline.with_structured_output(CourseOutline)
        course_outline = await outline_llm.ainvoke([SystemMessage(content=outline_prompt)])
    except Exception as e:
        logger.error(f"Failed to generate CourseOutline: {e}")
        return {"messages": [AIMessage(content="生成课程大纲失败，请稍后重试或缩小主题范围。")], "used_skill_ids": used_ids}

    llm_lesson = get_llm(temperature=0.55)
    lesson_llm = llm_lesson.with_structured_output(LessonContent)
    lessons: Dict[str, LessonContent] = {}

    # 3. 逐节生成内容
    for mi, module in enumerate(course_outline.modules):
        for li, lesson in enumerate(module.lessons):
            # 发送进度事件，通知前端当前正在生成哪一节
            await adispatch_custom_event(
                "tutorial_generation_progress",
                {
                    "export_id": export_id,
                    "module_index": mi,
                    "lesson_index": li,
                    "module_title": module.title,
                    "lesson_id": lesson.id,
                    "lesson_title": lesson.title
                }
            )

            prereq = "、".join(course_outline.prerequisites) if course_outline.prerequisites else "无"
            lesson_prompt = f"""你是 Richard Feynman 和 Claude Shannon 一起合作的课程作者。

目标：为离线 HTML 教程包生成一节课的内容。输出必须严格匹配 LessonContent 的结构化 schema，不要输出多余文本。

高优先级技能（必须遵守）：
{skills_context}

课程信息：
- 课程标题：{course_outline.title}
- 学习主题：{course_outline.topic}
- 目标人群：{course_outline.target_audience}
- 先修知识：{prereq}

当前模块：
- 标题：{module.title}
- 目标：{module.goal}

当前课时（必须与大纲一致）：
- id：{lesson.id}
- 标题：{lesson.title}
- 学习目标：{lesson.objective}
- 预计学习分钟：{lesson.estimated_minutes}

硬性要求：
1) 类比解释要贴近日常生活，避免术语堆砌。
2) 白话解释要像讲给 12 岁孩子，句子短，层次清晰。
3) 常见误解至少 3 条（若主题极简单，可 1-2 条）。
4) 例子至少 2 个，最好有一个反例。
5) 练习至少 3 个，且给出提示与参考要点。
6) 成果校验：
   - 选择题 5 题以上，每题给出 options（4 个选项）、answer_index（0-based）、rationale。
   - 简答题 2 题以上，每题给出 key_points 与 rubric（自评清单）。
7) **图片生成提示词 (image_prompt)**：
   - 请构思一张能概括本节课核心概念或类比的插图。
   - 核心原则：涉及到一些用图形展示更容易明白的地方，尽量用图片来展示。
   - 典型场景：如果是语言发音类课程，请生成嘴型发音图；如果是流程类，请生成流程示意图。
   - 提示词必须用英文书写（用于 DALL-E/Stable Diffusion）。
   - 风格：现代扁平化插画 (Modern Flat Illustration)，色彩明亮，易于理解。
   - 示例："A flat illustration showing a water pipe system analogy for electrical voltage and current, clean lines, educational style."
   - 发音示例："A close-up illustration of a mouth shape pronouncing the vowel 'i:', showing tongue position and lip shape, educational medical style."
"""

            try:
                lesson_content = await lesson_llm.ainvoke([SystemMessage(content=lesson_prompt)])
                
                # --- Generate Image if prompt exists ---
                if lesson_content.image_prompt:
                    # Notify frontend that we are generating image (optional, reusing progress event)
                    await adispatch_custom_event(
                        "tutorial_generation_progress",
                        {
                            "export_id": export_id,
                            "module_index": mi,
                            "lesson_index": li,
                            "module_title": module.title,
                            "lesson_id": lesson.id,
                            "lesson_title": lesson.title,
                            "status": "generating_image"
                        }
                    )
                    try:
                        # Invoke tool to generate image
                        b64_img = await generate_image_base64.ainvoke(lesson_content.image_prompt)
                        if b64_img:
                            lesson_content.image_base64 = b64_img
                    except Exception as img_err:
                        logger.error(f"Failed to generate image for lesson {lesson.id}: {img_err}")
                # ---------------------------------------

            except Exception as e:
                logger.error(f"Failed to generate LessonContent ({lesson.id}): {e}")
                lesson_content = LessonContent(
                    id=lesson.id,
                    title=lesson.title,
                    feynman_analogy="",
                    plain_explanation="",
                )

            lessons[lesson.id] = lesson_content

    course_package = OfflineCoursePackage(
        export_id=export_id,
        outline=course_outline,
        lessons=lessons,
        generated_at=datetime.utcnow().isoformat() + "Z",
    )

    # 4. 渲染为 HTML 并保存到磁盘 (或上传到 S3)
    html = _render_offline_course_html(course_package)
    safe_user_id = "".join(ch for ch in (user_id or tenant_id or "unknown") if ch.isalnum() or ch in {"-", "_"})
    
    from server.core.storage import S3Client
    s3_client = S3Client()
    file_url = None
    
    if s3_client.enabled:
        temp_dir = (Path.cwd() / "server" / "data" / "temp").resolve()
        temp_dir.mkdir(parents=True, exist_ok=True)
        filename = f"tutorial_{export_id}.html"
        temp_file_path = temp_dir / filename
        try:
            temp_file_path.write_text(html, encoding="utf-8")
            object_name = f"tutorials/{safe_user_id}/{filename}"
            file_url = s3_client.upload_file(temp_file_path, object_name)
        except Exception as e:
            logger.error(f"Failed to upload tutorial to S3: {e}")
        finally:
            if temp_file_path.exists():
                try:
                    os.remove(temp_file_path)
                except:
                    pass

    if file_url:
        relative_path = file_url
        logger.info(f"Tutorial uploaded to S3: {file_url}")
    else:
        # Fallback to local storage
        export_dir = (Path.cwd() / "server" / "data" / "user_files" / safe_user_id).resolve()
        export_dir.mkdir(parents=True, exist_ok=True)
        filename = f"tutorial_{export_id}.html"
        file_path = (export_dir / filename).resolve()
        file_path.write_text(html, encoding="utf-8")
        relative_path = f"{safe_user_id}/{filename}"
        logger.info(f"Tutorial saved locally: {file_path}")

    # 5. 保存记录到数据库
    try:
        from server.models.tutorial_export import TutorialExport
        from server.models.artifact import AgentArtifact
        from server.core.database import SessionLocal
        async with SessionLocal() as session:
            # Existing TutorialExport
            session.add(
                TutorialExport(
                    id=export_id,
                    tenant_id=tenant_id,
                    user_id=user_id,
                    topic=course_outline.topic,
                    title=course_outline.title,
                    file_path=relative_path,
                )
            )
            # New AgentArtifact
            session.add(
                AgentArtifact(
                    id=str(uuid.uuid4()),
                    tenant_id=tenant_id,
                    user_id=user_id,
                    agent_id="tutorial_generator",
                    type="file", # Storing as file path
                    value=relative_path,
                    title=course_outline.title,
                    description=f"Topic: {course_outline.topic}"
                )
            )
            await session.commit()
    except Exception as e:
        logger.error(f"Failed to persist TutorialExport/AgentArtifact: {e}")

    # 6. 将生成的教程保存为新技能 (Skill Self-Learning)
    try:
        skill_content_str = f"Course Title: {course_outline.title}\n"
        skill_content_str += f"Topic: {course_outline.topic}\n"
        skill_content_str += f"Target Audience: {course_outline.target_audience}\n\n"
        skill_content_str += "Outline:\n"
        
        for mod in course_outline.modules:
            skill_content_str += f"\nModule: {mod.title}\nGoal: {mod.goal}\n"
            for lesson in mod.lessons:
                # Get the detailed content if available
                l_content = lessons.get(lesson.id)
                if l_content:
                    skill_content_str += f"  - Lesson: {lesson.title}\n"
                    skill_content_str += f"    Objective: {lesson.objective}\n"
                    skill_content_str += f"    Explanation: {l_content.plain_explanation[:200]}...\n"
        
        new_skill = SkillCreate(
            name=f"Tutorial: {course_outline.title}",
            description=f"Auto-generated tutorial on {course_outline.topic}",
            category="tutorial",
            level=1,
            content=skill_content_str,
            tags=["generated", "tutorial", course_outline.topic]
        )
        
        await skill_service.create_skill(new_skill)
        logger.info(f"Saved generated tutorial as new skill: {new_skill.name}")

    except Exception as e:
        logger.error(f"Failed to save generated tutorial as skill: {e}")

    download_url = f"/api/v1/agent/tutorial_exports/{export_id}/download"
    
    # 发送完成事件
    await adispatch_custom_event(
        "tutorial_export_ready",
        {
            "export_id": export_id,
            "download_url": download_url,
            "title": course_outline.title
        }
    )

    final_message = AIMessage(
        content=(
            f"离线教程包已生成：{course_outline.title}\n"
            "说明：这是单文件 HTML，打开即可学习；学习记录保存在浏览器本地，可在页面导出 JSON。\n"
            "\n可在「内容广场」中下载该文件。"
        )
    )

    return {
        "messages": [final_message],
        "used_skill_ids": used_ids,
        "export_id": export_id,
        "export_download_url": download_url,
        "course_outline": course_outline,
        "course_package": course_package.model_dump(),
        "results": {
            "generate_content": final_message.content,
            "export_id": export_id,
            "download_url": download_url
        }
    }

async def collect_feedback(state: TutorialState):
    """
    收集用户反馈。
    （目前是占位符，可以扩展为让用户评价生成的教程质量）。
    """
    return {}

tutorial_graph = StateGraph(TutorialState)
tutorial_graph.add_node("load_skills", skill_injector.load_skills_context)
tutorial_graph.add_node("analyze_intent", analyze_intent)
tutorial_graph.add_node("generate_content", generate_offline_course_package)
tutorial_graph.add_node("collect_feedback", collect_feedback)

tutorial_graph.set_entry_point("load_skills")
tutorial_graph.add_edge("load_skills", "analyze_intent")
tutorial_graph.add_edge("analyze_intent", "generate_content")
tutorial_graph.add_edge("generate_content", "collect_feedback")
tutorial_graph.add_edge("collect_feedback", END)
app = tutorial_graph.compile()
