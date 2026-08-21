'use strict';

let lastReloadedRefreshOperationId = 0;

async function openSelectedLink() {
  const item = state.items.find((candidate) => candidate.id === state.selectedItemId);
  if (!item?.link) return;
  const response = await bridgeCall('openExternal', item.link);
  if (!response?.ok) showToast('Link non aperto', response?.message || '');
}

async function markSelectedRead() {
  const item = state.items.find((candidate) => candidate.id === state.selectedItemId);
  if (!item || item.read) return;
  const response = await bridgeCall('markRead', item.sourceId, item.id);
  if (!response?.ok) { showToast('Stato non aggiornato', response?.message || ''); return; }
  item.read = true;
  await loadSnapshot();
  applyFilters();
}

async function syncItemsAfterCompletedRefresh(refreshState) {
  const operationId = Number(refreshState?.operationId) || 0;
  if (
    refreshState?.active
    || operationId <= 0
    || operationId <= lastReloadedRefreshOperationId
  ) return;

  lastReloadedRefreshOperationId = operationId;
  await loadItems({ syncSnapshot: false });
}

function canNavigateArticlesWithArrows(target) {
  if (!els['modal-backdrop'].hidden) return false;
  if (!(target instanceof HTMLElement)) return true;
  if (target.matches('input, textarea, select') || target.isContentEditable) return false;
  const interactive = target.closest('button, a, [role="button"]');
  return !interactive || Boolean(target.closest('.article-row'));
}

async function navigateArticleSelection(direction) {
  const items = state.filteredItems;
  if (!items.length) return;

  const currentIndex = items.findIndex((item) => item.id === state.selectedItemId);
  let nextIndex;
  if (currentIndex < 0) {
    nextIndex = direction > 0 ? 0 : items.length - 1;
  } else {
    nextIndex = Math.max(0, Math.min(items.length - 1, currentIndex + direction));
  }

  if (nextIndex === currentIndex) return;
  await selectArticle(items[nextIndex].id);

  const selectedRow = [...els['article-list'].querySelectorAll('.article-row')]
    .find((row) => row.dataset.itemId === state.selectedItemId);
  if (selectedRow) {
    selectedRow.focus({ preventScroll: true });
    selectedRow.scrollIntoView({ block: 'nearest', behavior: 'auto' });
  }
}

