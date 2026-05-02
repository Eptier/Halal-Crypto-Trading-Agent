/**
 * GroupExtract Pro - Background Service Worker
 * Handles message relay between popup and content scripts.
 */

chrome.runtime.onInstalled.addListener(() => {
  console.log('[GroupExtract Pro] Extension installed');
});

// Relay extraction progress from content script to popup
chrome.runtime.onMessage.addListener((message, sender, sendResponse) => {
  if (message.type === 'extractionProgress') {
    // Forward to popup if open
    chrome.runtime.sendMessage(message).catch(() => {
      // Popup might not be open, ignore
    });
  }
});
