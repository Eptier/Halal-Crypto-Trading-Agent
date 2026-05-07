"""System information utilities for mining optimization."""

import platform
import subprocess

import psutil


def get_cpu_info() -> dict:
    """Get detailed CPU information."""
    info = {
        "name": platform.processor() or "Unknown",
        "cores_physical": psutil.cpu_count(logical=False) or 1,
        "cores_logical": psutil.cpu_count(logical=True) or 1,
        "frequency_mhz": 0,
        "architecture": platform.machine(),
    }

    freq = psutil.cpu_freq()
    if freq:
        info["frequency_mhz"] = int(freq.current)

    # Try to get CPU model name on Linux
    if platform.system() == "Linux":
        try:
            result = subprocess.run(
                ["lscpu"], capture_output=True, text=True, timeout=5
            )
            for line in result.stdout.split("\n"):
                if "Model name" in line:
                    info["name"] = line.split(":")[1].strip()
                    break
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    return info


def get_memory_info() -> dict:
    """Get system memory information."""
    mem = psutil.virtual_memory()
    return {
        "total_gb": round(mem.total / (1024**3), 2),
        "available_gb": round(mem.available / (1024**3), 2),
        "used_percent": mem.percent,
    }


def get_optimal_threads(max_cpu_percent: int = 75) -> int:
    """Calculate optimal mining threads based on CPU and desired usage."""
    logical_cores = psutil.cpu_count(logical=True) or 1
    optimal = max(1, int(logical_cores * (max_cpu_percent / 100)))
    return optimal


def get_system_summary() -> dict:
    """Get complete system summary for mining."""
    cpu = get_cpu_info()
    mem = get_memory_info()
    return {
        "os": f"{platform.system()} {platform.release()}",
        "cpu": cpu,
        "memory": mem,
        "optimal_threads": get_optimal_threads(),
        "mining_ready": mem["available_gb"] >= 2.0,  # RandomX needs ~2GB RAM
    }


def estimate_hashrate(cpu_name: str, threads: int) -> float:
    """Rough hashrate estimate for RandomX based on CPU type."""
    base_rates = {
        "ryzen 9": 1200,
        "ryzen 7": 800,
        "ryzen 5": 500,
        "i9": 700,
        "i7": 500,
        "i5": 350,
        "i3": 200,
        "xeon": 600,
    }

    cpu_lower = cpu_name.lower()
    per_thread_rate = 100  # default H/s per thread

    for key, rate in base_rates.items():
        if key in cpu_lower:
            per_thread_rate = rate / max(threads, 1)
            break

    return round(per_thread_rate * threads, 2)


def check_hugepages() -> dict:
    """Check if hugepages are enabled (important for RandomX performance)."""
    result = {"enabled": False, "total": 0, "free": 0, "suggestion": ""}

    if platform.system() != "Linux":
        result["suggestion"] = "Hugepages only available on Linux"
        return result

    try:
        with open("/proc/meminfo") as f:
            for line in f:
                if "HugePages_Total" in line:
                    result["total"] = int(line.split()[1])
                elif "HugePages_Free" in line:
                    result["free"] = int(line.split()[1])
    except FileNotFoundError:
        pass

    result["enabled"] = result["total"] > 0

    if not result["enabled"]:
        result["suggestion"] = (
            "Enable hugepages for +20% performance:\n"
            "  sudo sysctl -w vm.nr_hugepages=1280\n"
            "  sudo bash -c 'echo vm.nr_hugepages=1280 >> /etc/sysctl.conf'"
        )

    return result


def get_power_usage_estimate(threads: int) -> float:
    """Estimate power usage in watts for mining."""
    per_thread_watts = 8  # rough estimate
    base_system_watts = 50
    return base_system_watts + (threads * per_thread_watts)


def check_mining_compatibility() -> dict:
    """Check if the system is compatible with CPU mining."""
    cpu = get_cpu_info()
    mem = get_memory_info()

    issues = []
    warnings = []

    if mem["available_gb"] < 2.0:
        issues.append(
            f"Not enough RAM: {mem['available_gb']}GB available, need 2GB+ for RandomX"
        )

    if cpu["cores_logical"] < 2:
        warnings.append("Only 1 CPU thread available - mining will be very slow")

    if platform.machine() not in ("x86_64", "AMD64", "aarch64"):
        warnings.append(f"Architecture {platform.machine()} may not be fully supported")

    hugepages = check_hugepages()
    if not hugepages["enabled"]:
        warnings.append("Hugepages not enabled - performance will be reduced")

    return {
        "compatible": len(issues) == 0,
        "issues": issues,
        "warnings": warnings,
        "cpu": cpu,
        "memory": mem,
    }