function bindEvents() {
  els['source-nav'].querySelector('[data-scope="all"]').addEventListener('click', () => selectScope('all', '', 'Tutti gli articoli'));
  els['search-input'].addEventListener('input', (event) => { state.search = event.target.value; applyFilters(); });
  els['unread-toggle'].addEventListener('change', async (event) => {
    state.showUnreadOnly = event.target.checked;
    applyFilters();
    if (state.snapshot) {
      const settings = { ...state.snapshot.settings, show_unread_only: state.showUnreadOnly };
      const response = await bridgeCall('saveSettings', JSON.stringify({ show_unread_only: settings.show_unread_only }));
      if (!response?.ok) showToast('Filtro non salvato', response?.message || '');
    }
  });
  els['refresh-all-btn'].addEventListener('click', refreshAll);
  els['add-feed-btn'].addEventListener('click', openAddFeedModal);
  els['settings-btn'].addEventListener('click', openSettingsModal);
  els['refresh-feed-btn'].addEventListener('click', refreshCurrentFeed);
  els['edit-feed-btn'].addEventListener('click', openEditFeedModal);
  els['remove-feed-btn'].addEventListener('click', openRemoveFeedModal);
  els['open-link-btn'].addEventListener('click', openSelectedLink);
  els['mark-read-btn'].addEventListener('click', markSelectedRead);
  els['modal-close'].addEventListener('click', closeModal);
  els['modal-backdrop'].addEventListener('mousedown', (event) => { if (event.target === els['modal-backdrop']) closeModal(); });

  document.addEventListener('keydown', (event) => {
    if (!els['modal-backdrop'].hidden && event.key === 'Tab') {
      const focusable = [...els['modal'].querySelectorAll('button:not(:disabled), input:not(:disabled), select:not(:disabled), textarea:not(:disabled), [tabindex]:not([tabindex="-1"])')];
      if (focusable.length) {
        const first = focusable[0];
        const last = focusable[focusable.length - 1];
        if (event.shiftKey && document.activeElement === first) { event.preventDefault(); last.focus(); }
        else if (!event.shiftKey && document.activeElement === last) { event.preventDefault(); first.focus(); }
      }
    }
    if (event.key === 'Escape' && !els['modal-backdrop'].hidden) { closeModal(); return; }

    if (
      !event.ctrlKey
      && !event.metaKey
      && !event.altKey
      && (event.key === 'ArrowUp' || event.key === 'ArrowDown')
      && canNavigateArticlesWithArrows(event.target)
    ) {
      event.preventDefault();
      void navigateArticleSelection(event.key === 'ArrowDown' ? 1 : -1);
      return;
    }

    if (!(event.ctrlKey || event.metaKey)) return;
    const key = event.key.toLowerCase();
    if (key === 'f') { event.preventDefault(); els['search-input'].focus(); }
    else if (key === 'n') { event.preventDefault(); openAddFeedModal(); }
    else if (key === 'r' && event.shiftKey) { event.preventDefault(); refreshCurrentFeed(); }
    else if (key === 'r') { event.preventDefault(); refreshAll(); }
    else if (key === 'd') { event.preventDefault(); openRemoveFeedModal(); }
    else if (key === 'o') { event.preventDefault(); openSelectedLink(); }
    else if (key === 'm') { event.preventDefault(); markSelectedRead(); }
    else if (key === 'h') { event.preventDefault(); state.backend?.hideApp(); }
    else if (key === 'q') { event.preventDefault(); state.backend?.quitApp(); }
  });

  let resizing = false;
  let pendingWidth = null;
  els['sidebar-resizer'].addEventListener('pointerdown', (event) => { resizing = true; els['sidebar-resizer'].setPointerCapture(event.pointerId); });
  els['sidebar-resizer'].addEventListener('pointermove', (event) => {
    if (!resizing) return;
    const appLeft = document.querySelector('.workspace').getBoundingClientRect().left;
    pendingWidth = Math.max(240, Math.min(480, event.clientX - appLeft));
    document.documentElement.style.setProperty('--sidebar-width', `${pendingWidth}px`);
  });
  els['sidebar-resizer'].addEventListener('pointerup', async () => {
    resizing = false;
    if (pendingWidth !== null) await bridgeCall('setSidebarWidth', Math.round(pendingWidth));
    pendingWidth = null;
  });
  els['sidebar-resizer'].addEventListener('keydown', async (event) => {
    if (!['ArrowLeft','ArrowRight'].includes(event.key)) return;
    event.preventDefault();
    const current = parseInt(getComputedStyle(document.documentElement).getPropertyValue('--sidebar-width'), 10) || 280;
    const next = Math.max(240, Math.min(480, current + (event.key === 'ArrowRight' ? 16 : -16)));
    document.documentElement.style.setProperty('--sidebar-width', `${next}px`);
    await bridgeCall('setSidebarWidth', next);
  });
}

function bindBackendSignals() {
  state.backend.stateChanged.connect((raw) => {
    try {
      const snapshot = JSON.parse(raw);
      applySnapshot(snapshot);
      void syncItemsAfterCompletedRefresh(snapshot?.data?.refreshing);
    }
    catch { /* ignore malformed backend event */ }
  });

  state.backend.refreshFinished.connect(async (raw) => {
    let result = null;
    try { result = JSON.parse(raw); } catch { /* ignore */ }

    if (result?.scope === 'all') {
      const message = result.failed
        ? `${result.success || 0} riusciti, ${result.failed} falliti`
        : `${result.success || 0} feed aggiornati`;
      showToast(
        result.failed ? 'Aggiornamento completato con errori' : 'Aggiornamento completato',
        message
      );
    } else if (result?.scope === 'feed' && !result.ok) {
      showToast('Aggiornamento feed fallito', result.message || '');
    }

    await loadSnapshot();
    await syncItemsAfterCompletedRefresh(state.snapshot?.refreshing);
  });

  state.backend.backendEvent.connect((raw) => {
    try {
      const event = JSON.parse(raw);
      if (event.event === 'feed_refresh_failed') {
        showToast('Feed non aggiornato', event.payload?.error || 'Errore di rete');
      }
    } catch { /* ignore */ }
  });
}

async function start() {
  cacheElements();
  bindEvents();
  if (typeof qt === 'undefined' || typeof QWebChannel === 'undefined') {
    els['app'].setAttribute('aria-busy', 'false');
    showToast('Backend non disponibile', 'Avvia l’interfaccia tramite main.py.');
    return;
  }
  new QWebChannel(qt.webChannelTransport, async (channel) => {
    state.backend = channel.objects.backend;
    bindBackendSignals();
    await loadSnapshot();
    await loadItems();
    els['app'].setAttribute('aria-busy', 'false');
  });
}

document.addEventListener('DOMContentLoaded', start);
