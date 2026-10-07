from __future__ import annotations

import os
import re
import shutil
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict, List, Tuple

import yaml

ROOT_DIR = Path(__file__).resolve().parents[1]
MRS_OUTPUT_DIR = ROOT_DIR / "mrs"
MRS_DOMAIN_DIR = MRS_OUTPUT_DIR / "domain"
MRS_IP_DIR = MRS_OUTPUT_DIR / "ip"

# 创建分类存放目录
MRS_DOMAIN_DIR.mkdir(parents=True, exist_ok=True)
MRS_IP_DIR.mkdir(parents=True, exist_ok=True)

MIHOMO_BIN = shutil.which("mihomo") or "mihomo"


def is_ip_cidr(text: str) -> bool:
    """判断字符串是否为 IP CIDR 格式"""
    text = text.strip()
    if "/" in text:
        ip_part = text.split("/")[0]
        if re.match(r"^[\d\.]+$", ip_part) or ":" in ip_part:
            return True
    return False


def classify_rules(lines: List[str]) -> Tuple[List[str], List[str]]:
    """分类拆分规则列表为 (域名规则列表, IP 规则列表)"""
    domains: List[str] = []
    ips: List[str] = []

    for line in lines:
        line = line.strip()
        if not line or line.startswith("#"):
            continue

        if line.startswith("-"):
            line = line.lstrip("-").strip()

        if "," in line:
            parts = [p.strip() for p in line.split(",")]
            rtype = parts[0].upper()
            val = parts[1] if len(parts) > 1 else ""

            if rtype in ["IP-CIDR", "IP-CIDR6", "GEOIP"]:
                ips.append(val)
            elif rtype in ["DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD"]:
                domains.append(val)
            else:
                if is_ip_cidr(val):
                    ips.append(val)
                elif val:
                    domains.append(val)
        else:
            if is_ip_cidr(line):
                ips.append(line)
            else:
                domains.append(line)

    return sorted(list(set(domains))), sorted(list(set(ips)))


def compile_to_mrs(behavior: str, input_file: Path, output_file: Path) -> bool:
    """调用 mihomo CLI 编译成 .mrs 二进制规则集"""
    if not input_file.exists() or input_file.stat().st_size == 0:
        return False

    cmd = [MIHOMO_BIN, "convert-ruleset", behavior, "text", str(input_file), str(output_file)]
    try:
        subprocess.run(cmd, capture_output=True, text=True, check=True)
        print(f"[MRS OK] {behavior} -> {output_file.relative_to(ROOT_DIR)} ({output_file.stat().st_size} bytes)", flush=True)
        return True
    except (subprocess.CalledProcessError, FileNotFoundError) as e:
        print(f"[MRS FAIL] Failed {input_file.name}: {e}", flush=True)
        return False


def process_clash_yaml(yaml_path: Path):
    """解析源 Clash YAML，提取域名和 IP，分别生成 .mrs"""
    if not yaml_path.exists():
        return

    print(f"=== Processing Rule Source: {yaml_path.name} ===", flush=True)
    try:
        content = yaml_path.read_text(encoding="utf-8")
        data = yaml.safe_load(content) or {}
    except Exception as e:
        print(f"Error loading {yaml_path}: {e}", flush=True)
        return

    raw_rules = data.get("payload", []) or data.get("rules", [])
    if raw_rules:
        domains, ips = classify_rules([str(r) for r in raw_rules])
        base_name = yaml_path.stem

        if domains:
            tmp_domain_file = MRS_OUTPUT_DIR / f"_tmp_{base_name}_domains.txt"
            tmp_domain_file.write_text("\n".join(domains), encoding="utf-8")
            compile_to_mrs("domain", tmp_domain_file, MRS_DOMAIN_DIR / f"{base_name}.mrs")
            tmp_domain_file.unlink(missing_ok=True)

        if ips:
            tmp_ip_file = MRS_OUTPUT_DIR / f"_tmp_{base_name}_ips.txt"
            tmp_ip_file.write_text("\n".join(ips), encoding="utf-8")
            compile_to_mrs("ipcidr", tmp_ip_file, MRS_IP_DIR / f"{base_name}_ip.mrs")
            tmp_ip_file.unlink(missing_ok=True)


def process_text_domains(txt_path: Path):
    """直接将 txt 格式的域名列表编译为 domain .mrs"""
    if not txt_path.exists():
        return
    base_name = txt_path.stem
    domains, ips = classify_rules(txt_path.read_text(encoding="utf-8").splitlines())

    if domains:
        tmp_domain_file = MRS_OUTPUT_DIR / f"_tmp_{base_name}_domains.txt"
        tmp_domain_file.write_text("\n".join(domains), encoding="utf-8")
        compile_to_mrs("domain", tmp_domain_file, MRS_DOMAIN_DIR / f"{base_name}.mrs")
        tmp_domain_file.unlink(missing_ok=True)

    if ips:
        tmp_ip_file = MRS_OUTPUT_DIR / f"_tmp_{base_name}_ips.txt"
        tmp_ip_file.write_text("\n".join(ips), encoding="utf-8")
        compile_to_mrs("ipcidr", tmp_ip_file, MRS_IP_DIR / f"{base_name}_ip.mrs")
        tmp_ip_file.unlink(missing_ok=True)


def main() -> int:
    print("=== TVBoxSource MRS Compiler Engine ===", flush=True)
    print(f"Output Domain MRS: {MRS_DOMAIN_DIR}", flush=True)
    print(f"Output IP MRS: {MRS_IP_DIR}", flush=True)

    # 1. 编译核心规则文件
    for yaml_file in [ROOT_DIR / "clash_rules_direct.yaml", ROOT_DIR / "clash_rules_proxy.yaml"]:
        process_clash_yaml(yaml_file)

    # 2. 编译纯文本规则
    for txt_file in [ROOT_DIR / "domains_direct.txt", ROOT_DIR / "domains_proxy.txt", ROOT_DIR / "adguard_direct.txt", ROOT_DIR / "adguard_proxy.txt"]:
        process_text_domains(txt_file)

    print("=== TVBoxSource MRS Compile Complete ===", flush=True)
    return 0


if __name__ == "__main__":
    sys.exit(main())
