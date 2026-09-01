'use strict';

function openAddFeedModal() {
  const url = modalField('feed-url', 'URL del feed o del sito', '', 'https://example.com/feed.xml', 'url');
  const title = modalField('feed-title', 'Titolo personalizzato', '', 'Opzionale');
  const hint = document.createElement('p');
  hint.className = 'form-hint';
  hint.textContent = 'Se il sito espone un feed RSS/Atom diretto, usa quell’indirizzo.';
  const cancel = modalButton('Annulla');
  const add = modalButton('Aggiungi feed', true);
  cancel.addEventListener('click', closeModal);
  add.addEventListener('click', async () => {
    add.disabled = true;
    const response = await bridgeCommand('addFeed', url.input.value, title.input.value);
    if (!response?.ok) {
      add.disabled = false;
      showToast('Feed non aggiunto', response?.message || '');
      url.input.focus();
      return;
    }

    const source = response.data;
    let refreshStarted = false;
    if (source?.id) {
      const refresh = await bridgeCall('refreshFeed', source.id);
      refreshStarted = Boolean(refresh?.ok);
    }

    add.disabled = false;
    closeModal();
    showToast(
      'Feed aggiunto',
      refreshStarted ? 'Il primo aggiornamento è stato avviato.' : ''
    );
    await loadSnapshot({ reloadItems: state.scope.type === 'all' });
    if (source?.id) await selectScope('feed', source.id, source.title);
  });
  openModal({ eyebrow: 'Nuova sorgente', title: 'Aggiungi un feed', body: [url.group, title.group, hint], actions: [cancel, add], focus: url.input });
}

function openEditFeedModal() {
  const feed = selectedFeed();
  if (!feed) return;
  const title = modalField('edit-title', 'Titolo', feed.title);
  const category = modalField('edit-category', 'Categoria', feed.category || '', 'Es. Tecnologia');
  const urlText = document.createElement('p');
  urlText.className = 'form-hint';
  urlText.textContent = feed.url;
  const cancel = modalButton('Annulla');
  const save = modalButton('Salva', true);
  cancel.addEventListener('click', closeModal);
  save.addEventListener('click', async () => {
    save.disabled = true;
    const response = await bridgeCommand(
      'updateFeed',
      feed.id,
      title.input.value,
      category.input.value
    );
    save.disabled = false;
    if (!response?.ok) {
      showToast('Modifica non salvata', response?.message || '');
      return;
    }
    closeModal();
    state.scope.title = response.data?.title || title.input.value.trim();
    await loadSnapshot({ reloadItems: true });
    showToast('Feed aggiornato');
  });
  openModal({ eyebrow: 'Sorgente selezionata', title: 'Modifica feed', body: [title.group, category.group, urlText], actions: [cancel, save], focus: title.input });
}

function openRemoveFeedModal() {
  const feed = selectedFeed();
  if (!feed) return;
  const message = document.createElement('p');
  message.className = 'muted';
  message.textContent = `Rimuovere “${feed.title}” e gli articoli salvati associati a questa sorgente?`;
  const cancel = modalButton('Annulla');
  const remove = modalButton('Rimuovi', true);
  cancel.addEventListener('click', closeModal);
  remove.addEventListener('click', async () => {
    remove.disabled = true;
    const response = await bridgeCommand('removeFeed', feed.id);
    remove.disabled = false;
    if (!response?.ok) {
      showToast('Feed non rimosso', response?.message || '');
      return;
    }
    closeModal();
    state.scope = { type: 'all', id: '', title: 'Tutti gli articoli' };
    state.selectedItemId = null;
    await loadSnapshot({ reloadItems: true });
    showToast('Feed rimosso');
  });
  openModal({ eyebrow: 'Conferma', title: 'Rimuovi feed', body: [message], actions: [cancel, remove], focus: cancel });
}

function toggleForSetting(id, checked) {
  const label = document.createElement('label');
  label.className = 'toggle-control';
  label.htmlFor = id;
  const input = document.createElement('input');
  input.type = 'checkbox';
  input.id = id;
  input.checked = Boolean(checked);
  const track = document.createElement('span');
  track.className = 'toggle-track';
  track.setAttribute('aria-hidden', 'true');
  const thumb = document.createElement('span');
  thumb.className = 'toggle-thumb';
  track.appendChild(thumb);
  label.append(input, track);
  return { label, input };
}

function settingsRow(title, description, control) {
  const row = document.createElement('div');
  row.className = 'settings-row';
  const copy = document.createElement('div');
  copy.className = 'settings-copy';
  const strong = document.createElement('strong');
  strong.textContent = title;
  const span = document.createElement('span');
  span.textContent = description;
  copy.append(strong, span);
  row.append(copy, control);
  return row;
}

