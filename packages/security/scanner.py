"""Zero-cost static secret and credential detection scanner."""

import re
from dataclasses import dataclass
from pathlib import Path

PATTERNS: dict[str, re.Pattern[str]] = {
    "aws_access_key": re.compile(r"\b(AKIA[0-9A-Z]{16})\b"),
    "aws_secret_key": re.compile(r"(?i)aws_secret_access_key\s*=\s*['\"][A-Za-z0-9/\+=]{40}['\"]"),
    "private_key": re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    "github_token": re.compile(r"\bgh[pous]_[0-9a-zA-Z]{36}\b"),
    "slack_token": re.compile(r"xox[baprs]-[0-9]{12}-[0-9]{12}-[a-zA-Z0-9]{24}"),
    "generic_secret": re.compile(r"(?i)(?:api_key|password|secret_token)\s*=\s*['\"][A-Za-z0-9_=\-\.]{16,}['\"]"),
}

IGNORED_DIRECTORIES = {
    ".git",
    ".venv",
    "venv",
    "__pycache__",
    ".pytest_cache",
    ".ruff_cache",
    ".mypy_cache",
    ".terraform",
    ".tofu",
    "node_modules",
}
IGNORED_FILES = {".env.example", ".terraform.lock.hcl"}


@dataclass
class SecretFinding:
    rule_name: str
    file_path: str
    line_number: int
    matched_text_masked: str


@dataclass
class SecretScanResult:
    scanned_files_count: int
    findings: list[SecretFinding]

    @property
    def passed(self) -> bool:
        return len(self.findings) == 0


class RepositorySecretScanner:
    """Scans workspace source code and documentation for committed secrets."""

    def __init__(self, root_dir: Path | str) -> None:
        self.root_dir = Path(root_dir)

    def scan_text(self, text: str, source_name: str = "inline") -> list[SecretFinding]:
        """Scan a text buffer for sensitive patterns."""
        findings: list[SecretFinding] = []
        for line_num, line in enumerate(text.splitlines(), start=1):
            for rule, pattern in PATTERNS.items():
                m = pattern.search(line)
                if m:
                    # Check for explicit example placeholder comments
                    if "example" in line.lower() or "placeholder" in line.lower() or "dummy" in line.lower():
                        continue
                    matched = m.group(0)
                    masked = matched[:4] + "*" * (len(matched) - 8) + matched[-4:] if len(matched) > 8 else "***"
                    findings.append(
                        SecretFinding(
                            rule_name=rule,
                            file_path=source_name,
                            line_number=line_num,
                            matched_text_masked=masked,
                        )
                    )
        return findings

    def scan_repository(self) -> SecretScanResult:
        """Scan all text files in the repository."""
        scanned_count = 0
        all_findings: list[SecretFinding] = []

        for p in self.root_dir.rglob("*"):
            if not p.is_file():
                continue
            if any(part in IGNORED_DIRECTORIES for part in p.parts):
                continue
            if p.name in IGNORED_FILES:
                continue
            if p.suffix.lower() in {".png", ".jpg", ".jpeg", ".pyc", ".db", ".sqlite", ".ico", ".bin", ".exe", ".zip", ".tar", ".gz"}:
                continue

            try:
                content = p.read_text(encoding="utf-8", errors="ignore")
                scanned_count += 1
                findings = self.scan_text(content, source_name=str(p.relative_to(self.root_dir)))
                all_findings.extend(findings)
            except Exception:
                continue

        return SecretScanResult(scanned_files_count=scanned_count, findings=all_findings)
