'use strict';

const state = {
  backend: null,
  snapshot: null,
  scope: { type: 'all', id: '', title: 'Tutti gli articoli' },
  items: [],
  filteredItems: [],
  selectedItemId: null,
  search: '',
  showUnreadOnly: false,
  refresh: {
    running: false,
    current: 0,
    total: 0,
    manualSeenRunning: false,
    hideTimer: null,
  },
  modalReturnFocus: null,
};

let refreshPollTimer = null;

const $ = (id) => document.getElementById(id);
const els = {};
const ICONS = {
  feed: '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M5 4h14v16H5zM8 8h8M8 12h8M8 16h5"/></svg>',
  folder: '<svg class="icon" viewBox="0 0 24 24" aria-hidden="true"><path d="M3 6h7l2 2h9v10H3z"/></svg>',
};

function cacheElements() {
  [
    'app','app-name','scope-caption','search-input','refresh-all-btn','settings-btn','refresh-track','refresh-fill',
    'source-panel','source-nav','category-list','feed-list','all-unread','feed-actions','selected-feed-title','selected-feed-status',
    'add-feed-btn','refresh-feed-btn','edit-feed-btn','remove-feed-btn','sidebar-resizer','content-title','content-meta','unread-toggle',
    'article-list','article-empty','article-detail','detail-placeholder','detail-content','detail-source','detail-date','detail-title','detail-author',
    'detail-summary','open-link-btn','mark-read-btn','modal-backdrop','modal','modal-eyebrow','modal-title','modal-body','modal-actions','modal-close','toast-region'
  ].forEach((id) => { els[id] = $(id); });
}

function bridgeCall(method, ...args) {
  return new Promise((resolve) => {
    if (!state.backend || typeof state.backend[method] !== 'function') {
      resolve({ ok: false, message: 'Bridge Python non disponibile' });
      return;
    }
    state.backend[method](...args, (raw) => {
      if (typeof raw !== 'string') { resolve(raw); return; }
      try { resolve(JSON.parse(raw)); }
      catch { resolve({ ok: false, message: 'Risposta backend non valida' }); }
    });
  });
}

function formatDate(iso, includeTime = true) {
  if (!iso) return 'Mai';
  const date = new Date(iso);
  if (Number.isNaN(date.getTime())) return '';
  return new Intl.DateTimeFormat('it-IT', includeTime
    ? { day: '2-digit', month: 'short', hour: '2-digit', minute: '2-digit' }
    : { day: '2-digit', month: 'long', year: 'numeric' }).format(date);
}

function relativeDate(iso) {
  if (!iso) return '';
  const date = new Date(iso);
  const delta = Date.now() - date.getTime();
  const mins = Math.max(0, Math.floor(delta / 60000));
  if (mins < 1) return 'adesso';
  if (mins < 60) return `${mins} min`;
  const hours = Math.floor(mins / 60);
  if (hours < 24) return `${hours} h`;
  return formatDate(iso, false);
}

function showToast(title, message = '') {
  const toast = document.createElement('div');
  toast.className = 'toast';
  const strong = document.createElement('strong');
  strong.textContent = title;
  toast.appendChild(strong);
  if (message) {
    const text = document.createElement('span');
    text.textContent = message;
    toast.appendChild(text);
  }
  els['toast-region'].appendChild(toast);
  window.setTimeout(() => toast.remove(), 3600);
}

function scheduleRefreshStatePoll(active) {
  if (refreshPollTimer !== null) {
    window.clearTimeout(refreshPollTimer);
    refreshPollTimer = null;
  }
  if (!active) return;

  refreshPollTimer = window.setTimeout(async () => {
    refreshPollTimer = null;
    const response = await bridgeCall('getSnapshot');
    if (response?.ok) applySnapshot(response);
  }, 200);
}

function scheduleRefreshHide() {
  if (state.refresh.hideTimer !== null) return;
  state.refresh.hideTimer = window.setTimeout(() => {
    const backendBusy = Boolean(
      state.snapshot?.refreshing?.all
      || state.snapshot?.refreshing?.feeds?.length
    );
    if (!backendBusy) {
      state.refresh.running = false;
      state.refresh.manualSeenRunning = false;
      state.refresh.hideTimer = null;
      updateRefreshProgress();
    } else {
      state.refresh.hideTimer = null;
    }
  }, 450);
}

function applySnapshot(snapshot) {
  if (!snapshot?.ok) {
    showToast('Errore', snapshot?.message || 'Impossibile leggere lo stato');
    return;
  }
  state.snapshot = snapshot.data;
  state.showUnreadOnly = Boolean(snapshot.data.settings.show_unread_only);
  els['unread-toggle'].checked = state.showUnreadOnly;
  els['app-name'].textContent = snapshot.data.app.name;

  const refreshState = snapshot.data.refreshing || {
    all: false,
    manualAll: false,
    current: 0,
    total: 0,
    feeds: [],
  };
  const backendGlobalRunning = Boolean(refreshState.all);
  const backendManualRunning = Boolean(refreshState.manualAll);
  const backendBusy = backendGlobalRunning || (refreshState.feeds || []).length > 0;

  if (backendManualRunning) {
    if (state.refresh.hideTimer !== null) {
      window.clearTimeout(state.refresh.hideTimer);
      state.refresh.hideTimer = null;
    }
    state.refresh.running = true;
    state.refresh.manualSeenRunning = true;
    const backendTotal = Math.max(0, Number(refreshState.total) || 0);
    const backendCurrent = Math.max(0, Number(refreshState.current) || 0);
    if (backendTotal > 0) state.refresh.total = backendTotal;
    state.refresh.current = Math.max(
      Number(state.refresh.current) || 0,
      Math.min(state.refresh.total, backendCurrent)
    );
    updateRefreshProgress();
  } else if (
    state.refresh.running
    && state.refresh.manualSeenRunning
    && !backendGlobalRunning
  ) {
    state.refresh.current = state.refresh.total;
    updateRefreshProgress();
    scheduleRefreshHide();
  }

  els['refresh-all-btn'].disabled = backendBusy;
  scheduleRefreshStatePoll(backendBusy);

  document.documentElement.style.setProperty('--font-scale', String(snapshot.data.settings.font_scale_factor || 1));
  document.documentElement.style.setProperty('--sidebar-width', `${Math.max(240, Math.min(480, snapshot.data.settings.source_split_width || 280))}px`);
  renderSources();
  renderSelectedFeedActions();
}

