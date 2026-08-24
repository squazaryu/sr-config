#!/usr/bin/env python3
"""Check every remote RULE-SET referenced by the iOS/macOS configs."""

from __future__ import annotations

from concurrent.futures import ThreadPoolExecutor, as_completed
from dataclasses import dataclass, field
import sys
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
CONFIG_PATHS = (ROOT / "url-set-ios.conf", ROOT / "url-set-macos.conf")
FETCH_TIMEOUT = 30
MAX_SOURCE_BYTES = 16 * 1024 * 1024
MAX_WORKERS = 8
USER_AGENT = "sr-config-remote-check/1.0"


@dataclass
class Source:
    url: str
    references: list[str] = field(default_factory=list)


@dataclass
class CheckResult:
    url: str
    ok: bool
    detail: str


def collect_sources() -> tuple[dict[str, Source], list[str]]:
    sources: dict[str, Source] = {}
    errors: list[str] = []

    for config_path in CONFIG_PATHS:
        if not config_path.is_file():
            errors.append(f"{config_path.name}: file not found")
            continue

        for line_number, raw_line in enumerate(
            config_path.read_text(encoding="utf-8").splitlines(), start=1
        ):
            line = raw_line.strip()
            if not line.startswith("RULE-SET,"):
                continue

            fields = [field.strip() for field in line.split(",")]
            if len(fields) < 3 or not fields[1]:
                errors.append(f"{config_path.name}:{line_number}: malformed RULE-SET")
                continue

            url = fields[1]
            reference = f"{config_path.name}:{line_number}"
            sources.setdefault(url, Source(url)).references.append(reference)
            if not url.startswith("https://"):
                errors.append(f"{reference}: RULE-SET must use HTTPS: {url}")

    return sources, errors


def check_source(source: Source) -> CheckResult:
    request = Request(source.url, headers={"User-Agent": USER_AGENT})
    try:
        with urlopen(request, timeout=FETCH_TIMEOUT) as response:
            status = getattr(response, "status", 200)
            content_type = response.headers.get_content_type()
            payload = response.read(MAX_SOURCE_BYTES + 1)
    except (HTTPError, URLError, TimeoutError, OSError) as exc:
        return CheckResult(source.url, False, f"request failed: {exc}")

    if not 200 <= status < 300:
        return CheckResult(source.url, False, f"unexpected HTTP status: {status}")
    if len(payload) > MAX_SOURCE_BYTES:
        return CheckResult(source.url, False, f"response exceeds {MAX_SOURCE_BYTES} bytes")
    if content_type == "text/html":
        return CheckResult(source.url, False, "response is HTML, not a rule list")

    try:
        text = payload.decode("utf-8-sig", errors="strict")
    except UnicodeDecodeError as exc:
        return CheckResult(source.url, False, f"response is not UTF-8: {exc}")

    probe = text.lstrip().lower()[:512]
    if "<html" in probe or "<!doctype" in probe:
        return CheckResult(source.url, False, "response contains an HTML error page")

    rule_count = 0
    malformed: list[str] = []
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.strip()
        if not line or line.startswith("#") or line.startswith("//"):
            continue
        if len(line.split(",")) < 2:
            malformed.append(f"line {line_number}: {line[:100]}")
            continue
        rule_count += 1

    if rule_count == 0:
        return CheckResult(source.url, False, "response contains no rules")
    if malformed:
        sample = "; ".join(malformed[:3])
        return CheckResult(source.url, False, f"malformed rule(s): {sample}")

    return CheckResult(source.url, True, f"HTTP {status}, {rule_count} rules, {len(payload)} bytes")


def main() -> int:
    sources, errors = collect_sources()
    if errors:
        for error in errors:
            print(f"ERROR: {error}", file=sys.stderr)
        return 1
    if not sources:
        print("ERROR: no RULE-SET sources found", file=sys.stderr)
        return 1

    print(f"Checking {len(sources)} unique RULE-SET source(s) from {len(CONFIG_PATHS)} configs")
    results: dict[str, CheckResult] = {}
    worker_count = min(MAX_WORKERS, len(sources))
    with ThreadPoolExecutor(max_workers=worker_count) as executor:
        futures = {executor.submit(check_source, source): url for url, source in sources.items()}
        for future in as_completed(futures):
            result = future.result()
            results[result.url] = result

    failures = 0
    for url in sorted(results):
        result = results[url]
        references = ", ".join(sources[url].references)
        prefix = "OK" if result.ok else "ERROR"
        output = sys.stdout if result.ok else sys.stderr
        print(f"{prefix}: {result.detail} [{references}] {url}", file=output)
        if not result.ok:
            failures += 1

    if failures:
        print(f"FAILED: {failures} remote RULE-SET source(s)", file=sys.stderr)
        return 1

    print(f"OK: all {len(results)} remote RULE-SET source(s) are available and valid")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
