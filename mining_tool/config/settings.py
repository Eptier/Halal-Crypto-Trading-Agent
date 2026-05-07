"""Mining configuration settings and defaults."""

from dataclasses import dataclass, field
from pathlib import Path

import yaml

DEFAULT_CONFIG_PATH = Path.home() / ".crypto_miner" / "config.yaml"

# Popular Monero mining pools
MINING_POOLS = {
    "moneroocean": {
        "name": "MoneroOcean",
        "url": "gulf.moneroocean.stream",
        "port": 10128,
        "tls_port": 20128,
        "fee": 0.0,
        "description": "Auto-switching pool, best for CPU mining",
    },
    "p2pool": {
        "name": "P2Pool (Decentralized)",
        "url": "p2pool.io",
        "port": 3333,
        "tls_port": None,
        "fee": 0.0,
        "description": "Decentralized pool, no fees, supports network",
    },
    "nanopool": {
        "name": "Nanopool",
        "url": "xmr-eu1.nanopool.org",
        "port": 14433,
        "tls_port": 14433,
        "fee": 1.0,
        "description": "Large stable pool with low minimum payout",
    },
    "hashvault": {
        "name": "HashVault",
        "url": "pool.hashvault.pro",
        "port": 3333,
        "tls_port": 443,
        "fee": 0.9,
        "description": "Reliable pool with good uptime",
    },
    "supportxmr": {
        "name": "SupportXMR",
        "url": "pool.supportxmr.com",
        "port": 3333,
        "tls_port": 443,
        "fee": 0.6,
        "description": "Community-supported mining pool",
    },
}

# Supported minable coins (CPU-friendly)
SUPPORTED_COINS = {
    "xmr": {
        "name": "Monero",
        "symbol": "XMR",
        "algorithm": "RandomX",
        "cpu_friendly": True,
        "description": "Best CPU-mineable coin, privacy-focused",
    },
    "rtm": {
        "name": "Raptoreum",
        "symbol": "RTM",
        "algorithm": "GhostRider",
        "cpu_friendly": True,
        "description": "CPU-only coin with GhostRider algorithm",
    },
    "vrsc": {
        "name": "Verus",
        "symbol": "VRSC",
        "algorithm": "VerusHash",
        "cpu_friendly": True,
        "description": "CPU-optimized with VerusHash 2.2",
    },
}


@dataclass
class MinerConfig:
    """Configuration for the mining tool."""

    wallet_address: str = ""
    coin: str = "xmr"
    pool: str = "moneroocean"
    custom_pool_url: str = ""
    custom_pool_port: int = 3333
    worker_name: str = "my_pc"
    threads: int = 0  # 0 = auto-detect
    cpu_priority: int = 2  # 1-5 (1=lowest, 5=highest)
    cpu_max_usage: int = 75  # percentage
    use_tls: bool = True
    donate_level: int = 1  # XMRig donation %
    log_file: str = "mining.log"
    auto_start: bool = False
    dashboard_port: int = 5000
    xmrig_path: str = ""  # auto-detect or manual path
    api_port: int = 8080  # XMRig API port
    background_mode: bool = False
    extra_args: list[str] = field(default_factory=list)

    def get_pool_url(self) -> str:
        if self.custom_pool_url:
            return f"{self.custom_pool_url}:{self.custom_pool_port}"
        pool_info = MINING_POOLS.get(self.pool, MINING_POOLS["moneroocean"])
        use_tls = self.use_tls and pool_info["tls_port"]
        port = pool_info["tls_port"] if use_tls else pool_info["port"]
        return f"{pool_info['url']}:{port}"

    def get_pool_name(self) -> str:
        if self.custom_pool_url:
            return f"Custom ({self.custom_pool_url})"
        pool_info = MINING_POOLS.get(self.pool, MINING_POOLS["moneroocean"])
        return pool_info["name"]

    def save(self, path: Path | None = None) -> None:
        config_path = path or DEFAULT_CONFIG_PATH
        config_path.parent.mkdir(parents=True, exist_ok=True)
        data = {
            "wallet_address": self.wallet_address,
            "coin": self.coin,
            "pool": self.pool,
            "custom_pool_url": self.custom_pool_url,
            "custom_pool_port": self.custom_pool_port,
            "worker_name": self.worker_name,
            "threads": self.threads,
            "cpu_priority": self.cpu_priority,
            "cpu_max_usage": self.cpu_max_usage,
            "use_tls": self.use_tls,
            "donate_level": self.donate_level,
            "log_file": self.log_file,
            "auto_start": self.auto_start,
            "dashboard_port": self.dashboard_port,
            "xmrig_path": self.xmrig_path,
            "api_port": self.api_port,
            "background_mode": self.background_mode,
            "extra_args": self.extra_args,
        }
        with open(config_path, "w") as f:
            yaml.dump(data, f, default_flow_style=False)

    @classmethod
    def load(cls, path: Path | None = None) -> "MinerConfig":
        config_path = path or DEFAULT_CONFIG_PATH
        if not config_path.exists():
            return cls()
        with open(config_path) as f:
            data = yaml.safe_load(f) or {}
        return cls(**{k: v for k, v in data.items() if hasattr(cls, k)})
