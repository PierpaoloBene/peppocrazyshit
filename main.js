import Chart from 'chart.js/auto';

// ═══════════════════════════════════════════════════════════════
// PeppoCrazyShit — Main SPA Logic
// ═══════════════════════════════════════════════════════════════

// ─── STATE ───
const state = {
  currentPage: 'home',
  charts: {},
  supercazzolaData: null,
  whashabitData: null,
  pilData: null,
  activeParties: new Set(),
};

// ─── DASHBOARD CARDS CONFIG ───
const CARDS = [
  {
    id: 'supercazzola',
    title: 'SuperCazzola\nIndex (WIP)',
    bg: '#FF595E',
    page: 'supercazzola',
  },
  {
    id: 'whashabit',
    title: 'WhasHabits',
    bg: '#4361EE',
    page: 'whashabit',
  },
  {
    id: 'pil',
    title: 'PilLow',
    bg: '#06D6A0',
    page: 'pil',
  },
];

// ─── DOM UTILS ───
const $ = (sel) => document.querySelector(sel);
const $$ = (sel) => document.querySelectorAll(sel);

function showPage(pageId) {
  const doTransition = () => {
    $$('.page').forEach(p => {
      p.classList.remove('active');
      p.hidden = true;
    });
    const target = $(`#page-${pageId}`);
    if (target) {
      target.hidden = false;
      target.classList.add('active');
    }
    state.currentPage = pageId;
  };

  if (document.startViewTransition) {
    document.startViewTransition(doTransition);
  } else {
    doTransition();
  }

  // Accessibility: route focus to the page heading
  setTimeout(() => {
    const heading = $(`#page-${pageId} h1`);
    if (heading) { heading.setAttribute('tabindex', '-1'); heading.focus(); }
  }, 350);
}

// ─── VISITOR COUNTER ───
async function initVisitorCounter() {
  try {
    const res = await fetch('https://api.counterapi.dev/v1/peppocrazyshit/visits/up');
    const data = await res.json();
    $('#total-visits').textContent = data.count.toLocaleString('it-IT');
  } catch (e) {
    console.error('Errore caricamento contatore visite', e);
    $('#total-visits').textContent = '—';
  }
}

// ─── LANDING PAGE CARDS ───
function renderCards() {
  const grid = $('#card-grid');
  if (!grid) return;

  CARDS.forEach(card => {
    const el = document.createElement('article');
    el.className = 'dashboard-card';
    el.setAttribute('role', 'listitem');
    el.setAttribute('tabindex', '0');
    el.setAttribute('aria-label', `Go to: ${card.title.replace('\n', ' ')}`);

    // Title may contain a newline — split into two lines
    const titleParts = card.title.split('\n');
    const titleHTML = titleParts.map(p => `<span>${p}</span>`).join('<br />');

    el.innerHTML = `
      <div class="card-color-area" style="background-color: ${card.bg}">
        <div class="card-big-title">${titleHTML}</div>
      </div>
    `;

    const navigate = () => {
      showPage(card.page);
      loadPageData(card.page);
    };
    el.addEventListener('click', navigate);
    el.addEventListener('keydown', e => { if (e.key === 'Enter' || e.key === ' ') { e.preventDefault(); navigate(); } });

    grid.appendChild(el);
  });
}

// ─── BACK BUTTONS ───
function setupNavigation() {
  ['supercazzola', 'whashabit', 'pil'].forEach(page => {
    const btn = $(`#back-${page}`);
    if (btn) btn.addEventListener('click', () => showPage('home'));
  });
}

// ─── DATA LOADERS ───
async function loadPageData(page) {
  if (page === 'supercazzola' && !state.supercazzolaData) {
    await loadSupercazzola();
  } else if (page === 'whashabit' && !state.whashabitData) {
    await loadWhashabit();
  } else if (page === 'pil' && !state.pilData) {
    await loadPil();
  }
}

// ═══════════════════════════════════════════════════════════════
// ── SUPERCAZZOLA ──
// ═══════════════════════════════════════════════════════════════
async function loadSupercazzola() {
  try {
    const res = await fetch('./data/supercazzola_data.json');
    state.supercazzolaData = await res.json();
    renderSupercazzola();
  } catch (e) {
    console.error('Errore caricamento dati supercazzola', e);
  }
}

