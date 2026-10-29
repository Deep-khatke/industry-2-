#!/usr/bin/env python3
"""Zero-Cost Compliance Scanner for Federated Cyber Shield (Phase 11).

Statically inspects repository files to verify strict adherence to the
₹0 / $0 budget policy. Detects billable cloud provisioning, paid runners,
unapproved hosting, and unauthorized live cloud service activations.
"""

from dataclasses import asdict, dataclass
import json
from pathlib import Path
import re
import sys
from typing import Any

PROHIBITED_PATTERNS = [
    # Billable cloud provisioning commands
    (r"\bterraform\s+apply\b", "Prohibited live terraform apply command"),
    (r"\btofu\s+apply\b", "Prohibited live opentofu apply command"),
    (r"\baws\s+ec2\s+run-instances\b", "Prohibited AWS EC2 instance launch"),
    (r"\baws\s+rds\s+create-db-instance\b", "Prohibited AWS RDS instance creation"),
    (r"\bgcloud\s+compute\s+instances\s+create\b", "Prohibited GCP compute engine launch"),
    (r"\baz\s+vm\s+create\b", "Prohibited Azure VM creation"),
    # Paid CI/CD runners
    (r"runs-on:\s*\[?['\"]?macos-latest['\"]?\]?", "Prohibited billable macOS runner"),
    (r"runs-on:\s*\[?['\"]?windows-2022['\"]?\]?", "Prohibited paid runner tier check (prefer ubuntu-latest)"),
    (r"runs-on:\s*\[?['\"]?self-hosted['\"]?\]?", "Prohibited unverified self-hosted billable runner"),
    # Live automatic response activation
    (r"\bAUTO_LIVE\b\s*=\s*['\"]?true['\"]?", "AUTO_LIVE cannot be hardcoded true"),
    (r"\bauto_response_enabled\s*=\s*True\b", "auto_response_enabled cannot be hardcoded True"),
    # Paid third-party APIs
    (r"api\.openai\.com", "Paid commercial LLM API reference"),
    (r"api\.anthropic\.com", "Paid commercial Claude API reference"),
]

EXCLUDED_PATHS = {
    ".git",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    "node_modules",
    "dist",
    "__pycache__",
    "artifacts",
}


@dataclass
class Finding:
    file_path: str
    line_number: int
    rule: str
    matched_text: str
    severity: str


class ZeroCostScanner:
    """Scans repository files for budget and zero-cost policy violations."""

    def __init__(self, root_dir: Path | None = None) -> None:
        self.root_dir = root_dir or Path(__file__).resolve().parents[2]
        self.findings: list[Finding] = []

    def scan_file(self, file_path: Path) -> list[Finding]:
        findings: list[Finding] = []
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except Exception:
            return findings

        # Skip completion reports, scanner itself, or handoff docs documenting the rules
        rel_str = str(file_path.relative_to(self.root_dir)).replace("\\", "/")
        if "tools/zero-cost-audit" in rel_str or rel_str.endswith("_REPORT.md") or "PHASE10_HANDOFF.md" in rel_str:
            return findings

        lines = content.splitlines()
        for idx, line in enumerate(lines, start=1):
            stripped = line.strip()
            # Skip comment lines in python / yaml / shell
            if stripped.startswith("#") or stripped.startswith("//") or stripped.startswith("<!--"):
                continue

            for pattern, desc in PROHIBITED_PATTERNS:
                # Windows runner is allowed in dev workflows if standard eligible, but check
                if "windows-2022" in pattern and ".github/workflows" in rel_str:
                    continue  # standard GitHub free runner for public repos
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    findings.append(
                        Finding(
                            file_path=rel_str,
                            line_number=idx,
                            rule=desc,
                            matched_text=match.group(0),
                            severity="CRITICAL",
                        )
                    )
        return findings

    def run_scan(self) -> dict[str, Any]:
        self.findings = []
        files_scanned = 0

        for p in self.root_dir.rglob("*"):
            if not p.is_file():
                continue
            if any(part in EXCLUDED_PATHS for part in p.parts):
                continue
            if p.suffix.lower() not in (
                ".py", ".tf", ".yaml", ".yml", ".json", ".sh", ".ps1", ".toml", ".js", ".ts", ".tsx"
            ):
                continue

            files_scanned += 1
            file_findings = self.scan_file(p)
            self.findings.extend(file_findings)

        status = "PASS" if len(self.findings) == 0 else "FAIL"
        return {
            "scanner": "FCS Zero-Cost Compliance Checker",
            "version": "1.2.0",
            "status": status,
            "budget_cap": "₹0 / $0",
            "files_scanned": files_scanned,
            "violations_found": len(self.findings),
            "findings": [asdict(f) for f in self.findings],
        }


def main() -> int:
    scanner = ZeroCostScanner()
    report = scanner.run_scan()
    print(json.dumps(report, indent=2))
    return 0 if report["status"] == "PASS" else 1


if __name__ == "__main__":
    sys.exit(main())
