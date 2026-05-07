# Crypto Mining Tool

**CPU-based Crypto Mining Tool** - Normal PC তে Monero (XMR) mine করুন!

## বাংলায় গাইড

### এটা কি?
এই tool টি আপনার PC এর CPU ব্যবহার করে Monero (XMR) cryptocurrency mine করে। Mining মানে হলো আপনার computer এর processing power ব্যবহার করে blockchain transactions verify করা, এবং এর বিনিময়ে crypto coin পাওয়া।

### কেন Monero (XMR)?
- **CPU-friendly**: GPU না থাকলেও চলবে, normal PC তেই mine হয়
- **Privacy coin**: সবচেয়ে popular privacy-focused cryptocurrency
- **RandomX algorithm**: বিশেষভাবে CPU mining এর জন্য designed

### কত টাকা আয় হবে?
সত্যি কথা বলতে গেলে:
- Normal PC (i5/Ryzen 5): দিনে ~$0.05-0.15 USD
- Good PC (i7/Ryzen 7): দিনে ~$0.10-0.30 USD
- High-end PC (Ryzen 9): দিনে ~$0.20-0.50 USD

**Note**: এটা electricity cost বাদ দিয়ে। আয় network difficulty এবং XMR price এর উপর depend করে।

---

## Features

- **XMRig Integration**: Industry-standard Monero miner automatic download & setup
- **Web Dashboard**: Browser-based real-time monitoring (hashrate, earnings, shares)
- **CLI Dashboard**: Terminal-based live monitoring with Rich UI
- **Multi-Pool Support**: MoneroOcean, P2Pool, Nanopool, HashVault, SupportXMR
- **Earnings Tracker**: Real-time USD/XMR earnings estimates via CoinGecko
- **System Benchmark**: Test your PC and see estimated earnings before mining
- **Auto CPU Optimization**: Automatically detects optimal thread count
- **Easy Setup Wizard**: Interactive Bangla/English setup

## Quick Start (দ্রুত শুরু)

### 1. Install (ইনস্টল)

```bash
# Clone the repo
git clone https://github.com/Eptier/Halal-Crypto-Trading-Agent.git
cd Halal-Crypto-Trading-Agent

# Install with pip
pip install -e .
```

### 2. Setup (সেটআপ)

```bash
# Interactive setup wizard চালান
crypto-miner setup
```

এখানে আপনাকে দিতে হবে:
- **Wallet Address**: আপনার Monero (XMR) wallet address
  - Wallet নেই? [MyMonero](https://mymonero.com/) বা [Cake Wallet](https://cakewallet.com/) থেকে তৈরি করুন
- **Mining Pool**: কোন pool এ mine করবেন (MoneroOcean recommended)
- **Worker Name**: আপনার PC এর নাম
- **CPU Settings**: কত % CPU ব্যবহার করবে

### 3. Benchmark (পিসি টেস্ট)

```bash
# আপনার PC কতটা mine করতে পারবে দেখুন
crypto-miner benchmark
```

### 4. Start Mining (মাইনিং শুরু)

```bash
# Full dashboard সহ mining শুরু
crypto-miner start

# শুধু web dashboard সহ
crypto-miner start --web-only

# Dashboard ছাড়া background এ
crypto-miner start --no-dashboard
```

### 5. Monitor (মনিটর)

```bash
# Mining status দেখুন
crypto-miner status
```

Web dashboard: Browser এ http://localhost:5000 যান

### 6. Stop (বন্ধ)

```bash
crypto-miner stop
```

## All Commands

| Command | Description | বাংলা |
|---------|-------------|-------|
| `crypto-miner setup` | Interactive setup | সেটআপ |
| `crypto-miner start` | Start mining | মাইনিং শুরু |
| `crypto-miner stop` | Stop mining | মাইনিং বন্ধ |
| `crypto-miner status` | Show status | স্ট্যাটাস দেখুন |
| `crypto-miner benchmark` | PC benchmark | পিসি টেস্ট |
| `crypto-miner info` | Coins & pools info | তথ্য |

## Start Options

```bash
crypto-miner start --wallet YOUR_XMR_ADDRESS  # wallet দিয়ে সরাসরি শুরু
crypto-miner start --pool moneroocean         # specific pool select
crypto-miner start --threads 4                # thread সংখ্যা নির্ধারণ
crypto-miner start --web-only                 # শুধু web dashboard
crypto-miner start --no-dashboard             # dashboard ছাড়া
```

## Supported Mining Pools

| Pool | Fee | Description |
|------|-----|-------------|
| MoneroOcean | 0% | Auto-switching, best for CPU |
| P2Pool | 0% | Decentralized, no fees |
| Nanopool | 1% | Large stable pool |
| HashVault | 0.9% | Reliable with good uptime |
| SupportXMR | 0.6% | Community-supported |

## Performance Tips (ভালো performance পেতে)

1. **Hugepages Enable করুন** (Linux - +20% performance):
   ```bash
   sudo sysctl -w vm.nr_hugepages=1280
   ```

2. **CPU Usage Adjust করুন**: config এ `cpu_max_usage` কমিয়ে/বাড়িয়ে নিন

3. **Background Mode**: PC ব্যবহার করার সময় `--no-dashboard` দিয়ে চালান

4. **MoneroOcean Pool**: Auto-switching feature থাকায় সবচেয়ে বেশি earn হয়

## Project Structure

```
mining_tool/
├── main.py              # CLI entry point
├── config/
│   └── settings.py      # Configuration & pool settings
├── core/
│   ├── xmrig_manager.py # XMRig download, config & process management
│   └── earnings.py      # Earnings calculator & tracker
├── dashboard/
│   ├── web_dashboard.py  # Flask web dashboard
│   └── cli_dashboard.py  # Rich terminal dashboard
├── utils/
│   ├── system_info.py   # CPU/RAM detection & compatibility check
│   └── helpers.py       # Formatting utilities
└── scripts/
    └── install_xmrig.py # Standalone XMRig installer
```

## Requirements

- Python 3.9+
- 2GB+ RAM (RandomX algorithm requirement)
- Internet connection
- x86_64, AMD64, or ARM64 CPU

## License

MIT License