function renderSupercazzola() {
  const data = state.supercazzolaData;
  if (!data) return;

  // Update date
  if (data.generated_at) {
    const date = new Date(data.generated_at);
    $('#supercazzola-updated').textContent = `Aggiornato: ${date.toLocaleDateString('it-IT')}`;
  }

  // Party selector
  const selectorEl = $('#party-selector');
  selectorEl.innerHTML = '';
  data.parties.forEach(p => {
    state.activeParties.add(p.id);
    const chip = document.createElement('button');
    chip.className = 'party-chip active';
    chip.textContent = p.id;
    chip.style.borderColor = p.color;
    chip.style.color = p.color;
    chip.setAttribute('aria-pressed', 'true');
    chip.dataset.party = p.id;
    chip.addEventListener('click', () => {
      const isActive = state.activeParties.has(p.id);
      if (isActive) {
        state.activeParties.delete(p.id);
        chip.classList.remove('active');
        chip.setAttribute('aria-pressed', 'false');
      } else {
        state.activeParties.add(p.id);
        chip.classList.add('active');
        chip.setAttribute('aria-pressed', 'true');
      }
      updateRadarChart();
    });
    selectorEl.appendChild(chip);
  });

  // Radar chart
  buildRadarChart(data.parties);

  // Samples
  renderSamples(data.parties);
}

function buildRadarChart(parties) {
  const ctx = $('#radar-chart');
  if (!ctx) return;
  if (state.charts.radar) { state.charts.radar.destroy(); }

  const labels = ['Complessità Periodi', 'Vuoto Semantico', 'Indice di Fuffa', 'Astrazione Concettuale'];

  const datasets = parties.map(p => ({
    label: p.name,
    data: labels.map(l => p.radar[l] ?? 0),
    borderColor: p.color,
    backgroundColor: hexToRgba(p.color, 0.08),
    borderWidth: 2,
    pointBackgroundColor: p.color,
    pointRadius: 4,
    pointHoverRadius: 6,
  }));

  state.charts.radar = new Chart(ctx, {
    type: 'radar',
    data: { labels, datasets },
    options: {
      responsive: true,
      maintainAspectRatio: true,
      animation: { duration: 600, easing: 'easeOutQuart' },
      plugins: {
        legend: {
          display: true,
          position: 'bottom',
          labels: {
            color: '#555555',
            font: { family: "'Inter', sans-serif", size: 11 },
            padding: 16,
            boxWidth: 10,
            boxHeight: 10,
            usePointStyle: true,
          },
        },
        tooltip: {
          backgroundColor: '#111111',
          borderColor: '#333333',
          borderWidth: 1,
          titleColor: '#ffffff',
          bodyColor: '#cccccc',
          callbacks: {
            label: (ctx) => ` ${ctx.dataset.label}: ${ctx.raw.toFixed(1)}/100`,
          },
        },
      },
      scales: {
        r: {
          min: 0,
          max: 100,
          grid: { color: 'rgba(0,0,0,0.08)' },
          angleLines: { color: 'rgba(0,0,0,0.1)' },
          ticks: {
            color: '#999999',
            backdropColor: 'transparent',
            font: { size: 10 },
            stepSize: 25,
          },
          pointLabels: {
            color: '#555555',
            font: { family: "'Inter', sans-serif", size: 11 },
          },
        },
      },
    },
  });
}

function updateRadarChart() {
  const chart = state.charts.radar;
  if (!chart || !state.supercazzolaData) return;
  chart.data.datasets.forEach(ds => {
    const party = state.supercazzolaData.parties.find(p => p.name === ds.label);
    ds.hidden = party ? !state.activeParties.has(party.id) : false;
  });
  chart.update();
}

function renderSamples(parties) {
  const container = $('#supercazzola-samples');
  if (!container) return;
  container.innerHTML = '';

  const allSamples = [];
  parties.forEach(p => {
    (p.top_samples || []).slice(0, 1).forEach(s => {
      allSamples.push({ party: p, sample: s });
    });
  });

  allSamples.slice(0, 4).forEach(({ party, sample }) => {
    const div = document.createElement('div');
    div.className = 'sample-card glass-card';
    const highlighted = highlightPhrases(sample.text, sample.convoluted_phrases || []);
    div.innerHTML = `
      <div class="sample-header">
        <span class="sample-party" style="color: ${party.color}">${party.name}</span>
        <span class="sample-score">Fuffa: ${sample.score.toFixed(0)}</span>
      </div>
      <p class="sample-text">${highlighted}</p>
    `;
    container.appendChild(div);
  });
}

