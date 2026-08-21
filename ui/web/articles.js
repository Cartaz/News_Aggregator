'use strict';

function renderArticles() {
  els['article-list'].replaceChildren();
  els['article-empty'].hidden = state.filteredItems.length > 0;
  for (const item of state.filteredItems) {
    const row = document.createElement('button');
    row.type = 'button';
    row.className = `article-row${item.read ? ' read' : ''}${item.id === state.selectedItemId ? ' selected' : ''}`;
    row.setAttribute('role', 'option');
    row.setAttribute('aria-selected', item.id === state.selectedItemId ? 'true' : 'false');
    row.dataset.itemId = item.id;

    const title = document.createElement('span');
    title.className = 'article-title';
    title.textContent = item.title || 'Senza titolo';
    const marker = document.createElement('span');
    if (!item.read) marker.className = 'unread-dot';
    const source = document.createElement('span');
    source.className = 'article-source';
    source.textContent = item.sourceTitle;
    const time = document.createElement('span');
    time.className = 'article-time';
    time.textContent = relativeDate(item.published);
    row.append(title, marker, source, time);
    row.addEventListener('click', () => selectArticle(item.id));
    els['article-list'].appendChild(row);
  }
  const current = state.filteredItems.find((item) => item.id === state.selectedItemId);
  if (current) renderDetail(current);
  else clearDetail();
}

async function selectArticle(itemId) {
  const previousItemId = state.selectedItemId;
  if (previousItemId === itemId) return;

  const previousItem = state.items.find(
    (candidate) => candidate.id === previousItemId
  );
  const item = state.items.find((candidate) => candidate.id === itemId);
  if (!item) return;

  // Keep the article currently being read unread. The previous article is
  // marked read only when the user moves to another item. This prevents the
  // active article from disappearing immediately with the unread-only filter.
  state.selectedItemId = itemId;
  renderArticles();

  if (
    previousItem
    && !previousItem.read
    && state.snapshot?.settings?.mark_read_on_select
  ) {
    const response = await bridgeCall(
      'markRead',
      previousItem.sourceId,
      previousItem.id
    );
    if (response?.ok) {
      previousItem.read = true;
      await loadSnapshot();
      applyFilters();
    } else {
      showToast('Stato non aggiornato', response?.message || '');
    }
  }
}

function renderDetail(item) {
  els['detail-placeholder'].hidden = true;
  els['detail-content'].hidden = false;
  els['detail-source'].textContent = item.sourceTitle;
  els['detail-date'].textContent = formatDate(item.published);
  els['detail-title'].textContent = item.title || 'Senza titolo';
  els['detail-author'].textContent = item.author ? `Di ${item.author}` : '';
  els['detail-summary'].textContent = item.summary || 'Nessun sommario disponibile per questo articolo.';
  els['open-link-btn'].disabled = !item.link;
  els['mark-read-btn'].disabled = item.read;
  els['mark-read-btn'].textContent = item.read ? 'Già letto' : 'Segna come letto';
}

function clearDetail() {
  els['detail-content'].hidden = true;
  els['detail-placeholder'].hidden = false;
}

async function refreshAll() {
  const response = await bridgeCall('refreshAll');
  if (!response?.ok) { showToast('Aggiornamento non avviato', response?.message || ''); return; }
  state.refresh = {
    running: true,
    current: 0,
    total: state.snapshot?.feeds?.length || 0,
    backendSeenRunning: true,
  };
  updateRefreshProgress();
}

async function refreshCurrentFeed() {
  const feed = selectedFeed();
  if (!feed) return;
  const response = await bridgeCall('refreshFeed', feed.id);
  if (!response?.ok) showToast('Aggiornamento non avviato', response?.message || '');
  else await loadSnapshot();
}

function updateRefreshProgress() {
  els['refresh-track'].hidden = !state.refresh.running;
  els['refresh-all-btn'].disabled = state.refresh.running;
  const percent = state.refresh.total > 0 ? Math.round((state.refresh.current / state.refresh.total) * 100) : 0;
  els['refresh-fill'].style.width = `${Math.max(0, Math.min(100, percent))}%`;
  els['refresh-track'].setAttribute('aria-valuenow', String(percent));
}

function modalField(id, label, value = '', placeholder = '', type = 'text') {
  const group = document.createElement('div');
  group.className = 'field-group';
  const labelEl = document.createElement('label');
  labelEl.htmlFor = id;
  labelEl.textContent = label;
  const shell = document.createElement('div');
  shell.className = 'field-shell';
  const input = document.createElement('input');
  input.id = id;
  input.type = type;
  input.value = value;
  input.placeholder = placeholder;
  shell.appendChild(input);
  group.append(labelEl, shell);
  return { group, input };
}

function modalButton(label, primary = false) {
  const button = document.createElement('button');
  button.type = 'button';
  button.className = `action-button${primary ? ' active-accent' : ''}`;
  button.textContent = label;
  return button;
}

function openModal({ eyebrow = '', title, body, actions, focus }) {
  state.modalReturnFocus = document.activeElement instanceof HTMLElement ? document.activeElement : null;
  els['modal-eyebrow'].textContent = eyebrow;
  els['modal-title'].textContent = title;
  els['modal-body'].replaceChildren(...body);
  els['modal-actions'].replaceChildren(...actions);
  els['modal-backdrop'].hidden = false;
  window.setTimeout(() => (focus || els['modal-close']).focus(), 0);
}

function closeModal() {
  els['modal-backdrop'].hidden = true;
  els['modal-body'].replaceChildren();
  els['modal-actions'].replaceChildren();
  const returnFocus = state.modalReturnFocus;
  state.modalReturnFocus = null;
  if (returnFocus?.isConnected) window.setTimeout(() => returnFocus.focus(), 0);
}
