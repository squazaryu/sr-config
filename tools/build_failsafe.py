#!/usr/bin/env python3
"""Build the self-contained Shadowrocket fallback configuration.

The main config intentionally keeps the current rule order and policies, but
replaces remote RULE-SET entries with a reviewed snapshot of their contents.
The source URL and SHA-256 digest are recorded next to every embedded list.
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import time
from http.client import IncompleteRead
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATH = ROOT / "url-set-main.conf"
FETCH_TIMEOUT = 60
FETCH_ATTEMPTS = 3

APPLE_REAL_IP = (
    "time.*.com,ntp.*.com,*.cloudflareclient.com,time.apple.com,*.ntp.apple.com,"
    "apple.com,icloud.com,icloud-content.com,mzstatic.com,cdn-apple.com,aaplimg.com,"
    "appstore.com,apple-cloudkit.com,apple-livephotoskit.com,apple-dns.net,*.apple.com,"
    "*.icloud.com,*.icloud-content.com,*.mzstatic.com,*.cdn-apple.com,*.aaplimg.com,"
    "*.appstore.com,*.apple-cloudkit.com,*.apple-livephotoskit.com,*.apple-dns.net"
)

APPLE_WATCH_DIRECT_RULES = (
    "DOMAIN,appldnld.apple.com,DIRECT",
    "DOMAIN,gdmf.apple.com,DIRECT",
    "DOMAIN,gg.apple.com,DIRECT",
    "DOMAIN,gs.apple.com,DIRECT",
    "DOMAIN,mesu.apple.com,DIRECT",
    "DOMAIN,updates-http.cdn-apple.com,DIRECT",
    "DOMAIN,updates.cdn-apple.com,DIRECT",
    "DOMAIN,certs.apple.com,DIRECT",
    "DOMAIN,crl.apple.com,DIRECT",
    "DOMAIN,ocsp.apple.com,DIRECT",
    "DOMAIN,ocsp2.apple.com,DIRECT",
    "DOMAIN,valid.apple.com,DIRECT",
    "DOMAIN,crl3.digicert.com,DIRECT",
    "DOMAIN,crl4.digicert.com,DIRECT",
    "DOMAIN,ocsp.digicert.com,DIRECT",
    "DOMAIN,ocsp.digicert.cn,DIRECT",
)

SOURCES = (
    {
        "url": "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Shadowrocket/YouTube/YouTube.list",
        "policy": "🇫🇮 Финляндия",
        "options": (),
    },
    {
        "url": "https://raw.githubusercontent.com/blackmatrix7/ios_rule_script/master/rule/Shadowrocket/Telegram/Telegram.list",
        "policy": "🇫🇮 Финляндия",
        "options": (),
    },
    {
        "url": "https://raw.githubusercontent.com/misha-tgshv/shadowrocket-configuration-file/refs/heads/release/rules/domains_community.list",
        "policy": "PROXY",
        "options": (),
    },
    {
        "url": "https://raw.githubusercontent.com/misha-tgshv/shadowrocket-configuration-file/refs/heads/release/rules/domains_refilter.list",
        "policy": "PROXY",
        "options": (),
    },
    {
        "url": "https://raw.githubusercontent.com/misha-tgshv/shadowrocket-configuration-file/refs/heads/release/rules/ips_refilter.list",
        "policy": "PROXY",
        "options": ("no-resolve",),
    },
    {
        "url": "https://raw.githubusercontent.com/misha-tgshv/shadowrocket-configuration-file/refs/heads/release/rules/domains_discord.list",
        "policy": "PROXY",
        "options": (),
    },
    {
        "url": "https://raw.githubusercontent.com/helmiau/clashrules/refs/heads/main/shadowrocket/Game_Discord_Ports.list",
        "policy": "PROXY",
        "options": (),
    },
    {
        "url": "https://raw.githubusercontent.com/carrnot/shadowrocket-rules/release/reject.txt",
        "policy": "REJECT",
        "options": (),
    },
)


def fetch_source(url: str) -> tuple[str, str]:
    payload = b""
    last_error: Exception | None = None
    for attempt in range(1, FETCH_ATTEMPTS + 1):
        request = Request(url, headers={"User-Agent": "sr-config-failsafe-builder/1.0"})
        try:
            with urlopen(request, timeout=FETCH_TIMEOUT) as response:
                payload = response.read()
                content_length = response.headers.get("Content-Length")
                if content_length and len(payload) != int(content_length):
                    raise RuntimeError(
                        f"неполный ответ: получено {len(payload)} из {content_length} bytes"
                    )
            break
        except (HTTPError, URLError, TimeoutError, OSError, IncompleteRead, ValueError, RuntimeError) as exc:
            last_error = exc
            if attempt < FETCH_ATTEMPTS:
                time.sleep(attempt)
    else:
        raise RuntimeError(
            f"не удалось загрузить {url} после {FETCH_ATTEMPTS} попыток: {last_error}"
        ) from last_error

    text = payload.decode("utf-8-sig", errors="strict")
    probe = text.lstrip().lower()[:512]
    if "<html" in probe or "<!doctype" in probe:
        raise RuntimeError(f"источник вернул HTML вместо rule-set: {url}")
    if not any(line.strip() and not line.lstrip().startswith("#") for line in text.splitlines()):
        raise RuntimeError(f"источник не содержит правил: {url}")
    return text, hashlib.sha256(payload).hexdigest()


def annotate_rule(line: str, policy: str, options: tuple[str, ...], source: str) -> str:
    fields = [field.strip() for field in line.strip().split(",")]
    if len(fields) < 2 or not fields[0]:
        raise RuntimeError(f"некорректное правило в {source}: {line!r}")

    # The current upstream lists are policy-free. Telegram carries
    # no-resolve as its third field; preserve it after inserting the policy.
    if len(fields) > 2 and fields[2].upper() in {"DIRECT", "PROXY", "REJECT", "PASS", "DROP"}:
        raise RuntimeError(f"внешний список уже содержит policy: {source}: {line!r}")

    tail = fields[2:]
    for option in options:
        if option not in tail:
            tail.append(option)
    return ",".join(fields[:2] + [policy] + tail)


def embedded_source_block(source: dict[str, object], text: str, digest: str) -> list[str]:
    policy = str(source["policy"])
    options = tuple(source["options"])  # type: ignore[arg-type]
    url = str(source["url"])
    block = [
        f"# BEGIN FAILSAFE SOURCE: {url}",
        f"# SHA256: {digest}",
    ]
    rule_count = 0
    for raw_line in text.splitlines():
        stripped = raw_line.strip()
        if not stripped:
            block.append("")
        elif stripped.startswith("#"):
            block.append(raw_line.rstrip())
        else:
            block.append(annotate_rule(raw_line, policy, options, url))
            rule_count += 1
    block.insert(2, f"# RULES: {rule_count}")
    block.extend((f"# END FAILSAFE SOURCE: {url}", ""))
    return block


def replace_source_block(lines: list[str], source: dict[str, object], block: list[str]) -> None:
    url = str(source["url"])
    marker = f"# BEGIN FAILSAFE SOURCE: {url}"
    end_marker = f"# END FAILSAFE SOURCE: {url}"
    start = next((index for index, line in enumerate(lines) if line == marker), None)
    if start is not None:
        end = next(
            (index for index in range(start + 1, len(lines)) if lines[index] == end_marker),
            None,
        )
        if end is None:
            raise RuntimeError(f"повреждён snapshot-блок: {url}")
        after = end + 1
        while after < len(lines) and lines[after] == "":
            after += 1
        lines[start:after] = block
        return

    prefix = f"RULE-SET,{url},"
    start = next((index for index, line in enumerate(lines) if line.startswith(prefix)), None)
    if start is None:
        raise RuntimeError(f"не найден RULE-SET для замены: {url}")
    lines[start : start + 1] = block


def update_general(lines: list[str]) -> None:
    for index, line in enumerate(lines):
        if line.startswith("# Shadowrocket:"):
            lines[index] = "# Shadowrocket: self-contained failsafe snapshot"
        elif line.startswith("dns-direct-system ="):
            lines[index] = "dns-direct-system = true"
        elif line.startswith("tun-excluded-routes =") and "17.0.0.0/8" not in line:
            lines[index] = f"{line},17.0.0.0/8"
        elif line.startswith("always-real-ip ="):
            lines[index] = f"always-real-ip = {APPLE_REAL_IP}"


def ensure_apple_watch_rules(lines: list[str]) -> None:
    marker = "# watchOS / Apple software updates — встроенные правила"
    if marker in lines:
        missing = [rule for rule in APPLE_WATCH_DIRECT_RULES if rule not in lines]
        if missing:
            raise RuntimeError(
                "неполный встроенный блок Apple/watchOS: " + ", ".join(missing)
            )
        return

    try:
        anchor = next(i for i, line in enumerate(lines) if line == "DOMAIN-SUFFIX,local,DIRECT")
    except StopIteration as exc:
        raise RuntimeError("не найден anchor для встроенных Apple/watchOS правил") from exc

    insert_at = anchor + 1
    while insert_at < len(lines) and lines[insert_at] == "":
        insert_at += 1
    block = [
        marker,
        "# Не выносить во внешний RULE-SET: проверка обновления не должна зависеть",
        "# от загрузки списков из GitHub.",
        *APPLE_WATCH_DIRECT_RULES[:7],
        "",
        "# Проверка сертификатов Apple / DigiCert",
        *APPLE_WATCH_DIRECT_RULES[7:],
        "",
    ]
    lines[insert_at:insert_at] = block


def ensure_apple_rules(lines: list[str]) -> None:
    required = [
        "DOMAIN-SUFFIX,apple-cloudkit.com,DIRECT",
        "DOMAIN-SUFFIX,apple-livephotoskit.com,DIRECT",
        "DOMAIN-SUFFIX,apple-dns.net,DIRECT",
    ]
    try:
        section_start = next(i for i, line in enumerate(lines) if line == "# Apple Services & App Store")
        section_end = next(
            i for i in range(section_start + 1, len(lines)) if lines[i].startswith("# Точечный PROXY")
        )
    except StopIteration as exc:
        raise RuntimeError("не найден раздел Apple Services & App Store") from exc

    missing = [rule for rule in required if rule not in lines[section_start:section_end]]
    if missing:
        insert_at = section_end
        while insert_at > section_start and lines[insert_at - 1] == "":
            insert_at -= 1
        for rule in missing:
            lines.insert(insert_at, rule)
            insert_at += 1

    first_required = next(i for i, line in enumerate(lines) if line == required[0])
    if first_required > section_start and lines[first_required - 1] == "":
        lines.pop(first_required - 1)

    section_end = next(
        i for i in range(section_start + 1, len(lines)) if lines[i].startswith("# Точечный PROXY")
    )
    if section_end > section_start and lines[section_end - 1] != "":
        lines.insert(section_end, "")


def build() -> str:
    if not CONFIG_PATH.is_file():
        raise RuntimeError(f"не найден конфиг-шаблон: {CONFIG_PATH}")

    lines = CONFIG_PATH.read_text(encoding="utf-8").splitlines()
    update_general(lines)
    ensure_apple_watch_rules(lines)
    ensure_apple_rules(lines)

    for source in SOURCES:
        text, digest = fetch_source(str(source["url"]))
        replace_source_block(lines, source, embedded_source_block(source, text, digest))

    return "\n".join(lines).rstrip() + "\n"


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check",
        action="store_true",
        help="собрать ожидаемый snapshot и проверить, что файл уже актуален",
    )
    args = parser.parse_args()

    try:
        expected = build()
    except (OSError, RuntimeError, UnicodeError) as exc:
        print(f"ERROR: {exc}", file=sys.stderr)
        return 1

    current = CONFIG_PATH.read_text(encoding="utf-8")
    if args.check:
        if current != expected:
            print("ERROR: url-set-main.conf не совпадает с актуальным failsafe snapshot", file=sys.stderr)
            return 1
        print("OK: url-set-main.conf соответствует актуальным снапшотам")
        return 0

    CONFIG_PATH.write_text(expected, encoding="utf-8")
    print(f"OK: записан {CONFIG_PATH} ({len(expected.encode('utf-8'))} bytes)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