function highlightPhrases(text, phrases) {
  let result = escapeHtml(text);
  if (!phrases || phrases.length === 0) return result;

  phrases.forEach(phrase => {
    // Escape phrase for regex, but allow for some whitespace variation
    const escapedPhrase = escapeRegex(phrase).replace(/\\s+/g, '\\s+');
    const re = new RegExp(`(${escapedPhrase})`, 'gi');
    result = result.replace(re, '<mark>$1</mark>');
  });
  return result;
}

function escapeHtml(text) {
  return text.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function escapeRegex(s) {
  return s.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function hexToRgba(hex, alpha) {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  return `rgba(${r},${g},${b},${alpha})`;
}

// ═══════════════════════════════════════════════════════════════
// ── WHASHABIT ──
// ═══════════════════════════════════════════════════════════════
const FACTIONS = [
  {
    key: 'frontale',
    name: 'La Fazione Frontale',
    emoji: '🚿',
    color: '#FF595E',
    borderColor: '#ffcece',
    desc: 'Spiriti liberi. Affrontano il bidet con la stessa grinta con cui affrontano la vita. Pragmatici del quotidiano. Credono nel contatto diretto con la realtà.',
    sub: null,
  },
  {
    key: 'posteriore',
    name: 'La Fazione Posteriore',
    emoji: '🔄',
    color: '#4361EE',
    borderColor: '#c5ccf5',
    desc: 'Tradizionalisti, metodici, custodi della convenzione. Il bidet è uno strumento, non una metafora. Si siedono — si siedono nel modo giusto.',
    sub: null,
  },
  {
    key: 'altro',
    name: 'Altro',
    emoji: '🌀',
    color: '#06D6A0',
    borderColor: '#a3f0dc',
    desc: 'Una categoria vasta e misteriosa. Comprende:',
    sub: [
      'La Vaschetta: uno strano figuro ha confessato di riempire il bidet di acqua e fare la vasca ai propri genitali.',
      'Anti-Bidet Parties: lo straniero in Italia che continua a non lavarsi il culo come ha sempre fatto 🌍',
    ],
  },
];

async function loadWhashabit() {
  try {
    const res = await fetch('./data/whashabit_data.json');
    const baseData = await res.json();

    state.whashabitData = {
      frontale: baseData.frontale || 0,
      posteriore: baseData.posteriore || 0,
      altro: baseData.altro || 0,
    };

    renderWhashabit();
  } catch (e) {
    console.error('Errore caricamento whashabit', e);
  }
}

function renderWhashabit() {
  const data = state.whashabitData;
  buildWhashabitChart(data);
  renderFactions(data);
  const total = data.frontale + data.posteriore + data.altro;
  $('#whashabit-total').textContent = `${total} risposte totali`;
}

function buildWhashabitChart(data) {
  const ctx = $('#whashabit-chart');
  if (!ctx) return;
  if (state.charts.whashabit) { state.charts.whashabit.destroy(); }

  const labels = ['Frontale 🚿', 'Posteriore 🔄', 'Altro 🌀'];
  const values = [data.frontale, data.posteriore, data.altro];
  const colors = ['#FF595E', '#4361EE', '#06D6A0'];

  state.charts.whashabit = new Chart(ctx, {
    type: 'bar',
    data: {
      labels,
      datasets: [{
        label: 'Persone',
        data: values,
        backgroundColor: colors.map(c => hexToRgba(c, 0.15)),
        borderColor: colors,
        borderWidth: 2.5,
        borderRadius: 8,
        borderSkipped: false,
      }],
    },
    options: {
      responsive: true,
      maintainAspectRatio: false,
      animation: { duration: 800, easing: 'easeOutBounce' },
      plugins: {
        legend: { display: false },
        tooltip: {
          backgroundColor: '#111111',
          borderColor: '#333333',
          borderWidth: 1,
          titleColor: '#ffffff',
          bodyColor: '#cccccc',
          callbacks: {
            label: (ctx) => {
              const total = ctx.dataset.data.reduce((a, b) => a + b, 0);
              const pct = ((ctx.raw / total) * 100).toFixed(1);
              return ` ${ctx.raw} persone (${pct}%)`;
            },
          },
        },
      },
      scales: {
        x: {
          grid: { display: false },
          ticks: { color: '#666666', font: { family: "'Inter', sans-serif" } },
        },
        y: {
          grid: { color: 'rgba(0,0,0,0.06)' },
          ticks: { color: '#999999', font: { family: "'Inter', sans-serif" }, stepSize: 5 },
          beginAtZero: true,
        },
      },
    },
  });
}

function renderFactions(data) {
  const container = $('#factions-list');
  if (!container) return;
  container.innerHTML = '';

  const total = data.frontale + data.posteriore + data.altro;

  FACTIONS.forEach(f => {
    const count = data[f.key] || 0;
    const pct = total > 0 ? ((count / total) * 100).toFixed(1) : '0.0';

    const card = document.createElement('div');
    card.className = 'faction-card';
    card.style.borderColor = f.borderColor;

    let subHTML = '';
    if (f.sub && f.sub.length > 0) {
      subHTML = `<ul class="faction-sub-list">${f.sub.map(s => `<li>${s}</li>`).join('')}</ul>`;
    }

    card.innerHTML = `
      <span class="faction-emoji">${f.emoji}</span>
      <span class="faction-pct" style="color: ${f.color}">${pct}%</span>
      <div class="faction-name" style="color: ${f.color}">${f.name}</div>
      <div class="faction-desc">${f.desc}${subHTML}</div>
    `;
    container.appendChild(card);
  });
}

// ═══════════════════════════════════════════════════════════════
// ── PIL ──
// ═══════════════════════════════════════════════════════════════
async function loadPil() {
  try {
    const res = await fetch('./data/pil_data.json');
    state.pilData = await res.json();
    renderPil();
    startPilTicker();
  } catch (e) {
    console.error('Errore caricamento PIL', e);
  }
}

function renderPil() {
  const data = state.pilData;
  renderRevenuesList(data);
  renderBreakdownList(data);
}

// ─── Floating tooltip singleton ───
let _tooltip = null;
function getTooltip() {
  if (!_tooltip) {
    _tooltip = document.createElement('div');
    _tooltip.className = 'pil-hover-tooltip';
    _tooltip.setAttribute('role', 'tooltip');
    document.body.appendChild(_tooltip);
  }
  return _tooltip;
}

function attachTooltip(el, text) {
  const tip = getTooltip();
  el.addEventListener('mouseenter', (e) => {
    tip.textContent = text;
    tip.classList.add('visible');
    positionTooltip(e);
  });
  el.addEventListener('mousemove', positionTooltip);
  el.addEventListener('mouseleave', () => {
    tip.classList.remove('visible');
  });
}

function positionTooltip(e) {
  const tip = getTooltip();
  const GAP = 12;
  const tw = tip.offsetWidth;
  const th = tip.offsetHeight;
  let x = e.clientX + GAP;
  let y = e.clientY - th / 2;
  // Keep within viewport
  if (x + tw > window.innerWidth - 8) x = e.clientX - tw - GAP;
  if (y < 8) y = 8;
  if (y + th > window.innerHeight - 8) y = window.innerHeight - th - 8;
  tip.style.left = x + 'px';
  tip.style.top  = y + 'px';
}

function renderRevenuesList(data) {
  const container = $('#pil-revenues-list');
  if (!container) return;
  container.innerHTML = '';

  const items    = data.revenues || [];
  const groups   = data.revenue_groups || [];
  const total    = items.reduce((s, c) => s + c.valore_miliardi, 0);

  groups.forEach((group, idx) => {
    const groupItems = items.filter(c => c.group === group.key);

    // ── Group separator header ──
    const header = document.createElement('div');
    header.className = 'revenue-group-header' + (idx > 0 ? ' revenue-group-header--mt' : '');
    header.innerHTML = `
      <span class="revenue-group-label">${group.label}</span>
      <span class="revenue-group-desc">${group.desc}</span>
    `;
    container.appendChild(header);

    if (groupItems.length === 0) {
      const empty = document.createElement('div');
      empty.className = 'revenue-group-empty';
      empty.textContent = 'Dati non riportati separatamente in questo bilancio semplificato.';
      container.appendChild(empty);
      return;
    }

    groupItems.forEach(cat => {
      const pct = ((cat.valore_miliardi / total) * 100).toFixed(1);
      const div = document.createElement('div');
      div.className = 'breakdown-item';
      if (cat.desc) div.classList.add('has-tip');
      div.innerHTML = `
        <span class="breakdown-emoji">${cat.emoji}</span>
        <div class="breakdown-info">
          <div class="breakdown-label">${cat.label}</div>
          <div class="breakdown-value">€${cat.valore_miliardi} Mrd</div>
        </div>
        <div class="breakdown-bar-wrap">
          <div class="breakdown-bar" style="width: ${pct}%; background: ${cat.color}"></div>
        </div>
        <span class="breakdown-pct" style="color: ${cat.color}">${pct}%</span>
      `;
      if (cat.desc) attachTooltip(div, cat.desc);
      container.appendChild(div);
    });
  });
}


function renderBreakdownList(data) {
  const container = $('#pil-breakdown-list');
  if (!container) return;
  container.innerHTML = '';

  const total = data.categories.reduce((s, c) => s + c.valore_miliardi, 0);

  data.categories.forEach(cat => {
    const pct = ((cat.valore_miliardi / total) * 100).toFixed(1);
    const div = document.createElement('div');
    div.className = 'breakdown-item';
    if (cat.desc) div.classList.add('has-tip');
    div.innerHTML = `
      <span class="breakdown-emoji">${cat.emoji}</span>
      <div class="breakdown-info">
        <div class="breakdown-label">${cat.label}</div>
        <div class="breakdown-value">€${cat.valore_miliardi} Mrd</div>
      </div>
      <div class="breakdown-bar-wrap">
        <div class="breakdown-bar" style="width: ${pct}%; background: ${cat.color}"></div>
      </div>
      <span class="breakdown-pct" style="color: ${cat.color}">${pct}%</span>
    `;
    if (cat.desc) attachTooltip(div, cat.desc);
    container.appendChild(div);
  });
}


let pilTickerInterval = null;
function startPilTicker() {
  const data = state.pilData;
  if (!data || pilTickerInterval) return;

  // Calculate base values in euros
  const BASE_GDP = data.total_pil * 1e9;
  const DEBT_MS = data.total_debt * 1e9;
  const BASE_SPEND = data.total_spending * 1e9;

  const MS_PER_YEAR = 365.25 * 24 * 60 * 60 * 1000;
  
  // Calculate per-millisecond growth (assuming 1% GDP growth, 2.5% debt, 1.5% spending)
  const GDP_GROWTH_MS = (BASE_GDP * 0.01) / MS_PER_YEAR;
  const DEBT_GROWTH_MS = (DEBT_MS * 0.025) / MS_PER_YEAR;
  const SPEND_GROWTH_MS = (BASE_SPEND * 0.015) / MS_PER_YEAR;

  // Offset within the current year for the live effect
  const yearStart = new Date(new Date().getFullYear(), 0, 1).getTime();
  const elapsed = Date.now() - yearStart; 

  let gdp = BASE_GDP + GDP_GROWTH_MS * elapsed;
  let debt = DEBT_MS + DEBT_GROWTH_MS * elapsed;
  let spend = BASE_SPEND + SPEND_GROWTH_MS * elapsed;

  const gdpEl = $('#gdp-ticker');
  const debtEl = $('#debt-ticker');
  const spendEl = $('#spend-ticker');

  function fmt(n) {
    if (n >= 1e12) return `€ ${(n / 1e12).toFixed(3)} Tri`;
    if (n >= 1e9) return `€ ${(n / 1e9).toFixed(2)} Mrd`;
    if (n >= 1e6) return `€ ${(n / 1e6).toFixed(1)} Mln`;
    return `€ ${Math.round(n).toLocaleString('it-IT')}`;
  }

  const TICK_MS = 100;
  pilTickerInterval = setInterval(() => {
    gdp += GDP_GROWTH_MS * TICK_MS;
    debt += DEBT_GROWTH_MS * TICK_MS;
    spend += SPEND_GROWTH_MS * TICK_MS;

    if (gdpEl) gdpEl.textContent = fmt(gdp);
    if (debtEl) debtEl.textContent = fmt(debt);
    if (spendEl) spendEl.textContent = fmt(spend);
  }, TICK_MS);
}

// ═══════════════════════════════════════════════════════════════
// ── INIT ──
// ═══════════════════════════════════════════════════════════════
function init() {
  renderCards();
  setupNavigation();
  initVisitorCounter();

  // Ensure home page is active on load
  showPage('home');
}

document.addEventListener('DOMContentLoaded', init);
