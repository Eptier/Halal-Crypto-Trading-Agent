/**
 * GroupExtract Pro - Content Script
 * Adaptive DOM parsing for WhatsApp Web
 * 100% client-side, no data sent to any server
 */

(() => {
  'use strict';

  /* ========== ADAPTIVE SELECTORS ========== */
  const Selectors = {
    // WhatsApp frequently changes class names, so we use multiple strategies
    findByAriaLabel(label) {
      return document.querySelector(`[aria-label="${label}"]`);
    },

    findByDataAttr(attr, val) {
      return val
        ? document.querySelector(`[data-${attr}="${val}"]`)
        : document.querySelector(`[data-${attr}]`);
    },

    findByRole(role, text) {
      const els = document.querySelectorAll(`[role="${role}"]`);
      if (!text) return els[0];
      for (const el of els) {
        if (el.textContent.includes(text)) return el;
      }
      return null;
    },

    // Get the side panel / chat list
    getChatList() {
      return (
        document.querySelector('[aria-label="Chat list"]') ||
        document.querySelector('#pane-side') ||
        document.querySelector('[data-testid="chat-list"]') ||
        this.findByRole('grid') ||
        document.querySelector('div[class*="pane-side"]')
      );
    },

    // Get all visible chat row elements
    getChatRows() {
      const chatList = this.getChatList();
      if (!chatList) return [];

      const rows =
        chatList.querySelectorAll('[data-testid="cell-frame-container"]') ||
        chatList.querySelectorAll('[role="row"]') ||
        chatList.querySelectorAll('[role="listitem"]');

      if (rows.length > 0) return Array.from(rows);

      // Fallback: look for chat items by structure
      return Array.from(
        chatList.querySelectorAll('div[class] > div[class] > div[class]')
      ).filter((el) => {
        const spans = el.querySelectorAll('span[title]');
        return spans.length > 0;
      });
    },

    // Get group info panel (when a group is opened)
    getGroupInfoPanel() {
      return (
        document.querySelector('[data-testid="group-info-drawer"]') ||
        document.querySelector('[aria-label="Group info"]') ||
        document.querySelector('[data-testid="contact-info-drawer"]') ||
        null
      );
    },

    // Get search input for groups
    getSearchInput() {
      return (
        document.querySelector(
          '[data-testid="chat-list-search"]'
        ) ||
        this.findByAriaLabel('Search input textbox') ||
        document.querySelector(
          '#side [contenteditable="true"]'
        ) ||
        document.querySelector(
          '[data-testid="search-input"]'
        )
      );
    },

    // Get member list elements in group info
    getMemberElements() {
      const panel = this.getGroupInfoPanel();
      if (!panel) return [];

      const members =
        panel.querySelectorAll('[data-testid="cell-frame-container"]');
      if (members.length > 0) return Array.from(members);

      // Fallback strategies
      const listItems = panel.querySelectorAll('[role="listitem"]');
      if (listItems.length > 0) return Array.from(listItems);

      return Array.from(
        panel.querySelectorAll('div[class] span[title]')
      ).map((s) => s.closest('div[class][role], div[class]'));
    },

    // Get participant section container
    getParticipantsSection() {
      // Look for the section that contains participant count
      const spans = document.querySelectorAll('span');
      for (const span of spans) {
        const text = span.textContent.trim();
        if (/^\d+\s*participants?$/i.test(text) || /^\d+\s*members?$/i.test(text)) {
          return span.closest('div[class]');
        }
      }
      return null;
    },
  };

  /* ========== MUTATION OBSERVER ========== */
  let observer = null;

  function observeDOM(callback) {
    if (observer) observer.disconnect();
    observer = new MutationObserver((mutations) => {
      for (const mutation of mutations) {
        if (mutation.addedNodes.length > 0) {
          callback(mutation);
        }
      }
    });
    observer.observe(document.body, {
      childList: true,
      subtree: true,
    });
  }

  /* ========== UTILITY FUNCTIONS ========== */

  function sleep(ms) {
    return new Promise((resolve) => setTimeout(resolve, ms));
  }

  function extractPhoneFromTitle(title) {
    if (!title) return null;
    // Remove all non-digit and non-plus characters
    const cleaned = title.replace(/[^\d+]/g, '');
    if (/^\+?\d{7,15}$/.test(cleaned)) {
      return cleaned.startsWith('+') ? cleaned : '+' + cleaned;
    }
    return null;
  }

  function isGroupChat(chatElement) {
    // Groups typically have group icons or multiple participant indicators
    const groupIcon =
      chatElement.querySelector('[data-testid="default-group"]') ||
      chatElement.querySelector('[data-icon="default-group"]') ||
      chatElement.querySelector('img[src*="g.us"]');

    if (groupIcon) return true;

    // Check for participant count in subtitle
    const subtitles = chatElement.querySelectorAll('span[title]');
    for (const sub of subtitles) {
      const t = sub.getAttribute('title') || '';
      if (
        t.includes(',') &&
        !extractPhoneFromTitle(t)
      ) {
        // Multiple names separated by comma = group members subtitle
        const parts = t.split(',');
        if (parts.length >= 2) return true;
      }
    }

    return false;
  }

  function getGroupName(chatElement) {
    const titleSpan =
      chatElement.querySelector('[data-testid="cell-frame-title"] span[title]') ||
      chatElement.querySelector('span[title]');
    return titleSpan ? titleSpan.getAttribute('title') || titleSpan.textContent.trim() : 'Unknown Group';
  }

  function getGroupAvatar(chatElement) {
    const img =
      chatElement.querySelector('[data-testid="cell-frame-primary-detail"] img') ||
      chatElement.querySelector('img[src*="pps"]') ||
      chatElement.querySelector('img');
    return img ? img.src : null;
  }

  function getMemberCount(chatElement) {
    // Try to extract member count from the chat subtitle
    const meta =
      chatElement.querySelector('[data-testid="cell-frame-secondary"] span') ||
      chatElement.querySelector('span[title*=","]');
    if (meta) {
      const title = meta.getAttribute('title') || meta.textContent;
      if (title && title.includes(',')) {
        return title.split(',').length;
      }
    }
    return null;
  }

  /* ========== SCROLL HELPER ========== */

  async function scrollToLoadAll(container, maxScrollAttempts = 50) {
    if (!container) return;
    let lastHeight = container.scrollHeight;
    let attempts = 0;

    while (attempts < maxScrollAttempts) {
      container.scrollTop = container.scrollHeight;
      await sleep(500);

      if (container.scrollHeight === lastHeight) {
        // Try one more time with a longer wait
        await sleep(1000);
        if (container.scrollHeight === lastHeight) break;
      }
      lastHeight = container.scrollHeight;
      attempts++;
    }
  }

  /* ========== GROUP DETECTION ========== */

  async function detectGroups() {
    const chatList = Selectors.getChatList();
    if (!chatList) {
      return { success: false, error: 'WhatsApp Web not loaded or chat list not found.' };
    }

    // Scroll to load all chats
    const scrollContainer = chatList.querySelector('[role="list"]') || chatList;
    await scrollToLoadAll(scrollContainer, 30);

    const rows = Selectors.getChatRows();
    const groups = [];

    for (const row of rows) {
      if (isGroupChat(row)) {
        const name = getGroupName(row);
        const avatar = getGroupAvatar(row);
        const memberCount = getMemberCount(row);

        groups.push({
          name,
          avatar,
          memberCount,
          element: null, // Don't serialize DOM elements
          index: groups.length,
        });
      }
    }

    return { success: true, groups };
  }

  /* ========== MEMBER EXTRACTION ========== */

  async function simulateClick(element) {
    if (!element) return;
    const events = ['mousedown', 'mouseup', 'click'];
    for (const evtType of events) {
      element.dispatchEvent(
        new MouseEvent(evtType, {
          bubbles: true,
          cancelable: true,
          view: window,
        })
      );
    }
    await sleep(300);
  }

  async function clickGroupByName(groupName) {
    const rows = Selectors.getChatRows();
    for (const row of rows) {
      const name = getGroupName(row);
      if (name === groupName) {
        await simulateClick(row);
        await sleep(1000);
        return true;
      }
    }
    return false;
  }

  async function openGroupInfo() {
    // Click the group header to open info panel
    const header =
      document.querySelector('[data-testid="conversation-info-header"]') ||
      document.querySelector('[data-testid="conversation-header"]') ||
      document.querySelector('header');

    if (header) {
      const clickable =
        header.querySelector('[data-testid="cell-frame-container"]') ||
        header.querySelector('div[role="button"]') ||
        header.querySelector('span[title]') ||
        header;

      await simulateClick(clickable);
      await sleep(1500);
    }

    // Check if group info panel opened
    let panel = Selectors.getGroupInfoPanel();
    if (!panel) {
      // Try clicking the group name in the header
      const groupTitle = document.querySelector(
        '#main header span[title]'
      );
      if (groupTitle) {
        await simulateClick(groupTitle);
        await sleep(1500);
        panel = Selectors.getGroupInfoPanel();
      }
    }

    return panel !== null;
  }

  async function scrollMembersList() {
    const panel = Selectors.getGroupInfoPanel();
    if (!panel) return;

    // Find the scrollable section within group info
    const scrollable =
      panel.querySelector('[data-testid="group-info-participants-section"]') ||
      panel.querySelector('[role="list"]') ||
      panel;

    // Find "Search participants" or members list container
    const participantsSection = Selectors.getParticipantsSection();

    const container = participantsSection || scrollable;
    if (container) {
      await scrollToLoadAll(container, 40);
    }
    // Also scroll the main panel
    await scrollToLoadAll(panel, 20);
  }

  function parseMemberElement(el) {
    if (!el) return null;

    // Extract phone/name from span[title]
    const titleSpans = el.querySelectorAll('span[title]');
    let phone = null;
    let displayName = null;

    for (const span of titleSpans) {
      const title = span.getAttribute('title') || '';
      const maybePhone = extractPhoneFromTitle(title);
      if (maybePhone) {
        phone = maybePhone;
      } else if (title && !displayName) {
        displayName = title;
      }
    }

    // If no phone but we have a display name that looks like a phone
    if (!phone && displayName) {
      const p = extractPhoneFromTitle(displayName);
      if (p) {
        phone = p;
        displayName = null;
      }
    }

    // Check for admin badge
    const isAdmin =
      !!el.querySelector('[data-testid="admin"]') ||
      !!el.querySelector('[data-icon="admin"]') ||
      el.textContent.includes('Group admin') ||
      el.textContent.includes('Admin');

    // Get about/status text if visible
    let about = null;
    const aboutSpan =
      el.querySelector('[data-testid="cell-frame-secondary"] span') ||
      el.querySelector('span[class*="secondary"]');
    if (aboutSpan) {
      const aboutText = aboutSpan.textContent.trim();
      if (aboutText && aboutText !== displayName && !extractPhoneFromTitle(aboutText)) {
        about = aboutText;
      }
    }

    // Profile picture
    let profilePic = null;
    const img = el.querySelector('img[src]');
    if (img && img.src && !img.src.includes('data:')) {
      profilePic = img.src;
    }

    // Only return if we have either phone or name
    if (!phone && !displayName) return null;

    return {
      phone: phone || 'N/A',
      name: displayName || '',
      about: about || '',
      isAdmin,
      profilePic: profilePic || '',
    };
  }

  async function extractMembersFromGroup(groupName, progressCallback) {
    // Click the group
    const clicked = await clickGroupByName(groupName);
    if (!clicked) {
      return { success: false, error: `Could not find group: ${groupName}` };
    }

    await sleep(1000);

    // Open group info
    const infoOpened = await openGroupInfo();
    if (!infoOpened) {
      return {
        success: false,
        error: `Could not open info panel for: ${groupName}`,
      };
    }

    await sleep(1000);

    // Check for "View all" or "See all" button for participants
    const viewAllBtns = document.querySelectorAll(
      'div[role="button"], button'
    );
    for (const btn of viewAllBtns) {
      const text = btn.textContent.trim().toLowerCase();
      if (
        text.includes('view all') ||
        text.includes('see all') ||
        text.includes('search') ||
        /\d+\s*(more|others?)/.test(text)
      ) {
        await simulateClick(btn);
        await sleep(1500);
        break;
      }
    }

    // Scroll to load all members
    await scrollMembersList();
    if (progressCallback) progressCallback('scrolling');

    // Parse member elements
    const memberElements = Selectors.getMemberElements();
    const members = [];
    const seen = new Set();

    for (const el of memberElements) {
      const member = parseMemberElement(el);
      if (member) {
        const key = member.phone !== 'N/A' ? member.phone : member.name;
        if (!seen.has(key)) {
          seen.add(key);
          member.groupName = groupName;
          members.push(member);
        }
      }
    }

    // Close the group info panel
    const closeBtn =
      document.querySelector(
        '[data-testid="btn-closer-drawer"]'
      ) ||
      document.querySelector(
        '[aria-label="Close"]'
      );
    if (closeBtn) {
      await simulateClick(closeBtn);
      await sleep(500);
    }

    return { success: true, members, groupName };
  }

  /* ========== MESSAGE HANDLER ========== */

  chrome.runtime.onMessage.addListener((request, sender, sendResponse) => {
    const { action } = request;

    if (action === 'ping') {
      sendResponse({ alive: true, url: window.location.href });
      return true;
    }

    if (action === 'detectGroups') {
      detectGroups().then(sendResponse);
      return true; // async response
    }

    if (action === 'extractMembers') {
      const { groupName } = request;
      extractMembersFromGroup(groupName, (status) => {
        // Send progress via runtime message
        chrome.runtime.sendMessage({
          type: 'extractionProgress',
          groupName,
          status,
        });
      }).then(sendResponse);
      return true;
    }

    if (action === 'extractMultipleGroups') {
      const { groupNames } = request;
      (async () => {
        const allMembers = [];
        const results = [];

        for (let i = 0; i < groupNames.length; i++) {
          const gName = groupNames[i];

          // Notify progress
          chrome.runtime.sendMessage({
            type: 'extractionProgress',
            current: i + 1,
            total: groupNames.length,
            groupName: gName,
            membersFound: allMembers.length,
          });

          const result = await extractMembersFromGroup(gName);
          if (result.success) {
            for (const m of result.members) {
              m.groupName = gName;
              allMembers.push(m);
            }
            results.push({
              groupName: gName,
              count: result.members.length,
              success: true,
            });
          } else {
            results.push({
              groupName: gName,
              count: 0,
              success: false,
              error: result.error,
            });
          }

          await sleep(500);
        }

        sendResponse({
          success: true,
          members: allMembers,
          results,
        });
      })();
      return true;
    }
  });

  // Listen for DOM changes to keep track of loaded elements
  observeDOM(() => {
    // This keeps the mutation observer active
    // so new elements loaded via infinite scroll are tracked
  });

  console.log('[GroupExtract Pro] Content script loaded on WhatsApp Web');
})();
