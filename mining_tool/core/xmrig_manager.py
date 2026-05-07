"""XMRig miner process manager - download, configure, and control XMRig."""

import json
import os
import platform
import shutil
import signal
import subprocess
import tarfile
import zipfile
from pathlib import Path

import requests

from mining_tool.config.settings import MinerConfig

XMRIG_VERSION = "6.21.1"
XMRIG_BASE_URL = "https://github.com/xmrig/xmrig/releases/download"
INSTALL_DIR = Path.home() / ".crypto_miner" / "xmrig"


def get_xmrig_download_url() -> str:
    """Get the appropriate XMRig download URL for this system."""
    system = platform.system().lower()
    machine = platform.machine().lower()

    if system == "linux":
        if machine in ("x86_64", "amd64"):
            archive = f"xmrig-{XMRIG_VERSION}-linux-x64.tar.gz"
        elif machine == "aarch64":
            archive = f"xmrig-{XMRIG_VERSION}-linux-arm64.tar.gz"
        else:
            raise RuntimeError(f"Unsupported Linux architecture: {machine}")
    elif system == "windows":
        archive = f"xmrig-{XMRIG_VERSION}-msvc-win64.zip"
    elif system == "darwin":
        archive = f"xmrig-{XMRIG_VERSION}-macos-x64.tar.gz"
    else:
        raise RuntimeError(f"Unsupported OS: {system}")

    return f"{XMRIG_BASE_URL}/v{XMRIG_VERSION}/{archive}"


def download_xmrig(target_dir: Path | None = None) -> Path:
    """Download and extract XMRig to the target directory."""
    install_path = target_dir or INSTALL_DIR
    install_path.mkdir(parents=True, exist_ok=True)

    xmrig_binary = find_xmrig_binary(install_path)
    if xmrig_binary:
        return xmrig_binary

    url = get_xmrig_download_url()
    filename = url.split("/")[-1]
    download_path = install_path / filename

    print(f"Downloading XMRig from {url}...")
    response = requests.get(url, stream=True, timeout=120)
    response.raise_for_status()

    total_size = int(response.headers.get("content-length", 0))
    downloaded = 0

    with open(download_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=8192):
            f.write(chunk)
            downloaded += len(chunk)
            if total_size > 0:
                percent = (downloaded / total_size) * 100
                print(f"\rDownloading: {percent:.1f}%", end="", flush=True)

    print("\nExtracting...")

    if filename.endswith(".tar.gz"):
        with tarfile.open(download_path, "r:gz") as tar:
            tar.extractall(path=install_path)
    elif filename.endswith(".zip"):
        with zipfile.ZipFile(download_path, "r") as zip_ref:
            zip_ref.extractall(install_path)

    download_path.unlink()

    xmrig_binary = find_xmrig_binary(install_path)
    if xmrig_binary:
        os.chmod(xmrig_binary, 0o755)
        return xmrig_binary

    raise RuntimeError("XMRig binary not found after extraction")


def find_xmrig_binary(search_dir: Path) -> Path | None:
    """Find the XMRig binary in a directory."""
    binary_name = "xmrig.exe" if platform.system() == "Windows" else "xmrig"
    for path in search_dir.rglob(binary_name):
        if path.is_file():
            return path
    return None


def generate_xmrig_config(config: MinerConfig) -> dict:
    """Generate XMRig JSON configuration."""
    pool_url = config.get_pool_url()

    xmrig_config = {
        "autosave": True,
        "cpu": {
            "enabled": True,
            "huge-pages": True,
            "huge-pages-jit": True,
            "hw-aes": None,
            "priority": config.cpu_priority,
            "max-threads-hint": config.cpu_max_usage,
        },
        "donate-level": config.donate_level,
        "log-file": config.log_file,
        "pools": [
            {
                "url": pool_url,
                "user": config.wallet_address,
                "pass": config.worker_name,
                "rig-id": config.worker_name,
                "tls": config.use_tls,
                "keepalive": True,
                "nicehash": False,
            }
        ],
        "http": {
            "enabled": True,
            "host": "127.0.0.1",
            "port": config.api_port,
            "access-token": None,
            "restricted": True,
        },
    }

    if config.threads > 0:
        xmrig_config["cpu"]["max-threads-hint"] = min(
            100, int((config.threads / (os.cpu_count() or 1)) * 100)
        )

    return xmrig_config