function openSettingsModal() {
  const settings = state.snapshot?.settings;
  if (!settings) return;
  const refreshWrap = document.createElement('div');
  refreshWrap.className = 'segmented';
  const intervals = [1, 5, 15, 30, 60, 120, 360];
  let selectedInterval = settings.refresh_interval_minutes;
  intervals.forEach((minutes) => {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = minutes < 60 ? `${minutes}m` : `${minutes / 60}h`;
    button.setAttribute('aria-pressed', selectedInterval === minutes ? 'true' : 'false');
    button.addEventListener('click', () => {
      selectedInterval = minutes;
      refreshWrap.querySelectorAll('button').forEach((b) => b.setAttribute('aria-pressed', b === button ? 'true' : 'false'));
    });
    refreshWrap.appendChild(button);
  });

  const autoRead = toggleForSetting('setting-auto-read', settings.mark_read_on_select);
  const notify = toggleForSetting('setting-notify', settings.notify_new_items);
  const tray = toggleForSetting('setting-tray', settings.close_to_tray);
  const rangeWrap = document.createElement('div');
  rangeWrap.className = 'range-wrap';
  const range = document.createElement('input');
  range.type = 'range'; range.min = '0.75'; range.max = '1.5'; range.step = '0.05'; range.value = String(settings.font_scale_factor);
  range.setAttribute('aria-label', 'Scala testo');
  const rangeValue = document.createElement('span');
  rangeValue.className = 'range-value';
  rangeValue.textContent = `${Math.round(Number(range.value) * 100)}%`;
  range.addEventListener('input', () => { rangeValue.textContent = `${Math.round(Number(range.value) * 100)}%`; });
  rangeWrap.append(range, rangeValue);

  const logButton = modalButton('Apri log');
  logButton.addEventListener('click', openLogViewer);
  const body = [
    settingsRow('Aggiornamento automatico', 'Intervallo tra i refresh periodici', refreshWrap),
    settingsRow('Lettura automatica', 'Segna letto quando selezioni un articolo', autoRead.label),
    settingsRow('Notifiche desktop', 'Avvisa quando arrivano nuovi articoli', notify.label),
    settingsRow('Chiudi nel tray', 'La X nasconde la finestra invece di uscire', tray.label),
    settingsRow('Dimensione testo', 'Scala tipografica dell’interfaccia', rangeWrap),
    settingsRow('Log applicazione', 'Ultime righe del log reale su disco', logButton),
  ];
  const cancel = modalButton('Annulla');
  const save = modalButton('Salva', true);
  cancel.addEventListener('click', closeModal);
  save.addEventListener('click', async () => {
    const payload = {
      refresh_interval_minutes: selectedInterval,
      mark_read_on_select: autoRead.input.checked,
      show_unread_only: els['unread-toggle'].checked,
      notify_new_items: notify.input.checked,
      close_to_tray: tray.input.checked,
      font_scale_factor: Number(range.value),
    };
    save.disabled = true;
    const response = await bridgeCommand('saveSettings', JSON.stringify(payload));
    save.disabled = false;
    if (!response?.ok) { showToast('Impostazioni non salvate', response?.message || ''); return; }
    closeModal();
    await loadSnapshot();
    applyFilters();
    showToast('Impostazioni salvate');
  });
  openModal({ eyebrow: 'Preferenze', title: 'Impostazioni', body, actions: [cancel, save], focus: save });
}

async function openLogViewer() {
  const response = await bridgeCall('getLogTail', 300);
  if (!response?.ok) { showToast('Log non disponibile', response?.message || ''); return; }
  const path = document.createElement('p');
  path.className = 'form-hint';
  path.textContent = response.data.path;
  const viewer = document.createElement('pre');
  viewer.className = 'log-viewer';
  viewer.tabIndex = 0;
  viewer.textContent = (response.data.lines || []).join('\n') || 'Il log è vuoto.';
  const close = modalButton('Chiudi');
  const copy = modalButton('Copia', true);
  close.addEventListener('click', closeModal);
  copy.addEventListener('click', async () => {
    try {
      await navigator.clipboard.writeText(viewer.textContent);
      showToast('Log copiato');
    } catch {
      showToast('Copia non disponibile', 'Seleziona il testo manualmente.');
    }
  });
  openModal({ eyebrow: 'Diagnostica', title: 'Log applicazione', body: [path, viewer], actions: [close, copy], focus: viewer });
}
