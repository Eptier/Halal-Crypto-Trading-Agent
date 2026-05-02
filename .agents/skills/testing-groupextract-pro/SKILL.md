---
name: testing-groupextract-pro
description: Test the GroupExtract Pro Chrome extension UI end-to-end. Use when verifying UI changes to the popup, field selection, filters, export format cards, or navigation flow.
---

# Testing GroupExtract Pro Chrome Extension

## Prerequisites
- Chrome browser running
- Extension loaded via `chrome://extensions/` → Developer mode → Load unpacked → select `GroupExtract-Pro/` folder
- Note the extension ID from the extensions page (e.g., `eibilhhgekpgkibjdihpdengeidjfdae`)

## Opening the Popup for Testing
Open the popup as a full tab for easier testing:
```
chrome-extension://<EXTENSION_ID>/popup.html
```
This avoids the small popup window and gives full browser dev tools access.

## Testing Without WhatsApp Login
WhatsApp Web login is typically unavailable in test environments. The UI can still be tested by injecting mock data via browser console.

### Injecting Mock Groups (Step 1)
```javascript
const groupList = document.getElementById('groupList');
groupList.innerHTML = '';
const mockGroups = [
  { name: 'Test Group A', memberCount: 45 },
  { name: 'Test Group B', memberCount: 128 },
  { name: 'Test Group C', memberCount: 23 }
];
mockGroups.forEach(group => {
  const div = document.createElement('div');
  div.className = 'group-item';
  div.dataset.name = group.name;
  div.innerHTML = `
    <div class="group-avatar"><div class="group-avatar-initial">${group.name[0]}</div></div>
    <div class="group-info">
      <div class="group-name">${group.name}</div>
      <div class="group-meta">${group.memberCount} members</div>
    </div>
    <button class="group-fav-btn" title="Toggle favorite" data-group="${group.name}">
      <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
        <polygon points="12,2 15.09,8.26 22,9.27 17,14.14 18.18,21.02 12,17.77 5.82,21.02 7,14.14 2,9.27 8.91,8.26"/>
      </svg>
    </button>
    <div class="group-check"></div>
  `;
  groupList.appendChild(div);
});
```

### Adding Click Handlers for Mock Groups
Since injected DOM elements don't have the original IIFE event listeners, add custom handlers:
```javascript
const selectedGroups = new Set();
const nextBtn = document.getElementById('nextToFields');
const selectedCountEl = document.getElementById('selectedCount');
document.querySelectorAll('.group-item').forEach(item => {
  item.addEventListener('click', (e) => {
    if (e.target.closest('.group-fav-btn')) return;
    const name = item.dataset.name;
    if (selectedGroups.has(name)) {
      selectedGroups.delete(name);
      item.classList.remove('selected');
    } else {
      selectedGroups.add(name);
      item.classList.add('selected');
    }
    selectedCountEl.textContent = selectedGroups.size + ' selected';
    nextBtn.disabled = selectedGroups.size === 0;
  });
});
```

## Important Notes
- The popup.js uses an IIFE, so internal state (`state.groups`, `state.selectedGroups`) cannot be accessed directly from the console. Manipulate DOM elements and use custom event handlers instead.
- The original `bindEvents()` function binds navigation button handlers (Next, Back) on page load, so the Next/Back navigation buttons work natively even with injected data.
- The `Select All` checkbox might have dual event handler conflicts when used alongside injected DOM elements. Test individual group selection instead.
- Field selection checkboxes (Step 2) can be toggled via console: `document.querySelector('.field-check[value="about"]').checked = false; cb.dispatchEvent(new Event('change'));`
- Phone Number field has `disabled` attribute and cannot be unchecked (by design — it's required).

## UI Flow to Test
1. **Step 1 - Groups**: Groups listed, click to select, counter updates, Next enables
2. **Step 2 - Fields**: 6 fields, Phone "Required" + disabled, toggles work
3. **Step 3 - Filters**: 5 filters, Remove Duplicates ON by default, country code input
4. **Step 4 - Export**: 4 format cards, Export button disabled until format selected
5. **History Panel**: Clock icon in header, shows empty state
6. **Favorites Panel**: Star icon in header, shows empty state + disabled Load button
7. **Back Navigation**: All steps preserve state when navigating backwards

## What Cannot Be Tested Without WhatsApp Login
- Actual group detection from WhatsApp Web DOM
- Real member extraction with infinite scroll
- File download (Export & Download) with real data
- Export history saving after real export
- Content script DOM parsing and adaptive selectors

## Devin Secrets Needed
No secrets required for UI testing. WhatsApp login (if needed for full end-to-end) would require user's phone for QR code scan — cannot be automated with secrets.