class XMRigManager:
    """Manage the XMRig mining process."""

    def __init__(self, config: MinerConfig):
        self.config = config
        self.process: subprocess.Popen | None = None
        self.xmrig_path: Path | None = None
        self.config_path = Path.home() / ".crypto_miner" / "xmrig_config.json"

    def setup(self) -> bool:
        """Download and set up XMRig."""
        try:
            if self.config.xmrig_path:
                path = Path(self.config.xmrig_path)
                if path.exists():
                    self.xmrig_path = path
                    return True

            # Check if already installed
            existing = find_xmrig_binary(INSTALL_DIR)
            if existing:
                self.xmrig_path = existing
            else:
                # Check if xmrig is in PATH
                system_xmrig = shutil.which("xmrig")
                if system_xmrig:
                    self.xmrig_path = Path(system_xmrig)
                else:
                    self.xmrig_path = download_xmrig()

            return True
        except Exception as e:
            print(f"XMRig setup failed: {e}")
            return False

    def write_config(self) -> Path:
        """Write XMRig configuration to file."""
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        xmrig_config = generate_xmrig_config(self.config)
        with open(self.config_path, "w") as f:
            json.dump(xmrig_config, f, indent=2)
        return self.config_path

    def start(self) -> bool:
        """Start the XMRig mining process."""
        if self.is_running():
            print("Miner is already running!")
            return True

        if not self.xmrig_path or not self.xmrig_path.exists():
            if not self.setup():
                return False

        if not self.config.wallet_address:
            print("ERROR: Wallet address is required!")
            return False

        config_file = self.write_config()

        cmd = [str(self.xmrig_path), "--config", str(config_file)]
        cmd.extend(self.config.extra_args)

        try:
            if self.config.background_mode:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    start_new_session=True,
                )
            else:
                self.process = subprocess.Popen(
                    cmd,
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                )

            # Save PID for later management
            pid_file = Path.home() / ".crypto_miner" / "miner.pid"
            pid_file.write_text(str(self.process.pid))

            print(f"Miner started (PID: {self.process.pid})")
            return True

        except Exception as e:
            print(f"Failed to start miner: {e}")
            return False

    def stop(self) -> bool:
        """Stop the mining process."""
        if self.process and self.process.poll() is None:
            self.process.send_signal(signal.SIGINT)
            try:
                self.process.wait(timeout=10)
            except subprocess.TimeoutExpired:
                self.process.kill()
            print("Miner stopped.")
            return True

        # Try to stop via PID file
        pid_file = Path.home() / ".crypto_miner" / "miner.pid"
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip())
                os.kill(pid, signal.SIGINT)
                pid_file.unlink()
                print(f"Miner (PID: {pid}) stopped.")
                return True
            except (ProcessLookupError, ValueError):
                pid_file.unlink(missing_ok=True)

        print("No running miner found.")
        return False

    def is_running(self) -> bool:
        """Check if the miner is currently running."""
        if self.process and self.process.poll() is None:
            return True

        pid_file = Path.home() / ".crypto_miner" / "miner.pid"
        if pid_file.exists():
            try:
                pid = int(pid_file.read_text().strip())
                os.kill(pid, 0)
                return True
            except (ProcessLookupError, ValueError):
                pid_file.unlink(missing_ok=True)

        return False

    def get_status(self) -> dict:
        """Get current mining status from XMRig API."""
        try:
            response = requests.get(
                f"http://127.0.0.1:{self.config.api_port}/2/summary",
                timeout=5,
            )
            return response.json()
        except requests.RequestException:
            return {}

    def get_hashrate(self) -> dict:
        """Get current hashrate from XMRig API."""
        status = self.get_status()
        if not status:
            return {"current": 0, "average": 0, "max": 0}

        hashrate = status.get("hashrate", {})
        totals = hashrate.get("total", [0, 0, 0])
        return {
            "current": totals[0] if len(totals) > 0 else 0,
            "average": totals[1] if len(totals) > 1 else 0,
            "max": totals[2] if len(totals) > 2 else 0,
        }

    def get_mining_stats(self) -> dict:
        """Get comprehensive mining statistics."""
        status = self.get_status()
        if not status:
            return {
                "running": self.is_running(),
                "hashrate": {"current": 0, "average": 0, "max": 0},
                "shares": {"accepted": 0, "rejected": 0},
                "uptime": 0,
                "connection": "disconnected",
            }

        hashrate = status.get("hashrate", {})
        totals = hashrate.get("total", [0, 0, 0])
        results = status.get("results", {})
        connection = status.get("connection", {})

        return {
            "running": True,
            "hashrate": {
                "current": totals[0] if totals[0] else 0,
                "average": totals[1] if len(totals) > 1 and totals[1] else 0,
                "max": totals[2] if len(totals) > 2 and totals[2] else 0,
            },
            "shares": {
                "accepted": results.get("shares_good", 0),
                "rejected": results.get("shares_total", 0) - results.get("shares_good", 0),
            },
            "uptime": status.get("uptime", 0),
            "connection": {
                "pool": connection.get("pool", "N/A"),
                "uptime": connection.get("uptime", 0),
            },
            "cpu": status.get("cpu", {}),
            "version": status.get("version", "unknown"),
        }
