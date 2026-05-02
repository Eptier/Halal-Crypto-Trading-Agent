/**
 * GroupExtract Pro - Popup Controller
 * Handles UI, filtering, field selection, export, history, and favorites.
 * 100% client-side processing.
 */

(() => {
  'use strict';

  /* ========== STATE ========== */
  const state = {
    currentStep: 1,
    groups: [],
    selectedGroups: [],
    selectedFields: ['phone', 'name', 'about', 'isAdmin', 'groupName'],
    selectedFormat: null,
    extractedMembers: [],
    favorites: [],
    history: [],
    isExtracting: false,
  };

  /* ========== DOM REFS ========== */
  const $ = (sel) => document.querySelector(sel);
  const $$ = (sel) => document.querySelectorAll(sel);

  const els = {
    // Steps
    step1: $('#step1'),
    step2: $('#step2'),
    step3: $('#step3'),
    step4: $('#step4'),
    // Step 1
    groupSearch: $('#groupSearch'),
    groupList: $('#groupList'),
    selectAll: $('#selectAll'),
    selectedCount: $('#selectedCount'),
    nextToFields: $('#nextToFields'),
    // Step 2
    backToGroups: $('#backToGroups'),
    nextToFilter: $('#nextToFilter'),
    // Step 3
    filterAdmins: $('#filterAdmins'),
    filterDuplicates: $('#filterDuplicates'),
    filterSaved: $('#filterSaved'),
    countryCode: $('#countryCode'),
    filterNewOnly: $('#filterNewOnly'),
    backToFields: $('#backToFields'),
    nextToExport: $('#nextToExport'),
    // Step 4
    exportFormats: $('#exportFormats'),
    progressArea: $('#progressArea'),
    progressBar: $('#progressBar'),
    progressLabel: $('#progressLabel'),
    progressPercent: $('#progressPercent'),
    progressDetail: $('#progressDetail'),
    exportSummary: $('#exportSummary'),
    summaryGroups: $('#summaryGroups'),
    summaryMembers: $('#summaryMembers'),
    summaryFields: $('#summaryFields'),
    summaryFormat: $('#summaryFormat'),
    startExport: $('#startExport'),
    backToFilter: $('#backToFilter'),
    // Header
    historyBtn: $('#historyBtn'),
    favBtn: $('#favBtn'),
    // Panels
    historyPanel: $('#historyPanel'),
    historyList: $('#historyList'),
    closeHistory: $('#closeHistory'),
    favPanel: $('#favPanel'),
    favList: $('#favList'),
    closeFav: $('#closeFav'),
    loadFavGroups: $('#loadFavGroups'),
    // Status
    statusBar: $('#statusBar'),
    statusText: $('#statusText'),
  };

  /* ========== INIT ========== */
  async function init() {
    loadStoredData();
    bindEvents();
    await checkWhatsApp();
  }

  function loadStoredData() {
    chrome.storage.local.get(['favorites', 'history'], (data) => {
      state.favorites = data.favorites || [];
      state.history = data.history || [];
      renderHistory();
      renderFavorites();
    });
  }

  /* ========== EVENTS ========== */
  function bindEvents() {
    // Navigation
    els.nextToFields.addEventListener('click', () => goToStep(2));
    els.backToGroups.addEventListener('click', () => goToStep(1));
    els.nextToFilter.addEventListener('click', () => goToStep(3));
    els.backToFields.addEventListener('click', () => goToStep(2));
    els.nextToExport.addEventListener('click', () => goToStep(4));
    els.backToFilter.addEventListener('click', () => goToStep(3));

    // Search
    els.groupSearch.addEventListener('input', filterGroupList);

    // Select all
    els.selectAll.addEventListener('change', toggleSelectAll);

    // Field checkboxes
    $$('.field-check').forEach((cb) => {
      cb.addEventListener('change', updateFieldSelection);
    });

    // Field item click
    $$('.field-item').forEach((item) => {
      item.addEventListener('click', (e) => {
        const cb = item.querySelector('.field-check');
        if (cb && !cb.disabled && e.target !== cb) {
          cb.checked = !cb.checked;
          cb.dispatchEvent(new Event('change'));
        }
      });
    });

    // Export format selection
    $$('.export-card').forEach((card) => {
      card.addEventListener('click', () => selectFormat(card));
    });

    // Export button
    els.startExport.addEventListener('click', startExport);

    // Panels
    els.historyBtn.addEventListener('click', () =>
      togglePanel('historyPanel')
    );
    els.favBtn.addEventListener('click', () => togglePanel('favPanel'));
    els.closeHistory.addEventListener('click', () =>
      togglePanel('historyPanel')
    );
    els.closeFav.addEventListener('click', () => togglePanel('favPanel'));
    els.loadFavGroups.addEventListener('click', loadFavoriteGroups);

    // Listen for extraction progress from content script
    chrome.runtime.onMessage.addListener((msg) => {
      if (msg.type === 'extractionProgress') {
        updateProgress(msg);
      }
    });
  }

  /* ========== WHATSAPP CHECK ========== */
  async function checkWhatsApp() {
    try {
      const [tab] = await chrome.tabs.query({
        active: true,
        currentWindow: true,
      });

      if (!tab || !tab.url || !tab.url.includes('web.whatsapp.com')) {
        showNoWhatsApp();
        return;
      }

      // Ping content script
      try {
        const response = await chrome.tabs.sendMessage(tab.id, {
          action: 'ping',
        });
        if (response && response.alive) {
          showStatus('Connected to WhatsApp Web', 'success');
          await loadGroups(tab.id);
        }
      } catch {
        // Content script might not be injected yet
        showStatus('Connecting to WhatsApp Web...', 'info');

        // Try injecting content script
        try {
          await chrome.scripting.executeScript({
            target: { tabId: tab.id },
            files: ['content.js'],
          });
          await new Promise((r) => setTimeout(r, 1000));
          await loadGroups(tab.id);
          showStatus('Connected to WhatsApp Web', 'success');
        } catch (err) {
          showNoWhatsApp();
        }
      }
    } catch {
      showNoWhatsApp();
    }
  }

  function showNoWhatsApp() {
    els.groupList.innerHTML = `
      <div class="no-wa-state">
        <svg width="48" height="48" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
          <path d="M21 11.5a8.38 8.38 0 01-.9 3.8 8.5 8.5 0 01-7.6 4.7 8.38 8.38 0 01-3.8-.9L3 21l1.9-5.7a8.38 8.38 0 01-.9-3.8 8.5 8.5 0 014.7-7.6 8.38 8.38 0 013.8-.9h.5a8.48 8.48 0 018 8v.5z"/>
        </svg>
        <p>WhatsApp Web is not open</p>
        <p class="hint">Please open <strong>web.whatsapp.com</strong> in the active tab and make sure you are logged in, then click the extension icon again.</p>
      </div>
    `;
  }

  /* ========== GROUP LOADING ========== */
  async function loadGroups(tabId) {
    els.groupList.innerHTML = `
      <div class="loading-state">
        <div class="spinner"></div>
        <p>Detecting WhatsApp groups...</p>
        <p class="hint">This may take a moment</p>
      </div>
    `;

    try {
      const response = await chrome.tabs.sendMessage(tabId, {
        action: 'detectGroups',
      });

      if (response && response.success) {
        state.groups = response.groups;
        renderGroupList();
        showStatus(`Found ${state.groups.length} groups`, 'success');
      } else {
        els.groupList.innerHTML = `
          <div class="no-wa-state">
            <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
              <circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/>
              <line x1="9" y1="9" x2="15" y2="15"/>
            </svg>
            <p>${response?.error || 'Could not detect groups'}</p>
            <p class="hint">Make sure you have groups in your WhatsApp and the page is fully loaded.</p>
          </div>
        `;
      }
    } catch {
      els.groupList.innerHTML = `
        <div class="no-wa-state">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5">
            <circle cx="12" cy="12" r="10"/><line x1="12" y1="8" x2="12" y2="12"/>
            <line x1="12" y1="16" x2="12.01" y2="16"/>
          </svg>
          <p>Communication error</p>
          <p class="hint">Please refresh WhatsApp Web and try again.</p>
        </div>
      `;
    }
  }

  /* ========== GROUP RENDERING ========== */
  function renderGroupList() {
    if (state.groups.length === 0) {
      els.groupList.innerHTML = `
        <div class="no-wa-state">
          <p>No groups found</p>
          <p class="hint">Make sure you have groups in your WhatsApp chat list.</p>
        </div>
      `;
      return;
    }

    els.groupList.innerHTML = '';
    state.groups.forEach((group, index) => {
      const div = document.createElement('div');
      div.className = 'group-item';
      div.dataset.index = index;

      if (state.selectedGroups.includes(group.name)) {
        div.classList.add('selected');
      }

      const initial = group.name.charAt(0).toUpperCase();
      const isFav = state.favorites.includes(group.name);

      div.innerHTML = `
        <div class="group-avatar">
          ${
            group.avatar
              ? `<img src="${group.avatar}" alt="">`
              : initial
          }
        </div>
        <div class="group-info">
          <div class="group-name">${escapeHtml(group.name)}</div>
          <div class="group-meta">${
            group.memberCount
              ? `${group.memberCount} members`
              : 'Group'
          }</div>
        </div>
        <button class="group-fav-btn ${isFav ? 'favorited' : ''}" title="Toggle favorite" data-group="${escapeHtml(group.name)}">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="${isFav ? 'currentColor' : 'none'}" stroke="currentColor" stroke-width="2">
            <polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26"/>
          </svg>
        </button>
        <div class="group-check"></div>
      `;

      // Click to select
      div.addEventListener('click', (e) => {
        if (e.target.closest('.group-fav-btn')) return;
        toggleGroupSelection(div, group.name);
      });

      // Favorite button
      const favBtnEl = div.querySelector('.group-fav-btn');
      favBtnEl.addEventListener('click', (e) => {
        e.stopPropagation();
        toggleFavorite(group.name, favBtnEl);
      });

      els.groupList.appendChild(div);
    });
  }

  function filterGroupList() {
    const query = els.groupSearch.value.toLowerCase().trim();
    const items = els.groupList.querySelectorAll('.group-item');

    items.forEach((item) => {
      const name = item
        .querySelector('.group-name')
        .textContent.toLowerCase();
      item.style.display = name.includes(query) ? '' : 'none';
    });
  }

  function toggleGroupSelection(div, groupName) {
    const idx = state.selectedGroups.indexOf(groupName);
    if (idx === -1) {
      state.selectedGroups.push(groupName);
      div.classList.add('selected');
    } else {
      state.selectedGroups.splice(idx, 1);
      div.classList.remove('selected');
    }
    updateSelectionUI();
  }

  function toggleSelectAll() {
    const checked = els.selectAll.checked;
    state.selectedGroups = checked
      ? state.groups.map((g) => g.name)
      : [];

    els.groupList
      .querySelectorAll('.group-item')
      .forEach((item) => {
        item.classList.toggle('selected', checked);
      });
    updateSelectionUI();
  }

  function updateSelectionUI() {
    const count = state.selectedGroups.length;
    els.selectedCount.textContent = `${count} selected`;
    els.nextToFields.disabled = count === 0;
    els.selectAll.checked =
      count > 0 && count === state.groups.length;
  }

  /* ========== FIELD SELECTION ========== */
  function updateFieldSelection() {
    state.selectedFields = [];
    $$('.field-check').forEach((cb) => {
      if (cb.checked) {
        state.selectedFields.push(cb.value);
      }
      // Update active class
      const item = cb.closest('.field-item');
      item.classList.toggle('active', cb.checked);
    });
  }

  /* ========== STEP NAVIGATION ========== */
  function goToStep(step) {
    state.currentStep = step;

    // Update step panels
    $$('.step-panel').forEach((p) => p.classList.remove('active'));
    $(`#step${step}`).classList.add('active');

    // Update step indicators
    $$('.steps-bar .step').forEach((s, i) => {
      s.classList.remove('active', 'completed');
      if (i + 1 === step) s.classList.add('active');
      else if (i + 1 < step) s.classList.add('completed');
    });

    // Update step lines
    const lines = $$('.step-line');
    lines.forEach((line, i) => {
      line.classList.toggle('active', i + 1 < step);
    });

    // Step 4: prepare summary
    if (step === 4) {
      updateExportSummary();
    }
  }

  function updateExportSummary() {
    els.summaryGroups.textContent = state.selectedGroups.length;
    els.summaryFields.textContent = state.selectedFields.length;
  }

  /* ========== FORMAT SELECTION ========== */
  function selectFormat(card) {
    $$('.export-card').forEach((c) => c.classList.remove('selected'));
    card.classList.add('selected');
    state.selectedFormat = card.dataset.format;
    els.startExport.disabled = false;
    els.summaryFormat.textContent =
      card.querySelector('.export-name').textContent;
  }

  /* ========== EXTRACTION & EXPORT ========== */
  async function startExport() {
    if (state.isExtracting || !state.selectedFormat) return;
    state.isExtracting = true;

    els.startExport.disabled = true;
    els.progressArea.classList.remove('hidden');
    els.exportSummary.classList.add('hidden');

    try {
      const [tab] = await chrome.tabs.query({
        active: true,
        currentWindow: true,
      });

      updateProgressUI(0, state.selectedGroups.length, 'Starting extraction...');

      const response = await chrome.tabs.sendMessage(tab.id, {
        action: 'extractMultipleGroups',
        groupNames: state.selectedGroups,
      });

      if (response && response.success) {
        state.extractedMembers = response.members;

        // Apply filters
        let filtered = applyFilters(state.extractedMembers);

        updateProgressUI(
          state.selectedGroups.length,
          state.selectedGroups.length,
          `Extracted ${filtered.length} members`
        );

        // Export
        await exportData(filtered, state.selectedFormat);

        // Save to history
        saveToHistory(filtered.length);

        els.exportSummary.classList.remove('hidden');
        els.summaryMembers.textContent = filtered.length;

        showStatus(
          `Exported ${filtered.length} members as ${state.selectedFormat.toUpperCase()}`,
          'success'
        );

        showToast(`${filtered.length} members exported!`, 'success');
      } else {
        showStatus('Extraction failed. Please try again.', 'error');
      }
    } catch (err) {
      console.error('Export error:', err);
      showStatus('Error during export: ' + err.message, 'error');
    }

    state.isExtracting = false;
    els.startExport.disabled = false;
  }

  function updateProgress(msg) {
    if (msg.current && msg.total) {
      updateProgressUI(
        msg.current,
        msg.total,
        `Scanning: ${msg.groupName}`,
        msg.membersFound
      );
    }
  }

  function updateProgressUI(current, total, detail, membersFound) {
    const pct = total > 0 ? Math.round((current / total) * 100) : 0;
    els.progressBar.style.width = `${pct}%`;
    els.progressPercent.textContent = `${pct}%`;
    els.progressLabel.textContent = `Extracting members...`;
    els.progressDetail.textContent = `${detail}${
      membersFound !== undefined ? ` | ${membersFound} found` : ''
    }`;
  }

  /* ========== FILTERS ========== */
  function applyFilters(members) {
    let filtered = [...members];

    // Exclude admins
    if (els.filterAdmins.checked) {
      filtered = filtered.filter((m) => !m.isAdmin);
    }

    // Remove duplicates (by phone)
    if (els.filterDuplicates.checked) {
      const seen = new Set();
      filtered = filtered.filter((m) => {
        if (m.phone === 'N/A') return true;
        if (seen.has(m.phone)) return false;
        seen.add(m.phone);
        return true;
      });
    }

    // Country code filter
    const codes = els.countryCode.value
      .split(',')
      .map((c) => c.trim())
      .filter(Boolean);
    if (codes.length > 0) {
      filtered = filtered.filter((m) =>
        codes.some((code) => m.phone.startsWith(code))
      );
    }

    // Exclude saved contacts (those with a name and no raw phone as name)
    if (els.filterSaved.checked) {
      filtered = filtered.filter((m) => {
        // If they have a display name that isn't their phone number, they're saved
        if (m.name && m.name !== m.phone && !/^\+?\d+$/.test(m.name)) {
          return false;
        }
        return true;
      });
    }

    // Only new members (compare with last export)
    if (els.filterNewOnly.checked && state.history.length > 0) {
      const lastExport = state.history[0];
      if (lastExport && lastExport.phones) {
        const prevPhones = new Set(lastExport.phones);
        filtered = filtered.filter((m) => !prevPhones.has(m.phone));
      }
    }

    return filtered;
  }

  /* ========== EXPORT FUNCTIONS ========== */
  async function exportData(members, format) {
    // Filter fields based on selection
    const data = members.map((m) => {
      const row = {};
      if (state.selectedFields.includes('phone')) row['Phone Number'] = m.phone;
      if (state.selectedFields.includes('name')) row['Display Name'] = m.name;
      if (state.selectedFields.includes('about')) row['About'] = m.about;
      if (state.selectedFields.includes('isAdmin'))
        row['Admin'] = m.isAdmin ? 'Yes' : 'No';
      if (state.selectedFields.includes('profilePic'))
        row['Profile Picture'] = m.profilePic;
      if (state.selectedFields.includes('groupName'))
        row['Group'] = m.groupName;
      return row;
    });

    switch (format) {
      case 'xlsx':
        exportXLSX(data);
        break;
      case 'csv':
        exportCSV(data);
        break;
      case 'vcf':
        exportVCF(members);
        break;
      case 'html':
        exportHTML(data);
        break;
    }
  }

  function exportXLSX(data) {
    if (typeof XLSX === 'undefined') {
      showToast('Excel library not loaded. Try CSV instead.', 'error');
      exportCSV(data);
      return;
    }

    const ws = XLSX.utils.json_to_sheet(data);

    // Auto-column width
    const colWidths = Object.keys(data[0] || {}).map((key) => {
      const maxLen = Math.max(
        key.length,
        ...data.map((row) => String(row[key] || '').length)
      );
      return { wch: Math.min(maxLen + 2, 50) };
    });
    ws['!cols'] = colWidths;

    const wb = XLSX.utils.book_new();
    XLSX.utils.book_append_sheet(wb, ws, 'Members');
    XLSX.writeFile(wb, generateFilename('xlsx'));
  }

  function exportCSV(data) {
    if (data.length === 0) {
      showToast('No data to export', 'error');
      return;
    }

    const headers = Object.keys(data[0]);
    const csvContent =
      '\uFEFF' + // UTF-8 BOM
      headers.join(',') +
      '\n' +
      data
        .map((row) =>
          headers
            .map((h) => {
              const val = String(row[h] || '').replace(/"/g, '""');
              return `"${val}"`;
            })
            .join(',')
        )
        .join('\n');

    downloadFile(csvContent, generateFilename('csv'), 'text/csv;charset=utf-8');
  }

  function exportVCF(members) {
    const vcards = members
      .map((m) => {
        const name = m.name || 'WhatsApp Contact';
        const phone = m.phone !== 'N/A' ? m.phone : '';
        if (!phone) return '';

        let vcard = 'BEGIN:VCARD\n';
        vcard += 'VERSION:3.0\n';
        vcard += `FN:${name}\n`;
        vcard += `N:${name};;;;\n`;
        if (phone) vcard += `TEL;TYPE=CELL:${phone}\n`;
        if (m.about) vcard += `NOTE:${m.about}\n`;
        if (m.groupName) vcard += `ORG:${m.groupName}\n`;
        vcard += 'END:VCARD';
        return vcard;
      })
      .filter(Boolean)
      .join('\n');

    downloadFile(vcards, generateFilename('vcf'), 'text/vcard;charset=utf-8');
  }

  function exportHTML(data) {
    if (data.length === 0) {
      showToast('No data to export', 'error');
      return;
    }

    const headers = Object.keys(data[0]);
    const now = new Date().toLocaleString();

    const html = `<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <title>GroupExtract Pro - Export</title>
  <style>
    * { margin: 0; padding: 0; box-sizing: border-box; }
    body { font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background: #f5f5f5; color: #333; padding: 30px; }
    .container { max-width: 1000px; margin: 0 auto; }
    h1 { font-size: 24px; margin-bottom: 4px; color: #1a1a2e; }
    .meta { font-size: 12px; color: #888; margin-bottom: 20px; }
    table { width: 100%; border-collapse: collapse; background: white; border-radius: 8px; overflow: hidden; box-shadow: 0 2px 12px rgba(0,0,0,0.08); }
    th { background: #1a1a2e; color: white; padding: 12px 16px; text-align: left; font-size: 13px; font-weight: 600; }
    td { padding: 10px 16px; border-bottom: 1px solid #eee; font-size: 13px; }
    tr:nth-child(even) { background: #fafafa; }
    tr:hover { background: #f0f0ff; }
    .footer { margin-top: 20px; text-align: center; font-size: 11px; color: #aaa; }
    @media print {
      body { padding: 10px; }
      table { box-shadow: none; }
      .footer { display: none; }
    }
  </style>
</head>
<body>
  <div class="container">
    <h1>GroupExtract Pro - Export</h1>
    <p class="meta">${data.length} members | Exported on ${now}</p>
    <table>
      <thead>
        <tr>${headers.map((h) => `<th>${escapeHtml(h)}</th>`).join('')}</tr>
      </thead>
      <tbody>
        ${data
          .map(
            (row) =>
              `<tr>${headers
                .map((h) => `<td>${escapeHtml(String(row[h] || ''))}</td>`)
                .join('')}</tr>`
          )
          .join('\n')}
      </tbody>
    </table>
    <p class="footer">Generated by GroupExtract Pro</p>
  </div>
</body>
</html>`;

    downloadFile(html, generateFilename('html'), 'text/html;charset=utf-8');
  }

  /* ========== FILE DOWNLOAD ========== */
  function downloadFile(content, filename, type) {
    const blob = new Blob([content], { type });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = filename;
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
  }

  function generateFilename(ext) {
    const date = new Date().toISOString().slice(0, 10);
    const groupPart =
      state.selectedGroups.length === 1
        ? state.selectedGroups[0].replace(/[^a-zA-Z0-9]/g, '_').slice(0, 30)
        : `${state.selectedGroups.length}_groups`;
    return `GroupExtract_${groupPart}_${date}.${ext}`;
  }

  /* ========== HISTORY ========== */
  function saveToHistory(memberCount) {
    const entry = {
      date: new Date().toISOString(),
      groups: [...state.selectedGroups],
      groupCount: state.selectedGroups.length,
      memberCount,
      format: state.selectedFormat,
      phones: state.extractedMembers.map((m) => m.phone),
      fields: [...state.selectedFields],
    };

    state.history.unshift(entry);
    if (state.history.length > 5) state.history = state.history.slice(0, 5);

    chrome.storage.local.set({ history: state.history });
    renderHistory();
  }

  function renderHistory() {
    if (state.history.length === 0) {
      els.historyList.innerHTML = `
        <div class="empty-state">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.4">
            <circle cx="12" cy="12" r="10"/><polyline points="12,6 12,12 16,14"/>
          </svg>
          <p>No export history yet</p>
        </div>
      `;
      return;
    }

    els.historyList.innerHTML = state.history
      .map(
        (entry, i) => `
      <div class="history-item" data-index="${i}">
        <div class="history-icon">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M14 2H6a2 2 0 00-2 2v16a2 2 0 002 2h12a2 2 0 002-2V8z"/>
            <polyline points="14,2 14,8 20,8"/>
          </svg>
        </div>
        <div class="history-info">
          <div class="history-title">${entry.groupCount} group(s) - ${entry.memberCount} members</div>
          <div class="history-meta">${formatDate(entry.date)} | ${entry.format.toUpperCase()} | ${entry.fields.length} fields</div>
        </div>
        <div class="history-actions">
          <button class="icon-btn re-export-btn" title="Re-export" data-index="${i}">
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
              <polyline points="1,4 1,10 7,10"/><path d="M3.51 15a9 9 0 102.13-9.36L1 10"/>
            </svg>
          </button>
        </div>
      </div>
    `
      )
      .join('');

    // Bind re-export buttons
    els.historyList
      .querySelectorAll('.re-export-btn')
      .forEach((btn) => {
        btn.addEventListener('click', (e) => {
          e.stopPropagation();
          const idx = parseInt(btn.dataset.index);
          reExport(idx);
        });
      });
  }

  function reExport(historyIndex) {
    const entry = state.history[historyIndex];
    if (!entry) return;

    state.selectedGroups = [...entry.groups];
    state.selectedFields = [...(entry.fields || ['phone', 'name', 'about', 'isAdmin', 'groupName'])];
    state.selectedFormat = entry.format;

    // Update UI
    renderGroupList();
    updateSelectionUI();

    // Update field checkboxes
    $$('.field-check').forEach((cb) => {
      if (!cb.disabled) {
        cb.checked = state.selectedFields.includes(cb.value);
      }
      cb.closest('.field-item').classList.toggle('active', cb.checked);
    });

    // Close history panel and go to export
    els.historyPanel.classList.add('hidden');
    goToStep(4);

    // Select the format card
    $$('.export-card').forEach((card) => {
      card.classList.toggle(
        'selected',
        card.dataset.format === entry.format
      );
    });
    els.startExport.disabled = false;

    showToast('Previous export settings loaded', 'success');
  }

  /* ========== FAVORITES ========== */
  function toggleFavorite(groupName, btnEl) {
    const idx = state.favorites.indexOf(groupName);
    if (idx === -1) {
      state.favorites.push(groupName);
      btnEl.classList.add('favorited');
      btnEl.querySelector('svg').setAttribute('fill', 'currentColor');
    } else {
      state.favorites.splice(idx, 1);
      btnEl.classList.remove('favorited');
      btnEl.querySelector('svg').setAttribute('fill', 'none');
    }

    chrome.storage.local.set({ favorites: state.favorites });
    renderFavorites();
  }

  function renderFavorites() {
    if (state.favorites.length === 0) {
      els.favList.innerHTML = `
        <div class="empty-state">
          <svg width="40" height="40" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5" opacity="0.4">
            <polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26"/>
          </svg>
          <p>No favorite groups saved</p>
        </div>
      `;
      els.loadFavGroups.disabled = true;
      return;
    }

    els.loadFavGroups.disabled = false;
    els.favList.innerHTML = state.favorites
      .map(
        (name) => `
      <div class="fav-item">
        <div class="group-avatar">${name.charAt(0).toUpperCase()}</div>
        <span class="group-name">${escapeHtml(name)}</span>
        <button class="remove-fav" data-name="${escapeHtml(name)}" title="Remove">
          <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>
          </svg>
        </button>
      </div>
    `
      )
      .join('');

    els.favList.querySelectorAll('.remove-fav').forEach((btn) => {
      btn.addEventListener('click', () => {
        const name = btn.dataset.name;
        state.favorites = state.favorites.filter((f) => f !== name);
        chrome.storage.local.set({ favorites: state.favorites });
        renderFavorites();
        renderGroupList(); // Update star icons
      });
    });
  }

  function loadFavoriteGroups() {
    state.selectedGroups = state.favorites.filter((f) =>
      state.groups.some((g) => g.name === f)
    );
    renderGroupList();
    updateSelectionUI();
    els.favPanel.classList.add('hidden');
    showToast(`${state.selectedGroups.length} favorite groups selected`, 'success');
  }

  /* ========== PANELS ========== */
  function togglePanel(panelId) {
    const panel = $(`#${panelId}`);
    panel.classList.toggle('hidden');
  }

  /* ========== STATUS & TOAST ========== */
  function showStatus(text, type) {
    els.statusBar.className = `status-bar ${type}`;
    els.statusBar.classList.remove('hidden');
    els.statusText.textContent = text;

    setTimeout(() => {
      els.statusBar.classList.add('hidden');
    }, 4000);
  }

  function showToast(msg, type = '') {
    const existing = document.querySelector('.toast');
    if (existing) existing.remove();

    const toast = document.createElement('div');
    toast.className = `toast ${type}`;
    toast.textContent = msg;
    document.body.appendChild(toast);

    requestAnimationFrame(() => {
      toast.classList.add('show');
    });

    setTimeout(() => {
      toast.classList.remove('show');
      setTimeout(() => toast.remove(), 300);
    }, 3000);
  }

  /* ========== HELPERS ========== */
  function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  function formatDate(isoStr) {
    const d = new Date(isoStr);
    return d.toLocaleDateString('en-US', {
      month: 'short',
      day: 'numeric',
      year: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    });
  }

  /* ========== START ========== */
  document.addEventListener('DOMContentLoaded', init);
})();
