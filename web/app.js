(() => {
  "use strict";

  const DATA = window.DEMO_DATA;
  const COLORS = {
    dijkstra: "#6c757d",
    astar: "#0072b2",
    mxa_full: "#d55e00",
    mxa_id: "#0b7a4b",
  };
  const PROPOSED = "mxa_id";
  const CANVAS_SIZE = 640;
  const TICK_MS = 75;

  const state = {
    scenarioIndex: 0,
    step: 0,
    maxStep: 0,
    playing: false,
    speed: 2,
    showTruth: false,
    panels: [],
    raf: null,
    lastTs: null,
    accumulator: 0,
  };

  const els = {
    scenario: document.getElementById("scenario"),
    scenarioSubtitle: document.getElementById("scenario-subtitle"),
    play: document.getElementById("play"),
    stepBack: document.getElementById("step-back"),
    stepForward: document.getElementById("step-forward"),
    reset: document.getElementById("reset"),
    speed: document.getElementById("speed"),
    speedValue: document.getElementById("speed-value"),
    truth: document.getElementById("truth"),
    progress: document.getElementById("progress"),
    panels: document.getElementById("panels"),
    metricsBody: document.getElementById("metrics-body"),
  };

  if (!DATA || !Array.isArray(DATA.scenarios) || DATA.scenarios.length === 0) {
    els.panels.innerHTML =
      '<p class="note">demo_data.js is missing or empty. Run <code>python experiments/export_demo.py</code> first.</p>';
    return;
  }

  function clamp(value, lo, hi) {
    return Math.max(lo, Math.min(hi, value));
  }

  function formatInt(value) {
    return String(Math.round(value));
  }

  function formatCost(value) {
    return Number.isFinite(value) ? value.toFixed(2) : "—";
  }

  function buildFrameIndex(frames) {
    const maxE = frames.reduce((m, f) => Math.max(m, f.e), 0);
    const at = new Array(maxE + 1).fill(null);
    let fi = 0;
    for (let e = 0; e <= maxE; e += 1) {
      while (fi + 1 < frames.length && frames[fi + 1].e <= e) fi += 1;
      if (frames[fi] && frames[fi].e <= e) at[e] = frames[fi];
    }
    return { at, maxE };
  }

  function populateScenarios() {
    els.scenario.innerHTML = DATA.scenarios
      .map(
        (scenario, index) => `<option value="${index}">${scenario.title}</option>`
      )
      .join("");
  }

  function makePanel(algorithm) {
    const color = COLORS[algorithm.key] || "#0072b2";
    const article = document.createElement("article");
    article.className = "panel" + (algorithm.key === PROPOSED ? " proposed" : "");

    const head = document.createElement("div");
    head.className = "panel-head";
    head.innerHTML = `
      <div class="panel-title">
        <span class="dot" style="background:${color}"></span>
        <h3>${algorithm.name}</h3>
        ${algorithm.key === PROPOSED ? '<span class="tag">proposed</span>' : ""}
      </div>
      <span class="status" data-status>ready</span>
    `;

    const canvasWrap = document.createElement("div");
    canvasWrap.className = "canvas-wrap";
    const canvas = document.createElement("canvas");
    canvas.width = CANVAS_SIZE;
    canvas.height = CANVAS_SIZE;
    canvas.setAttribute(
      "aria-label",
      `${algorithm.name} exploration trace. ${algorithm.metrics.explorations} explorations, optimal cost ${algorithm.metrics.cost.toFixed(2)}.`
    );
    canvasWrap.appendChild(canvas);

    const metrics = document.createElement("div");
    metrics.className = "panel-metrics";
    metrics.innerHTML = `
      <div class="metric"><small>Explored</small><strong data-metric="explored">0</strong></div>
      <div class="metric"><small>Obstacles found</small><strong data-metric="blocked">0</strong></div>
      <div class="metric"><small>Expanded</small><strong data-metric="expanded">0</strong></div>
      <div class="metric"><small>Frontier</small><strong data-metric="frontier">0</strong></div>
    `;

    const foot = document.createElement("div");
    foot.className = "panel-foot";
    foot.innerHTML = `
      <span>Path cost <code data-metric="cost">—</code></span>
      <span>Path length <code data-metric="pathlen">—</code></span>
    `;

    article.append(head, canvasWrap, metrics, foot);
    els.panels.appendChild(article);

    const metricEls = {};
    article.querySelectorAll("[data-metric]").forEach((el) => {
      metricEls[el.dataset.metric] = el;
    });

    return {
      key: algorithm.key,
      name: algorithm.name,
      color,
      data: algorithm,
      canvas,
      ctx: canvas.getContext("2d", { alpha: false }),
      status: article.querySelector("[data-status]"),
      metricEls,
      frameAt: algorithm.frames,
      maxE: algorithm.frames.length
        ? algorithm.frames[algorithm.frames.length - 1].e
        : 0,
      actualBlocked: null,
    };
  }

  function loadScenario(index) {
    pause();
    state.scenarioIndex = index;
    state.step = 0;
    state.lastTs = null;
    state.accumulator = 0;

    const scenario = DATA.scenarios[index];
    els.scenario.value = String(index);
    els.scenarioSubtitle.textContent = `${scenario.title} · ${scenario.subtitle}`;
    els.panels.innerHTML = "";
    state.panels = scenario.algorithms.map((algorithm) => {
      const panel = makePanel(algorithm);
      const built = buildFrameIndex(algorithm.frames);
      panel.frameAt = built.at;
      panel.maxE = built.maxE;
      panel.actualBlocked = scenario.grid.actual_blocked;
      return panel;
    });
    state.maxStep = state.panels.reduce((m, p) => Math.max(m, p.maxE), 0);
    buildComparisonTable(scenario);
    draw();
  }

  function buildComparisonTable(scenario) {
    const astar = scenario.algorithms.find((a) => a.key === "astar");
    const astarExplorations = astar ? astar.metrics.explorations : 0;
    els.metricsBody.innerHTML = scenario.algorithms
      .map((algorithm) => {
        const m = algorithm.metrics;
        let deltaText = "—";
        let deltaClass = "neutral";
        if (astar && algorithm.key !== "astar" && astarExplorations > 0) {
          const delta = ((m.explorations - astarExplorations) / astarExplorations) * 100;
          const sign = delta < 0 ? "\u2212" : "+";
          deltaText = `${sign}${Math.abs(delta).toFixed(1)}%`;
          deltaClass = delta < -0.05 ? "better" : delta > 0.05 ? "worse" : "neutral";
        }
        const proposed = algorithm.key === PROPOSED;
        return `
          <tr class="${proposed ? "proposed-row" : ""}">
            <td>${algorithm.name}${proposed ? " <span class=\"tag\">proposed</span>" : ""}</td>
            <td class="num">${formatInt(m.explorations)}</td>
            <td class="num">${formatInt(m.expansions)}</td>
            <td class="num">${formatCost(m.cost)}</td>
            <td class="num">${m.runtime_ms.toFixed(1)}</td>
            <td class="num ${deltaClass}">${deltaText}</td>
          </tr>
        `;
      })
      .join("");
  }

  function drawStar(ctx, cx, cy, outer, inner) {
    ctx.beginPath();
    for (let i = 0; i < 10; i += 1) {
      const radius = i % 2 === 0 ? outer : inner;
      const angle = -Math.PI / 2 + (i * Math.PI) / 5;
      const x = cx + Math.cos(angle) * radius;
      const y = cy + Math.sin(angle) * radius;
      if (i === 0) ctx.moveTo(x, y);
      else ctx.lineTo(x, y);
    }
    ctx.closePath();
  }

  function drawPanel(panel) {
    const scenario = DATA.scenarios[state.scenarioIndex];
    const width = scenario.grid.width;
    const height = scenario.grid.height;
    const ctx = panel.ctx;
    const size = CANVAS_SIZE;
    const cell = Math.max(1, Math.floor(size / Math.max(width, height)));
    const gridW = cell * width;
    const gridH = cell * height;
    const originX = Math.floor((size - gridW) / 2);
    const originY = Math.floor((size - gridH) / 2);

    const stepForPanel = Math.min(state.step, panel.maxE);
    const frame = panel.frameAt[stepForPanel] || null;
    const eCount = frame ? frame.e : 0;
    const bCount = frame ? frame.b : 0;
    const finished = state.step >= panel.maxE;

    const explored = panel.data.explored;
    const blocked = panel.data.blocked;
    const blockedSet = new Set(blocked.slice(0, bCount));
    const openSet = new Set(frame ? frame.o : []);

    ctx.fillStyle = "#e9ecef";
    ctx.fillRect(0, 0, size, size);

    // A faint cell grid makes the unknown region readable before playback.
    ctx.strokeStyle = "rgba(21, 32, 51, 0.055)";
    ctx.lineWidth = 1;
    ctx.beginPath();
    for (let x = 0; x <= width; x += 1) {
      const px = originX + x * cell + 0.5;
      ctx.moveTo(px, originY);
      ctx.lineTo(px, originY + gridH);
    }
    for (let y = 0; y <= height; y += 1) {
      const py = originY + y * cell + 0.5;
      ctx.moveTo(originX, py);
      ctx.lineTo(originX + gridW, py);
    }
    ctx.stroke();

    // Optional ground truth: faint outlines for every actual obstacle, so a
    // viewer can see what was hidden. Discovered obstacles are still drawn in
    // solid black below.
    if (state.showTruth) {
      ctx.fillStyle = "rgba(33, 37, 41, 0.10)";
      for (const v of panel.actualBlocked || []) {
        const x = v % width;
        const y = Math.floor(v / width);
        ctx.fillRect(originX + x * cell, originY + y * cell, cell, cell);
      }
    }

    // Explored cells, in discovery order.
    for (let i = 0; i < eCount; i += 1) {
      const v = explored[i];
      const x = v % width;
      const y = Math.floor(v / width);
      ctx.fillStyle = blockedSet.has(v) ? "#212529" : "#74c0fc";
      ctx.fillRect(originX + x * cell, originY + y * cell, cell, cell);
    }

    // Current OPEN frontier: a small inset marker so it remains visible even
    // when it sits on top of an explored cell that was reopened.
    if (frame) {
      ctx.fillStyle = "rgba(255, 193, 7, 0.92)";
      const inset = Math.max(1, Math.round(cell * 0.22));
      const side = Math.max(2, cell - 2 * inset);
      for (const v of openSet) {
        const x = v % width;
        const y = Math.floor(v / width);
        ctx.fillRect(originX + x * cell + inset, originY + y * cell + inset, side, side);
      }
    }

    // The last explored cell.
    if (eCount > 0 && !finished) {
      const current = explored[eCount - 1];
      const x = current % width;
      const y = Math.floor(current / width);
      ctx.strokeStyle = "#e03131";
      ctx.lineWidth = Math.max(1.5, cell * 0.13);
      ctx.strokeRect(
        originX + x * cell + 1.5,
        originY + y * cell + 1.5,
        cell - 3,
        cell - 3
      );
    }

    // Final path, drawn once this algorithm has finished its exploration.
    if (finished && panel.data.path.length > 0) {
      const path = panel.data.path;
      const points = path.map((v) => {
        const x = v % width;
        const y = Math.floor(v / width);
        return {
          x: originX + (x + 0.5) * cell,
          y: originY + (y + 0.5) * cell,
        };
      });
      ctx.lineCap = "round";
      ctx.lineJoin = "round";
      ctx.beginPath();
      ctx.moveTo(points[0].x, points[0].y);
      for (let i = 1; i < points.length; i += 1) ctx.lineTo(points[i].x, points[i].y);
      ctx.strokeStyle = "rgba(255, 255, 255, 0.88)";
      ctx.lineWidth = Math.max(3.0, cell * 0.46);
      ctx.stroke();
      ctx.strokeStyle = "#2b8a3e";
      ctx.lineWidth = Math.max(1.4, cell * 0.23);
      ctx.stroke();
    }

    // Start and goal are always known to the agent.
    const startX = originX + (scenario.grid.start % width + 0.5) * cell;
    const startY = originY + (Math.floor(scenario.grid.start / width) + 0.5) * cell;
    ctx.beginPath();
    ctx.arc(startX, startY, Math.max(2.6, cell * 0.32), 0, Math.PI * 2);
    ctx.fillStyle = "#2f9e44";
    ctx.fill();
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = Math.max(1, cell * 0.08);
    ctx.stroke();

    const goalX = originX + (scenario.grid.goal % width + 0.5) * cell;
    const goalY = originY + (Math.floor(scenario.grid.goal / width) + 0.5) * cell;
    drawStar(ctx, goalX, goalY, Math.max(4.0, cell * 0.5), Math.max(2.0, cell * 0.22));
    ctx.fillStyle = "#f08c00";
    ctx.fill();
    ctx.strokeStyle = "#ffffff";
    ctx.lineWidth = Math.max(1, cell * 0.08);
    ctx.stroke();

    const exploredValue = frame ? frame.e : 0;
    const blockedValue = frame ? frame.b : 0;
    const expandedValue = frame ? frame.x : 0;
    const frontierValue = frame ? frame.o.length : 0;
    panel.metricEls.explored.textContent = formatInt(exploredValue);
    panel.metricEls.blocked.textContent = formatInt(blockedValue);
    panel.metricEls.expanded.textContent = formatInt(expandedValue);
    panel.metricEls.frontier.textContent = formatInt(frontierValue);
    panel.metricEls.cost.textContent = finished ? formatCost(panel.data.metrics.cost) : "—";
    panel.metricEls.pathlen.textContent = finished ? formatInt(panel.data.metrics.path_len) : "—";

    panel.status.textContent = finished ? "done" : state.step === 0 ? "ready" : "searching";
    panel.status.classList.toggle("done", finished);
  }

  function draw() {
    for (const panel of state.panels) drawPanel(panel);
    const shown = Math.min(state.step, state.maxStep);
    els.progress.textContent = `${formatInt(shown)} / ${formatInt(state.maxStep)}`;
  }

  function updatePlayButton() {
    els.play.textContent = state.playing ? "Pause" : "Play";
    els.play.setAttribute("aria-pressed", state.playing ? "true" : "false");
  }

  function tick(timestamp) {
    if (!state.playing) return;
    if (state.lastTs === null) state.lastTs = timestamp;
    const elapsed = timestamp - state.lastTs;
    state.lastTs = timestamp;
    state.accumulator += elapsed;

    if (state.accumulator >= TICK_MS) {
      state.accumulator = 0;
      state.step = Math.min(state.maxStep, state.step + state.speed);
      draw();
      if (state.step >= state.maxStep) {
        state.playing = false;
        updatePlayButton();
        return;
      }
    }
    state.raf = requestAnimationFrame(tick);
  }

  function play() {
    if (state.playing) return;
    if (state.step >= state.maxStep) state.step = 0;
    state.playing = true;
    state.lastTs = null;
    state.accumulator = 0;
    updatePlayButton();
    draw();
    state.raf = requestAnimationFrame(tick);
  }

  function pause() {
    if (state.raf !== null) {
      cancelAnimationFrame(state.raf);
      state.raf = null;
    }
    state.playing = false;
    updatePlayButton();
  }

  function togglePlay() {
    if (state.playing) pause();
    else play();
  }

  function stepBy(delta) {
    pause();
    state.step = clamp(state.step + delta, 0, state.maxStep);
    draw();
  }

  function reset() {
    pause();
    state.step = 0;
    state.lastTs = null;
    state.accumulator = 0;
    draw();
  }

  function bindControls() {
    els.play.addEventListener("click", togglePlay);
    els.stepBack.addEventListener("click", () => stepBy(-1));
    els.stepForward.addEventListener("click", () => stepBy(1));
    els.reset.addEventListener("click", reset);
    els.speed.addEventListener("input", () => {
      state.speed = Number(els.speed.value);
      els.speedValue.textContent = `${state.speed}\u00d7`;
    });
    els.truth.addEventListener("change", () => {
      state.showTruth = els.truth.checked;
      draw();
    });
    els.scenario.addEventListener("change", () => {
      loadScenario(Number(els.scenario.value));
    });
    document.addEventListener("keydown", (event) => {
      const tag = (event.target && event.target.tagName) || "";
      if (tag === "SELECT" || tag === "INPUT" || tag === "TEXTAREA") return;
      if (event.code === "Space") {
        event.preventDefault();
        togglePlay();
      } else if (event.code === "ArrowRight") {
        event.preventDefault();
        stepBy(1);
      } else if (event.code === "ArrowLeft") {
        event.preventDefault();
        stepBy(-1);
      }
    });
  }

  populateScenarios();
  bindControls();
  loadScenario(0);
  updatePlayButton();
})();
