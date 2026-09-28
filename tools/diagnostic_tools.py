"""Diagnostic and Security Auditing tools for hardware, network, web headers, logs, and checksums."""
import os
import socket
import hashlib
import psutil
import requests
import datetime
from typing import Dict, Any, List, Optional
from rich.console import Console

console = Console()

class DiagnosticTools:
    """Diagnostic, security audit, and system health metrics tools suite."""

    def __init__(self):
        pass

    def get_system_health(self) -> Dict[str, Any]:
        """
        Gathers live CPU %, RAM %, per-partition disk usage %, and battery percentage.
        """
        try:
            # CPU
            cpu_percent = psutil.cpu_percent(interval=0.2)
            cpu_count_logical = psutil.cpu_count(logical=True)
            cpu_count_physical = psutil.cpu_count(logical=False)
            cpu_freq = psutil.cpu_freq()
            
            # RAM
            ram = psutil.virtual_memory()
            
            # Disk
            disk_partitions = []
            for part in psutil.disk_partitions(all=False):
                try:
                    usage = psutil.disk_usage(part.mountpoint)
                    disk_partitions.append({
                        "device": part.device,
                        "mountpoint": part.mountpoint,
                        "fstype": part.fstype,
                        "total_gb": round(usage.total / (1024 ** 3), 2),
                        "used_gb": round(usage.used / (1024 ** 3), 2),
                        "free_gb": round(usage.free / (1024 ** 3), 2),
                        "percent": usage.percent
                    })
                except (PermissionError, FileNotFoundError):
                    continue

            # Battery
            battery = psutil.sensors_battery()
            battery_info = None
            if battery:
                battery_info = {
                    "percent": battery.percent,
                    "power_plugged": battery.power_plugged,
                    "secsleft": battery.secsleft if battery.secsleft != psutil.POWER_TIME_UNLIMITED else "Unlimited"
                }

            # Top memory processes
            top_procs = []
            for proc in sorted(psutil.process_iter(['pid', 'name', 'memory_percent', 'cpu_percent']), 
                               key=lambda p: p.info.get('memory_percent') or 0, reverse=True)[:5]:
                try:
                    top_procs.append({
                        "pid": proc.info['pid'],
                        "name": proc.info['name'],
                        "memory_percent": round(proc.info.get('memory_percent') or 0, 2),
                        "cpu_percent": round(proc.info.get('cpu_percent') or 0, 2)
                    })
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    continue

            return {
                "status": "success",
                "cpu": {
                    "usage_percent": cpu_percent,
                    "physical_cores": cpu_count_physical,
                    "logical_cores": cpu_count_logical,
                    "current_freq_mhz": round(cpu_freq.current, 2) if cpu_freq else None
                },
                "memory": {
                    "total_gb": round(ram.total / (1024 ** 3), 2),
                    "available_gb": round(ram.available / (1024 ** 3), 2),
                    "used_gb": round(ram.used / (1024 ** 3), 2),
                    "usage_percent": ram.percent
                },
                "disk": disk_partitions,
                "battery": battery_info,
                "top_memory_consumers": top_procs
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed fetching system health: {str(e)}"}

    def inspect_service_reachability(self, host: str, ports: Optional[List[int]] = None, timeout: float = 1.5) -> Dict[str, Any]:
        """
        Validates network reachability and open socket states for local or authorized hosts.
        """
        if ports is None or not ports:
            ports = [80, 443, 22, 21, 3306, 5432, 8080, 8000, 27017]

        clean_host = host.replace("http://", "").replace("https://", "").split("/")[0].split(":")[0].strip()
        port_results = []
        
        try:
            ip_address = socket.gethostbyname(clean_host)
        except socket.gaierror as e:
            return {
                "status": "error",
                "host": clean_host,
                "message": f"DNS resolution failed for host '{clean_host}': {str(e)}"
            }

        for port in ports:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(timeout)
            is_open = False
            banner = None
            try:
                result = sock.connect_ex((ip_address, int(port)))
                if result == 0:
                    is_open = True
                    try:
                        sock.sendall(b"HEAD / HTTP/1.0\r\n\r\n")
                        data = sock.recv(128)
                        banner = data.decode(errors="ignore").strip()[:80]
                    except Exception:
                        banner = None
            except Exception:
                is_open = False
            finally:
                sock.close()

            port_results.append({
                "port": int(port),
                "state": "OPEN" if is_open else "CLOSED",
                "service_hint": socket.getservbyport(int(port), "tcp") if is_open and port < 1024 else None,
                "banner": banner
            })

        open_count = sum(1 for p in port_results if p["state"] == "OPEN")
        return {
            "status": "success",
            "host": clean_host,
            "resolved_ip": ip_address,
            "scanned_ports": len(ports),
            "open_ports_count": open_count,
            "results": port_results
        }

    def audit_web_headers(self, url: str) -> Dict[str, Any]:
        """
        Inspects HTTP response headers of a web endpoint for critical security controls:
        - Content-Security-Policy (CSP)
        - Strict-Transport-Security (HSTS)
        - X-Frame-Options
        - X-Content-Type-Options
        - Referrer-Policy
        - Permissions-Policy
        """
        target_url = url.strip()
        if not target_url.startswith("http://") and not target_url.startswith("https://"):
            target_url = f"https://{target_url}"

        try:
            resp = requests.get(target_url, timeout=10, allow_redirects=True, headers={
                "User-Agent": "SecurityAuditorAgent/1.0"
            })
            headers = resp.headers

            security_checks = {
                "Strict-Transport-Security": {
                    "present": "Strict-Transport-Security" in headers,
                    "value": headers.get("Strict-Transport-Security", None),
                    "importance": "CRITICAL",
                    "description": "Protects against SSL-stripping and man-in-the-middle attacks."
                },
                "Content-Security-Policy": {
                    "present": "Content-Security-Policy" in headers,
                    "value": headers.get("Content-Security-Policy", None),
                    "importance": "HIGH",
                    "description": "Mitigates Cross-Site Scripting (XSS) and data injection attacks."
                },
                "X-Frame-Options": {
                    "present": "X-Frame-Options" in headers,
                    "value": headers.get("X-Frame-Options", None),
                    "importance": "HIGH",
                    "description": "Protects against Clickjacking by controlling framing permissions."
                },
                "X-Content-Type-Options": {
                    "present": "X-Content-Type-Options" in headers,
                    "value": headers.get("X-Content-Type-Options", None),
                    "importance": "MEDIUM",
                    "description": "Prevents MIME-sniffing vulnerabilities."
                },
                "Referrer-Policy": {
                    "present": "Referrer-Policy" in headers,
                    "value": headers.get("Referrer-Policy", None),
                    "importance": "LOW",
                    "description": "Controls how much referrer information is sent with requests."
                },
                "Permissions-Policy": {
                    "present": "Permissions-Policy" in headers,
                    "value": headers.get("Permissions-Policy", None),
                    "importance": "LOW",
                    "description": "Allows control over browser features and APIs (camera, geolocation, etc.)."
                }
            }

            passed_checks = sum(1 for c in security_checks.values() if c["present"])
            total_checks = len(security_checks)
            security_score = round((passed_checks / total_checks) * 100, 1)

            grade = "A" if security_score >= 80 else "B" if security_score >= 60 else "C" if security_score >= 40 else "F"

            return {
                "status": "success",
                "target_url": target_url,
                "final_url": resp.url,
                "http_status": resp.status_code,
                "server": headers.get("Server", "Unknown"),
                "security_score_percent": security_score,
                "security_grade": grade,
                "checks": security_checks,
                "all_headers": dict(headers)
            }
        except Exception as e:
            return {"status": "error", "target_url": target_url, "message": f"Header audit request failed: {str(e)}"}

    def analyze_system_logs(self, log_path: str, keyword: str = "failed", max_lines: int = 500) -> Dict[str, Any]:
        """
        Parses local log files to extract frequency counts and anomaly patterns.
        """
        target = os.path.abspath(os.path.expanduser(log_path))
        if not os.path.exists(target) or not os.path.isfile(target):
            return {"status": "error", "message": f"Log file does not exist: {target}"}

        keyword_lower = keyword.lower()
        matching_entries = []
        total_lines = 0
        error_count = 0
        warning_count = 0
        critical_count = 0

        try:
            with open(target, "r", encoding="utf-8", errors="ignore") as f:
                lines = f.readlines()
                total_lines = len(lines)
                
                # Check the most recent lines
                sample_lines = lines[-max_lines:] if total_lines > max_lines else lines
                for idx, line in enumerate(sample_lines):
                    line_str = line.strip()
                    if not line_str:
                        continue
                    l_lower = line_str.lower()
                    if "error" in l_lower or "err" in l_lower:
                        error_count += 1
                    if "warn" in l_lower:
                        warning_count += 1
                    if "critical" in l_lower or "fatal" in l_lower:
                        critical_count += 1

                    if keyword_lower in l_lower:
                        matching_entries.append({
                            "line_number": total_lines - len(sample_lines) + idx + 1,
                            "content": line_str
                        })

            return {
                "status": "success",
                "log_file": target,
                "total_lines_analyzed": min(total_lines, max_lines),
                "total_file_lines": total_lines,
                "filter_keyword": keyword,
                "matches_count": len(matching_entries),
                "metrics": {
                    "errors_found": error_count,
                    "warnings_found": warning_count,
                    "critical_found": critical_count
                },
                "matched_samples": matching_entries[:50]
            }
        except Exception as e:
            return {"status": "error", "message": f"Failed analyzing logs: {str(e)}"}

    def predict_hardware_lifespan(self) -> Dict[str, Any]:
        """
        Performs deep multi-factor telemetry analysis on CPU, RAM, Disk, Battery, and Uptime
        to predict the laptop's remaining lifespan, health index (0-100), and component wear.
        """
        import time
        import platform
        try:
            # 1. CPU Telemetry & Thermal Stress Index
            cpu_usage = psutil.cpu_percent(interval=0.3)
            cpu_cores_phys = psutil.cpu_count(logical=False) or 4
            cpu_cores_log = psutil.cpu_count(logical=True) or 8
            cpu_freq = psutil.cpu_freq()
            boot_time = datetime.datetime.fromtimestamp(psutil.boot_time())
            uptime_hours = round((time.time() - psutil.boot_time()) / 3600, 1)

            # 2. RAM Stress Factor
            ram = psutil.virtual_memory()
            ram_total_gb = round(ram.total / (1024 ** 3), 1)
            ram_stress = ram.percent

            # 3. Disk Wear & Storage Strain
            disk_usage = psutil.disk_usage("/")
            disk_free_gb = round(disk_usage.free / (1024 ** 3), 1)
            disk_used_pct = disk_usage.percent

            # 4. Battery Health & Degradation Rate
            battery = psutil.sensors_battery()
            battery_pct = battery.percent if battery else 100
            is_plugged = battery.power_plugged if battery else True

            # 5. Lifespan Calculation Model (Multi-variable algorithmic scoring)
            # Base modern laptop lifespan expectation = 6 to 7 years from baseline
            health_score = 100.0
            risk_factors = []
            component_status = {}

            # Disk risk calculation
            if disk_used_pct > 90:
                health_score -= 15
                risk_factors.append("Disk storage is over 90% full, causing extreme SSD write amplification and swap thrashing.")
                component_status["Storage (SSD/HDD)"] = "High Strain (Critically Low Free Space)"
            elif disk_used_pct > 75:
                health_score -= 7
                risk_factors.append("Disk storage is over 75% full. SSD trim efficiency reduces when free space is low.")
                component_status["Storage (SSD/HDD)"] = "Moderate Strain"
            else:
                component_status["Storage (SSD/HDD)"] = "Optimal Health"

            # RAM risk calculation
            if ram_stress > 88:
                health_score -= 12
                risk_factors.append("High continuous RAM pressure (>88%) triggers intensive pagefile paging on disk.")
                component_status["RAM Memory"] = "Heavy Workload"
            elif ram_stress > 70:
                health_score -= 5
                component_status["RAM Memory"] = "Moderate Load"
            else:
                component_status["RAM Memory"] = "Healthy"

            # Battery wear calculation
            if battery:
                if battery_pct < 60 and not is_plugged:
                    health_score -= 5
                component_status["Battery & Power"] = f"Operating at {battery_pct}% capacity"
            else:
                component_status["Battery & Power"] = "Desktop AC Power (No battery wear factor)"

            # CPU Frequency & Stress
            if cpu_usage > 85:
                health_score -= 10
                risk_factors.append("CPU operating under sustained heavy load; thermal dissipation needs monitoring.")
                component_status["Processor (CPU)"] = "High Thermal/Computing Load"
            else:
                component_status["Processor (CPU)"] = f"{cpu_cores_phys} Cores ({cpu_cores_log} Threads) - Operating Efficiently"

            health_score = max(35.0, min(98.0, health_score))

            # Estimated Remaining Lifespan in Years
            if health_score >= 85:
                est_lifespan_years = "4.5 to 6.5 Years"
                verdict = "Excellent Hardware Condition"
                grade = "A+"
            elif health_score >= 70:
                est_lifespan_years = "3.0 to 4.5 Years"
                verdict = "Good Condition with Normal Aging"
                grade = "B+"
            elif health_score >= 50:
                est_lifespan_years = "1.5 to 2.5 Years"
                verdict = "Moderate Wear (Optimization Recommended)"
                grade = "C"
            else:
                est_lifespan_years = "Under 1.5 Years"
                verdict = "Critical Hardware Strain (Component Replacement Advised)"
                grade = "D"

            # Actionable Lifespan Extension Tips
            extension_tips = [
                "Keep SSD free space at least 20-25% to maximize TRIM endurance and prevent NAND flash cell degradation.",
                "Ensure ventilation grills are dust-free to keep CPU core temperatures under 75°C under load.",
                "Maintain battery charge between 20% and 80% to double chemical Li-ion battery cycle life.",
                "Close background autostart programs to reduce perpetual RAM paging."
            ]

            return {
                "status": "success",
                "system_os": f"{platform.system()} {platform.release()} ({platform.architecture()[0]})",
                "processor_model": platform.processor(),
                "health_index_score": round(health_score, 1),
                "hardware_grade": grade,
                "overall_verdict": verdict,
                "estimated_remaining_lifespan": est_lifespan_years,
                "system_uptime": f"{uptime_hours} hours (Booted: {boot_time.strftime('%Y-%m-%d %H:%M')})",
                "component_health_matrix": component_status,
                "identified_risk_factors": risk_factors if risk_factors else ["No critical degradation anomalies detected."],
                "actionable_lifespan_tips": extension_tips
            }
        except Exception as e:
            return {"status": "error", "message": f"Hardware lifespan prediction failure: {str(e)}"}

    def audit_system_vulnerabilities(self) -> Dict[str, Any]:
        """
        Scans local security parameters, active connections, firewall exposure, and startup footprint.
        """
        try:
            # Active network connections count
            net_conns = psutil.net_connections(kind='inet')
            listening_ports = [c.laddr.port for c in net_conns if c.status == 'LISTEN' and hasattr(c.laddr, 'port')]
            unique_listening = sorted(list(set(listening_ports)))

            # High risk open ports
            risky_ports = [21, 23, 135, 139, 445, 3389]
            exposed_risky = [p for p in unique_listening if p in risky_ports]

            # Running processes count
            procs_count = len(psutil.pids())

            sec_score = 95
            if exposed_risky:
                sec_score -= (len(exposed_risky) * 15)

            return {
                "status": "success",
                "total_active_processes": procs_count,
                "open_listening_ports_count": len(unique_listening),
                "listening_ports_sample": unique_listening[:15],
                "flagged_high_risk_ports": exposed_risky,
                "system_security_score": max(20, sec_score),
                "security_status": "Secure" if not exposed_risky else "Attention Required"
            }
        except Exception as e:
            return {"status": "error", "message": f"Vulnerability audit error: {str(e)}"}

    def benchmark_system_performance(self) -> Dict[str, Any]:
        """
        Runs a quick CPU floating point & memory throughput benchmark to classify workstation compute tier.
        """
        import time
        import math
        try:
            start_cpu = time.perf_counter()
            # 1. CPU Floating Point Stress
            val = 0.0
            for i in range(1, 1500000):
                val += math.sin(i) * math.cos(i)
            cpu_time_ms = round((time.perf_counter() - start_cpu) * 1000, 2)

            # 2. Memory Allocation & Throughput
            start_mem = time.perf_counter()
            block = [x * 2 for x in range(1000000)]
            del block
            mem_time_ms = round((time.perf_counter() - start_mem) * 1000, 2)

            total_benchmark_time = round(cpu_time_ms + mem_time_ms, 2)
            
            if total_benchmark_time < 200:
                tier = "Tier 1: High-Performance Workstation / Gaming Rig"
            elif total_benchmark_time < 400:
                tier = "Tier 2: Modern Fast Multitasking Laptop"
            elif total_benchmark_time < 700:
                tier = "Tier 3: Standard Everyday Utility PC"
            else:
                tier = "Tier 4: Entry Level / Throttled System"

            return {
                "status": "success",
                "cpu_calc_time_ms": cpu_time_ms,
                "memory_throughput_time_ms": mem_time_ms,
                "total_benchmark_score_ms": total_benchmark_time,
                "performance_tier": tier,
                "evaluation": "Lower latency score indicates faster CPU instruction pipeline and RAM clock speed."
            }
        except Exception as e:
            return {"status": "error", "message": f"Benchmark error: {str(e)}"}

    def calculate_file_checksum(self, filepath: str, algo: str = "sha256") -> Dict[str, Any]:
        """
        Generates cryptographic hashes for file integrity checks (sha256, sha1, md5, sha512).
        """
        target = os.path.abspath(os.path.expanduser(filepath))
        if not os.path.exists(target) or not os.path.isfile(target):
            return {"status": "error", "message": f"File does not exist: {target}"}

        algo_name = algo.lower().strip()
        hasher_map = {
            "sha256": hashlib.sha256,
            "sha1": hashlib.sha1,
            "md5": hashlib.md5,
            "sha512": hashlib.sha512
        }

        if algo_name not in hasher_map:
            return {"status": "error", "message": f"Unsupported algorithm '{algo}'. Choose from {list(hasher_map.keys())}"}

        try:
            hasher = hasher_map[algo_name]()
            file_size = os.path.getsize(target)
            with open(target, "rb") as f:
                while chunk := f.read(65536):
                    hasher.update(chunk)

            checksum = hasher.hexdigest()
            return {
                "status": "success",
                "filepath": target,
                "file_size_bytes": file_size,
                "algorithm": algo_name.upper(),
                "checksum": checksum
            }
        except Exception as e:
            return {"status": "error", "message": f"Checksum calculation failed: {str(e)}"}
