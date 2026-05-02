# GroupExtract Pro

A professional Chrome extension to export WhatsApp Web group members' contacts and information.

## Features

### Smart Group Selector
- Auto-detect all WhatsApp groups
- Group names, member counts, and avatars displayed in a beautiful UI
- Select/deselect all toggle
- Search bar to find specific groups
- Favorite groups for quick access

### Data Field Selection
Choose exactly which data fields to include in your export:
- **Phone Number** (required)
- **Display Name**
- **About Status**
- **Admin Status**
- **Profile Picture URL**
- **Group Name**

### Advanced Member Export Engine
- Parse all member data from selected groups
- Infinite scrolling auto-handled
- Real-time progress bar

### Powerful Filter System
- Exclude admins
- Country code filter (e.g., +880, +1, +91)
- Auto-remove duplicate numbers
- Exclude saved contacts
- Export only new members (compared to previous export)

### Multi-Format Export
- **Excel (.xlsx)** — formatted headers, auto-column width
- **CSV** — UTF-8 encoded with BOM
- **VCF (vCard)** — directly importable on mobile
- **HTML** — print-friendly table view

### Smart Backup & History
- Last 5 exports saved with date, group count, and member count
- One-click re-export
- "New members only" option
- Favorite group lists

### Adaptive DOM Parsing
- Uses aria-label, role, data-* attributes
- Text content analysis
- MutationObserver for dynamically loaded elements
- Resilient to WhatsApp DOM class changes

## Technical Details

- **Manifest V3** compliant
- **100% client-side** — no data sent to any server
- Dark mode glassmorphic/neumorphic UI
- Inter font for professional typography

## Installation

1. Clone or download this repository
2. Open Chrome and go to `chrome://extensions/`
3. Enable **Developer mode** (top-right toggle)
4. Click **Load unpacked** and select the `GroupExtract-Pro` folder
5. Navigate to `web.whatsapp.com` and click the extension icon

## Privacy

All data processing is done locally in your browser. No data is transmitted to any external server. Your contacts remain completely private.
