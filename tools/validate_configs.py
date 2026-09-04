#!/usr/bin/env python3
"""Static validation for the Shadowrocket configurations in this repository."""

from __future__ import annotations

import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
CONFIGS = {
    "main": ROOT / "url-set-main.conf",
    "ios": ROOT / "url-set-ios.conf",
    "macos": ROOT / "url-set-macos.conf",
}
BUILTIN_POLICIES = {"DIRECT", "PROXY", "REJECT", "PASS", "DROP"}
REQUIRED_EXTERNAL_SNAPSHOTS = 8
SECRET_PATTERN = re.compile(
    r"-----BEGIN [^-]*PRIVATE KEY-----|\b(?:vless|vmess|trojan|ss)://|"
    r"\b(?:password|passwd|secret|access[_-]?token|api[_-]?key)\s*=",
    re.IGNORECASE,
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
GITHUB_DIRECT_DOMAINS = (
    "github.com",
    "githubusercontent.com",
    "github.io",
    "githubassets.com",
    "githubcopilot.com",
    "github.dev",
    "ghcr.io",
)
# Historical S01 requirements, also reused by the independent main service guards.
IOS_YOUTUBE_CRITICAL_RULES = (
    "DOMAIN-SUFFIX,youtube.com,📺 YouTube",
    "DOMAIN-SUFFIX,ytimg.com,📺 YouTube",
    "DOMAIN-SUFFIX,googlevideo.com,📺 YouTube",
    "DOMAIN-SUFFIX,googleusercontent.com,📺 YouTube",
    "DOMAIN,youtubei.googleapis.com,📺 YouTube",
    "IP-CIDR6,2620:120:e000::/40,📺 YouTube,no-resolve",
)
IOS_YOUTUBE_QUIC_RULES = tuple(
    f"AND,((PROTOCOL,UDP),(DST-PORT,443),(DOMAIN-SUFFIX,{domain})),REJECT-NO-DROP"
    for domain in (
        "youtube.com",
        "youtu.be",
        "youtube-nocookie.com",
        "youtubeeducation.com",
        "youtubegaming.com",
        "youtubekids.com",
        "yt.be",
        "ytimg.com",
        "googlevideo.com",
        "googleusercontent.com",
        "ggpht.com",
        "gvt1.com",
        "gvt2.com",
        "video.google.com",
        "youtube.googleapis.com",
        "youtubei.googleapis.com",
        "youtubeembeddedplayer.googleapis.com",
    )
)
IOS_INSTAGRAM_CRITICAL_RULES = (
    "DOMAIN-SUFFIX,instagram.com,🗺️ Выбор сервера",
    "DOMAIN-SUFFIX,cdninstagram.com,🗺️ Выбор сервера",
    "DOMAIN-SUFFIX,facebook.com,🗺️ Выбор сервера",
    "DOMAIN-SUFFIX,fbcdn.net,🗺️ Выбор сервера",
    "IP-ASN,32934,🗺️ Выбор сервера,no-resolve",
    "IP-ASN,63293,🗺️ Выбор сервера,no-resolve",
    "IP-CIDR6,2a03:2880::/32,🗺️ Выбор сервера,no-resolve",
)
IOS_IAPPS_DIRECT_RULES = (
    "DOMAIN-SUFFIX,rejail.ru,DIRECT",
)
IOS_FEATHER_FINLAND_RULES = tuple(
    f"DOMAIN-SUFFIX,{domain},🇫🇮 Финляндия (авто)"
    for domain in (
        "getutm.app",
        "fastsign.dev",
        "apptesters.org",
        "hottubapp.io",
        "stikdebug.xyz",
    )
)
MAIN_PLATIPOMIRU_RULE = "DOMAIN-SUFFIX,platipomiru.com,🇫🇮 Финляндия"


def fail(errors: list[str], message: str) -> None:
    errors.append(message)


def read_config(path: Path, errors: list[str]) -> list[str]:
    if not path.is_file():
        fail(errors, f"не найден файл: {path}")
        return []
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except UnicodeError as exc:
        fail(errors, f"не удалось прочитать {path}: {exc}")
        return []


def section_lines(lines: list[str], section: str) -> list[str]:
    current = None
    result: list[str] = []
    for line in lines:
        stripped = line.strip()
        if stripped.startswith("[") and stripped.endswith("]"):
            current = stripped
        elif current == section:
            result.append(line)
    return result


def meaningful(lines: list[str]) -> list[str]:
    return [line.strip() for line in lines if line.strip() and not line.lstrip().startswith("#")]


def parse_groups(lines: list[str], name: str, errors: list[str]) -> set[str]:
    groups: list[str] = []
    for line in meaningful(section_lines(lines, "[Proxy Group]")):
        if "=" not in line:
            fail(errors, f"{name}: некорректная строка Proxy Group: {line}")
            continue
        group = line.split("=", 1)[0].strip()
        if not group:
            fail(errors, f"{name}: пустое имя Proxy Group: {line}")
        groups.append(group)

    duplicates = sorted({group for group in groups if groups.count(group) > 1})
    for group in duplicates:
        fail(errors, f"{name}: дублируется Proxy Group: {group}")

    case_duplicates = sorted(
        {
            group.lower()
            for group in groups
            if sum(other.lower() == group.lower() for other in groups) > 1
        }
    )
    for group in case_duplicates:
        fail(errors, f"{name}: Proxy Group отличается только регистром: {group}")
    return set(groups)


def parse_rules(lines: list[str], name: str, errors: list[str]) -> list[tuple[str, list[str], str]]:
    parsed: list[tuple[str, list[str], str]] = []
    for raw in section_lines(lines, "[Rule]"):
        line = raw.strip()
        if not line or line.startswith("#"):
            continue
        fields = [field.strip() for field in line.split(",")]
        if len(fields) < 2:
            fail(errors, f"{name}: некорректное правило: {line}")
            continue
        if fields[0] != "FINAL" and len(fields) < 3:
            fail(errors, f"{name}: у правила отсутствует policy: {line}")
            continue
        policy = fields[1] if fields[0] == "FINAL" else fields[2]
        parsed.append((line, fields, policy))
    return parsed


def validate_structure(name: str, lines: list[str], errors: list[str]) -> tuple[set[str], list[tuple[str, list[str], str]]]:
    for required in ("[General]", "[Rule]"):
        if required not in {line.strip() for line in lines}:
            fail(errors, f"{name}: отсутствует секция {required}")
    groups = parse_groups(lines, name, errors) if name != "main" else set()
    rules = parse_rules(lines, name, errors)

    if name != "main":
        for line, fields, policy in rules:
            if fields[0] == "RULE-SET" and fields[1].startswith("https://") and policy not in BUILTIN_POLICIES:
                if policy not in groups:
                    fail(errors, f"{name}: policy правила не совпадает с Proxy Group: {policy} ({line})")
    return groups, rules


def validate_general(name: str, lines: list[str], errors: list[str]) -> None:
    general = "\n".join(section_lines(lines, "[General]"))
    for required in (
        "dns-direct-system = true",
        "17.0.0.0/8",
        "apple-cloudkit.com",
        "apple-livephotoskit.com",
        "apple-dns.net",
    ):
        if required not in general:
            fail(errors, f"{name}: в [General] отсутствует обязательная настройка: {required}")


def validate_apple_watch_rules(name: str, lines: list[str], errors: list[str]) -> None:
    rule_start = next((index for index, line in enumerate(lines) if line.strip() == "[Rule]"), None)
    if rule_start is None:
        return
    rule_end = next(
        (index for index in range(rule_start + 1, len(lines)) if lines[index].strip().startswith("[")),
        len(lines),
    )
    rule_lines = [line.strip() for line in lines[rule_start + 1 : rule_end]]
    for required in APPLE_WATCH_DIRECT_RULES:
        count = rule_lines.count(required)
        if count != 1:
            fail(errors, f"{name}: Apple/watchOS rule должна встречаться ровно один раз: {required} (найдено {count})")

    first_external = next(
        (index for index in range(rule_start + 1, rule_end) if lines[index].strip().startswith("RULE-SET,https://")),
        None,
    )
    apple_positions = [
        index for index in range(rule_start + 1, rule_end) if lines[index].strip() in APPLE_WATCH_DIRECT_RULES
    ]
    if first_external is not None and len(apple_positions) == len(APPLE_WATCH_DIRECT_RULES):
        last_apple = max(apple_positions)
        if last_apple > first_external:
            fail(errors, f"{name}: Apple/watchOS rules должны находиться до внешних RULE-SET")


def validate_sources(name: str, rules: list[tuple[str, list[str], str]], errors: list[str]) -> None:
    for line, fields, _policy in rules:
        if fields[0] != "RULE-SET":
            continue
        source = fields[1]
        if not source.startswith("https://"):
            fail(errors, f"{name}: RULE-SET должен использовать HTTPS: {line}")
        local_match = re.search(
            r"raw\.githubusercontent\.com/squazaryu/sr-config/main/(lists/[^?#]+)$",
            source,
        )
        if local_match and not (ROOT / local_match.group(1)).is_file():
            fail(errors, f"{name}: локальный список отсутствует: {local_match.group(1)}")


def normalized_rule_key(line: str) -> str:
    fields = [field.strip() for field in line.split(",")]
    return ",".join(fields[:2])


def with_rule_policy(line: str, policy: str) -> str:
    fields = [field.strip() for field in line.split(",")]
    policy_index = 1 if fields[0] == "FINAL" else 2
    fields[policy_index] = policy
    return ",".join(fields)


def validate_local_lists(main_rules: list[tuple[str, list[str], str]], errors: list[str]) -> None:
    main_keys = {normalized_rule_key(line) for line, _fields, _policy in main_rules}
    for path in sorted((ROOT / "lists").glob("*.list")):
        seen: set[str] = set()
        for raw in path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#"):
                continue
            key = normalized_rule_key(line)
            if key in seen:
                fail(errors, f"lists/{path.name}: дубликат правила: {line}")
            seen.add(key)
            if key not in main_keys:
                fail(errors, f"url-set-main.conf: failsafe не содержит правило из lists/{path.name}: {line}")


def validate_failsafe(lines: list[str], rules: list[tuple[str, list[str], str]], errors: list[str]) -> None:
    if any(fields[0] == "RULE-SET" for _line, fields, _policy in rules):
        fail(errors, "main: самодостаточный failsafe не должен содержать RULE-SET")

    snapshot_count = sum(line.startswith("# BEGIN FAILSAFE SOURCE: ") for line in lines)
    if snapshot_count != REQUIRED_EXTERNAL_SNAPSHOTS:
        fail(errors, f"main: ожидалось {REQUIRED_EXTERNAL_SNAPSHOTS} embedded source snapshots, найдено {snapshot_count}")

    for index, line in enumerate(lines):
        if line.startswith("# BEGIN FAILSAFE SOURCE: "):
            if (
                index + 2 >= len(lines)
                or not lines[index + 1].startswith("# SHA256: ")
                or not lines[index + 2].startswith("# RULES: ")
            ):
                fail(errors, f"main: повреждён заголовок snapshot около строки {index + 1}")


def validate_special_cases(lines_by_name: dict[str, list[str]], errors: list[str]) -> None:
    macos = "\n".join(lines_by_name["macos"])
    if "🗺️ Выбор сервера = select,YOUR-DUREV.COM" not in macos:
        fail(errors, "macos: узел YOUR-DUREV.COM должен оставаться в ручной группе")
    if "🎧 Spotify = select, DIRECT" not in macos:
        fail(errors, "macos: Spotify должен оставаться DIRECT")

    for name, lines in lines_by_name.items():
        for line_number, line in enumerate(lines, start=1):
            if SECRET_PATTERN.search(line):
                fail(errors, f"{name}: возможный секрет в строке {line_number}")


def validate_ios_service_routes(lines_by_name: dict[str, list[str]], errors: list[str]) -> None:
    # Main iOS promotes the accepted N01 settings; main remains the expanded fallback.
    main_update = "update-url = https://raw.githubusercontent.com/squazaryu/sr-config/main/url-set-main.conf"
    ios_update = "update-url = https://raw.githubusercontent.com/squazaryu/sr-config/main/url-set-ios.conf"
    reference_update = "update-url = https://raw.githubusercontent.com/squazaryu/sr-config/main/url-set-ios-names-test.conf"
    reference = read_config(ROOT / "url-set-ios-names-test.conf", errors)
    fallback = lines_by_name["main"]
    ios_lines = lines_by_name["ios"]
    if fallback.count(main_update) != 1:
        fail(errors, "main: fallback должен содержать ровно один main update-url")
    if reference.count(reference_update) != 1:
        fail(errors, "ios-reference: эталон N01 должен содержать ровно один собственный update-url")
    if ios_lines.count(ios_update) != 1:
        fail(errors, "ios: основной профиль должен содержать ровно один iOS update-url")
    expected = [ios_update if line == reference_update else line for line in meaningful(reference)]
    if meaningful(ios_lines) != expected:
        fail(errors, "ios: активные настройки должны совпадать с N01, кроме собственного update-url")

    # Keep independent critical-service guards on the self-contained fallback.
    main_lines = [line.strip() for line in fallback]
    github_main = [f"DOMAIN-SUFFIX,{domain},DIRECT" for domain in GITHUB_DIRECT_DOMAINS]
    for rule in github_main:
        if main_lines.count(rule) != 1:
            fail(errors, f"main: GitHub DIRECT rule должно встречаться ровно один раз: {rule}")
    for ios_rule in IOS_IAPPS_DIRECT_RULES:
        if ios_rule not in main_lines:
            fail(errors, f"main: failsafe не содержит iApps DIRECT rule: {ios_rule}")
    for ios_rule in IOS_FEATHER_FINLAND_RULES:
        main_rule = with_rule_policy(ios_rule, "🇫🇮 Финляндия")
        if main_rule not in main_lines:
            fail(errors, f"main: failsafe не содержит Feather Finland rule: {main_rule}")
    if main_lines.count(MAIN_PLATIPOMIRU_RULE) != 1:
        fail(
            errors,
            "main: failsafe должен содержать ровно одно правило Telegram Mini App: "
            f"{MAIN_PLATIPOMIRU_RULE}",
        )
    for ios_rule in IOS_YOUTUBE_CRITICAL_RULES:
        main_rule = ios_rule.replace("📺 YouTube", "🇫🇮 Финляндия")
        if main_rule not in main_lines:
            fail(errors, f"main: failsafe не содержит обязательное service rule: {main_rule}")
    for ios_rule in IOS_INSTAGRAM_CRITICAL_RULES:
        main_rule = with_rule_policy(ios_rule, "🇫🇮 Финляндия")
        if main_rule not in main_lines:
            fail(errors, f"main: failsafe не содержит обязательное service rule: {main_rule}")


def main() -> int:
    errors: list[str] = []
    lines_by_name = {name: read_config(path, errors) for name, path in CONFIGS.items()}
    rules_by_name: dict[str, list[tuple[str, list[str], str]]] = {}
    for name, lines in lines_by_name.items():
        _groups, rules = validate_structure(name, lines, errors)
        rules_by_name[name] = rules
        validate_general(name, lines, errors)
        validate_apple_watch_rules(name, lines, errors)
        validate_sources(name, rules, errors)

    if lines_by_name["main"]:
        validate_local_lists(rules_by_name["main"], errors)
        validate_failsafe(lines_by_name["main"], rules_by_name["main"], errors)
    validate_special_cases(lines_by_name, errors)
    validate_ios_service_routes(lines_by_name, errors)

    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        print(f"FAILED: {len(errors)} validation error(s)", file=sys.stderr)
        return 1

    print("OK: Shadowrocket configs passed structural, failsafe, list and secret checks")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
