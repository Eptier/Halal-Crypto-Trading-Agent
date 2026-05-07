"""Flask-based web dashboard for monitoring mining operations."""

import threading

from flask import Flask, jsonify, render_template_string

from mining_tool.core.earnings import EarningsTracker
from mining_tool.core.xmrig_manager import XMRigManager
from mining_tool.utils.helpers import format_hashrate, format_uptime

DASHBOARD_HTML = """
<!DOCTYPE html>
<html lang="bn">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Crypto Mining Dashboard</title>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        body {
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif;
            background: linear-gradient(135deg, #0f0c29, #302b63, #24243e);
            color: #e0e0e0;
            min-height: 100vh;
        }
        .header {
            background: rgba(0,0,0,0.3);
            padding: 20px 30px;
            border-bottom: 2px solid #6c63ff;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .header h1 {
            font-size: 24px;
            background: linear-gradient(90deg, #6c63ff, #00d2ff);
            -webkit-background-clip: text;
            -webkit-text-fill-color: transparent;
        }
        .status-badge {
            padding: 8px 16px;
            border-radius: 20px;
            font-weight: bold;
            font-size: 14px;
        }
        .status-running { background: #00c853; color: #000; }
        .status-stopped { background: #ff5252; color: #fff; }
        .container { max-width: 1200px; margin: 0 auto; padding: 20px; }
        .grid {
            display: grid;
            grid-template-columns: repeat(auto-fit, minmax(280px, 1fr));
            gap: 20px;
            margin-top: 20px;
        }
        .card {
            background: rgba(255,255,255,0.05);
            border: 1px solid rgba(255,255,255,0.1);
            border-radius: 12px;
            padding: 24px;
            backdrop-filter: blur(10px);
            transition: transform 0.2s;
        }
        .card:hover { transform: translateY(-2px); }
        .card h3 {
            color: #6c63ff;
            margin-bottom: 12px;
            font-size: 14px;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        .card .value {
            font-size: 32px;
            font-weight: bold;
            color: #fff;
        }
        .card .sub {
            color: #888;
            margin-top: 8px;
            font-size: 13px;
        }
        .card.highlight { border-color: #6c63ff; }
        .earnings-positive { color: #00c853 !important; }
        .earnings-negative { color: #ff5252 !important; }
        .info-table {
            width: 100%;
            margin-top: 20px;
        }
        .info-table td {
            padding: 8px 12px;
            border-bottom: 1px solid rgba(255,255,255,0.05);
        }
        .info-table td:first-child {
            color: #888;
            width: 40%;
        }
        .section-title {
            font-size: 18px;
            margin: 30px 0 10px;
            color: #6c63ff;
        }
        .controls {
            display: flex;
            gap: 10px;
            margin-top: 20px;
        }
        .btn {
            padding: 12px 24px;
            border: none;
            border-radius: 8px;
            cursor: pointer;
            font-size: 14px;
            font-weight: bold;
            transition: opacity 0.2s;
        }
        .btn:hover { opacity: 0.8; }
        .btn-start { background: #00c853; color: #000; }
        .btn-stop { background: #ff5252; color: #fff; }
        .btn-refresh { background: #6c63ff; color: #fff; }
        .bangla-note {
            background: rgba(108, 99, 255, 0.1);
            border: 1px solid rgba(108, 99, 255, 0.3);
            border-radius: 8px;
            padding: 16px;
            margin-top: 20px;
            font-size: 14px;
            line-height: 1.6;
        }
        @keyframes pulse { 0%,100% { opacity: 1; } 50% { opacity: 0.5; } }
        .pulsing { animation: pulse 2s infinite; }
        #refresh-timer { color: #666; font-size: 12px; }
    </style>
</head>
<body>
    <div class="header">
        <h1>Crypto Mining Dashboard</h1>
        <div>
            <span id="status-badge" class="status-badge status-stopped">Stopped</span>
            <span id="refresh-timer"></span>
        </div>
    </div>

    <div class="container">
        <div class="controls">
            <button class="btn btn-start" onclick="controlMiner('start')">Start Mining</button>
            <button class="btn btn-stop" onclick="controlMiner('stop')">Stop Mining</button>
            <button class="btn btn-refresh" onclick="refreshStats()">Refresh</button>
        </div>

        <div class="grid">
            <div class="card highlight">
                <h3>Hashrate (Now)</h3>
                <div class="value" id="hashrate-current">0 H/s</div>
                <div class="sub">Average: <span id="hashrate-avg">0 H/s</span> | Max: <span id="hashrate-max">0 H/s</span></div>
            </div>
            <div class="card">
                <h3>Daily Earning (Estimate)</h3>
                <div class="value earnings-positive" id="earn-daily-usd">$0.00</div>
                <div class="sub" id="earn-daily-xmr">0.00000000 XMR</div>
            </div>
            <div class="card">
                <h3>Monthly Earning (Estimate)</h3>
                <div class="value earnings-positive" id="earn-monthly-usd">$0.00</div>
                <div class="sub" id="earn-monthly-xmr">0.00000000 XMR</div>
            </div>
            <div class="card">
                <h3>Shares</h3>
                <div class="value" id="shares-accepted">0</div>
                <div class="sub">Rejected: <span id="shares-rejected">0</span></div>
            </div>
            <div class="card">
                <h3>Uptime</h3>
                <div class="value" id="uptime">0s</div>
                <div class="sub" id="pool-info">Not connected</div>
            </div>
            <div class="card">
                <h3>XMR Price</h3>
                <div class="value" id="xmr-price">$0.00</div>
                <div class="sub">via CoinGecko</div>
            </div>
        </div>

        <h2 class="section-title">System Information</h2>
        <div class="grid">
            <div class="card">
                <table class="info-table">
                    <tr><td>CPU</td><td id="sys-cpu">Loading...</td></tr>
                    <tr><td>Cores</td><td id="sys-cores">-</td></tr>
                    <tr><td>RAM</td><td id="sys-ram">-</td></tr>
                    <tr><td>OS</td><td id="sys-os">-</td></tr>
                </table>
            </div>
            <div class="card">
                <table class="info-table">
                    <tr><td>Mining Coin</td><td id="cfg-coin">XMR (Monero)</td></tr>
                    <tr><td>Pool</td><td id="cfg-pool">-</td></tr>
                    <tr><td>Threads</td><td id="cfg-threads">Auto</td></tr>
                    <tr><td>CPU Limit</td><td id="cfg-cpu-limit">75%</td></tr>
                </table>
            </div>
        </div>

        <div class="bangla-note">
            <strong>Mining Guide (বাংলা):</strong><br>
            - এই tool টি আপনার PC এর CPU ব্যবহার করে Monero (XMR) mine করে<br>
            - Mining শুরু করতে উপরের "Start Mining" বাটনে ক্লিক করুন<br>
            - Normal PC তে দিনে কয়েক সেন্ট থেকে কয়েক ডলার earn হতে পারে<br>
            - CPU usage কমাতে config এ cpu_max_usage কমিয়ে দিন<br>
            - Wallet address অবশ্যই সঠিক দিতে হবে, না হলে earning পাবেন না
        </div>
    </div>

    <script>
        function refreshStats() {
            fetch('/api/stats')
                .then(r => r.json())
                .then(data => {
                    const s = data.mining_stats;
                    const e = data.earnings;

                    // Status
                    const badge = document.getElementById('status-badge');
                    if (s.running) {
                        badge.textContent = 'Mining...';
                        badge.className = 'status-badge status-running pulsing';
                    } else {
                        badge.textContent = 'Stopped';
                        badge.className = 'status-badge status-stopped';
                    }

                    // Hashrate
                    document.getElementById('hashrate-current').textContent = data.formatted.hashrate_current;
                    document.getElementById('hashrate-avg').textContent = data.formatted.hashrate_avg;
                    document.getElementById('hashrate-max').textContent = data.formatted.hashrate_max;

                    // Earnings
                    document.getElementById('earn-daily-usd').textContent = '$' + e.usd_per_day.toFixed(4);
                    document.getElementById('earn-daily-xmr').textContent = e.xmr_per_day.toFixed(8) + ' XMR';
                    document.getElementById('earn-monthly-usd').textContent = '$' + e.usd_per_month.toFixed(2);
                    document.getElementById('earn-monthly-xmr').textContent = e.xmr_per_month.toFixed(8) + ' XMR';

                    // Shares
                    document.getElementById('shares-accepted').textContent = s.shares?.accepted || 0;
                    document.getElementById('shares-rejected').textContent = s.shares?.rejected || 0;

                    // Uptime
                    document.getElementById('uptime').textContent = data.formatted.uptime;
                    if (s.connection?.pool) {
                        document.getElementById('pool-info').textContent = 'Pool: ' + s.connection.pool;
                    }

                    // XMR Price
                    document.getElementById('xmr-price').textContent = '$' + (e.xmr_price_usd || 0).toFixed(2);

                    // System info
                    if (data.system) {
                        document.getElementById('sys-cpu').textContent = data.system.cpu?.name || '-';
                        document.getElementById('sys-cores').textContent =
                            (data.system.cpu?.cores_physical || '-') + 'P / ' +
                            (data.system.cpu?.cores_logical || '-') + 'L';
                        document.getElementById('sys-ram').textContent =
                            (data.system.memory?.total_gb || '-') + ' GB';
                        document.getElementById('sys-os').textContent = data.system.os || '-';
                    }

                    // Config info
                    if (data.config) {
                        document.getElementById('cfg-pool').textContent = data.config.pool_name || '-';
                        document.getElementById('cfg-threads').textContent =
                            data.config.threads === 0 ? 'Auto' : data.config.threads;
                        document.getElementById('cfg-cpu-limit').textContent =
                            data.config.cpu_max_usage + '%';
                    }
                })
                .catch(err => console.error('Failed to fetch stats:', err));
        }

        function controlMiner(action) {
            fetch('/api/control/' + action, { method: 'POST' })
                .then(r => r.json())
                .then(data => {
                    alert(data.message);
                    setTimeout(refreshStats, 2000);
                })
                .catch(err => alert('Error: ' + err));
        }

        // Auto-refresh every 10 seconds
        refreshStats();
        setInterval(refreshStats, 10000);
    </script>
</body>
</html>
"""