async function loadSnapshot({ reloadItems = false } = {}) {
  const response = await bridgeCall('getSnapshot');
  applySnapshot(response);
  if (reloadItems) await loadItems();
}

async function loadItems({ syncSnapshot = true } = {}) {
  const response = await bridgeCall('getItems', state.scope.type, state.scope.id, 300);
  if (!response?.ok) {
    showToast('Articoli non disponibili', response?.message || 'Errore sconosciuto');
    return;
  }
  state.items = response.data || [];
  if (state.selectedItemId && !state.items.some((item) => item.id === state.selectedItemId)) state.selectedItemId = null;

  if (syncSnapshot) {
    const snapshot = await bridgeCall('getSnapshot');
    if (snapshot?.ok) applySnapshot(snapshot);
  }

  applyFilters();
}

function applyFilters() {
  const query = state.search.trim().toLocaleLowerCase('it');
  state.filteredItems = state.items.filter((item) => {
    if (state.showUnreadOnly && item.read) return false;
    if (!query) return true;
    return [item.title, item.sourceTitle, item.summary, item.author]
      .filter(Boolean)
      .some((value) => value.toLocaleLowerCase('it').includes(query));
  });
  renderArticles();
  renderHeader();
}

function renderHeader() {
  els['scope-caption'].textContent = state.scope.title;
  els['content-title'].textContent = state.scope.title;
  const visible = state.filteredItems.length;
  const total = state.items.length;
  els['content-meta'].textContent = state.search || state.showUnreadOnly
    ? `${visible} di ${total} articoli`
    : `${total} ${total === 1 ? 'articolo' : 'articoli'}`;
}

function navButton({ scope, id, title, count, icon }) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = 'source-row';
  if (state.scope.type === scope && state.scope.id === id) button.classList.add('selected');
  button.dataset.scope = scope;
  button.dataset.id = id;
  button.setAttribute('aria-current', button.classList.contains('selected') ? 'page' : 'false');

  const iconWrap = document.createElement('span');
  iconWrap.className = 'source-icon';
  iconWrap.innerHTML = ICONS[icon];
  const label = document.createElement('span');
  label.className = 'source-label';
  label.textContent = title;
  const badge = document.createElement('span');
  badge.className = 'count-badge';
  badge.textContent = String(count ?? 0);
  button.append(iconWrap, label, badge);
  button.addEventListener('click', () => selectScope(scope, id, title));
  return button;
}

function renderSources() {
  if (!state.snapshot) return;
  els['all-unread'].textContent = String(state.snapshot.unreadCount || 0);
  const allButton = els['source-nav'].querySelector('[data-scope="all"]');
  allButton.classList.toggle('selected', state.scope.type === 'all');
  allButton.setAttribute('aria-current', state.scope.type === 'all' ? 'page' : 'false');

  els['category-list'].replaceChildren();
  for (const category of state.snapshot.categories) {
    const feeds = state.snapshot.feeds.filter((feed) => feed.category === category);
    const unread = feeds.reduce((sum, feed) => sum + feed.unreadCount, 0);
    els['category-list'].appendChild(navButton({ scope: 'category', id: category, title: category, count: unread, icon: 'folder' }));
  }

  els['feed-list'].replaceChildren();
  for (const feed of state.snapshot.feeds) {
    els['feed-list'].appendChild(navButton({ scope: 'feed', id: feed.id, title: feed.title, count: feed.unreadCount, icon: 'feed' }));
  }
}

async function selectScope(type, id, title) {
  state.scope = { type, id, title };
  state.selectedItemId = null;
  renderSources();
  renderSelectedFeedActions();
  clearDetail();
  await loadItems();
}

function selectedFeed() {
  if (!state.snapshot || state.scope.type !== 'feed') return null;
  return state.snapshot.feeds.find((feed) => feed.id === state.scope.id) || null;
}

function renderSelectedFeedActions() {
  const feed = selectedFeed();
  els['feed-actions'].hidden = !feed;
  if (!feed) return;
  els['selected-feed-title'].textContent = feed.title;
  if (feed.lastError) els['selected-feed-status'].textContent = `Errore: ${feed.lastError}`;
  else els['selected-feed-status'].textContent = feed.lastUpdated ? `Aggiornato ${formatDate(feed.lastUpdated)}` : 'Mai aggiornato';
  const refreshing = Boolean(state.snapshot?.refreshing?.all || state.snapshot?.refreshing?.feeds?.includes(feed.id));
  els['refresh-feed-btn'].disabled = refreshing;
  els['refresh-feed-btn'].textContent = refreshing ? 'In corso…' : 'Aggiorna';
}