def create_dashboard_app(miner_manager: XMRigManager) -> Flask:
    """Create the Flask dashboard application."""
    app = Flask(__name__)
    earnings_tracker = EarningsTracker()

    @app.route("/")
    def index():
        return render_template_string(DASHBOARD_HTML)

    @app.route("/api/stats")
    def api_stats():
        from mining_tool.utils.system_info import get_system_summary

        stats = miner_manager.get_mining_stats()
        hashrate_current = stats["hashrate"]["current"] or 0

        earnings = earnings_tracker.estimate_daily_earnings(hashrate_current)
        system = get_system_summary()


        return jsonify(
            {
                "mining_stats": stats,
                "earnings": earnings,
                "system": system,
                "config": {
                    "pool_name": miner_manager.config.get_pool_name(),
                    "coin": miner_manager.config.coin,
                    "threads": miner_manager.config.threads,
                    "cpu_max_usage": miner_manager.config.cpu_max_usage,
                },
                "formatted": {
                    "hashrate_current": format_hashrate(hashrate_current),
                    "hashrate_avg": format_hashrate(stats["hashrate"]["average"] or 0),
                    "hashrate_max": format_hashrate(stats["hashrate"]["max"] or 0),
                    "uptime": format_uptime(stats.get("uptime", 0)),
                },
            }
        )

    @app.route("/api/control/<action>", methods=["POST"])
    def api_control(action: str):
        if action == "start":
            success = miner_manager.start()
            msg = "Mining started!" if success else "Failed to start mining"
        elif action == "stop":
            success = miner_manager.stop()
            msg = "Mining stopped" if success else "No miner running"
        else:
            return jsonify({"success": False, "message": f"Unknown action: {action}"}), 400

        return jsonify({"success": success, "message": msg})

    @app.route("/api/earnings")
    def api_earnings():
        return jsonify(
            {
                "all_time": earnings_tracker.get_total_earnings(),
                "last_7_days": earnings_tracker.get_total_earnings(days=7),
                "last_30_days": earnings_tracker.get_total_earnings(days=30),
            }
        )

    return app


def run_dashboard(miner_manager: XMRigManager, port: int = 5000) -> None:
    """Run the dashboard in a background thread."""
    app = create_dashboard_app(miner_manager)

    thread = threading.Thread(
        target=lambda: app.run(host="0.0.0.0", port=port, debug=False),
        daemon=True,
    )
    thread.start()
    print(f"Dashboard running at http://localhost:{port}")
    return thread
