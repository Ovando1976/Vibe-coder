from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path

from .commands import PORTED_COMMANDS
from .port_manifest import build_port_manifest
from .tools import PORTED_TOOLS


@dataclass(frozen=True)
class ReadinessCheck:
    name: str
    passed: bool
    detail: str
    weight: int = 1


@dataclass(frozen=True)
class ReadinessReport:
    checks: tuple[ReadinessCheck, ...]

    @property
    def score(self) -> int:
        total_weight = sum(check.weight for check in self.checks)
        earned_weight = sum(check.weight for check in self.checks if check.passed)
        return int((earned_weight / total_weight) * 100) if total_weight else 0

    def to_markdown(self) -> str:
        passed = sum(1 for check in self.checks if check.passed)
        lines = [
            '# Awesome Assistant Readiness Report',
            '',
            f'Score: **{self.score}/100**',
            f'Checks passed: **{passed}/{len(self.checks)}**',
            '',
            '## Checks',
        ]
        for check in self.checks:
            marker = '✅' if check.passed else '⚠️'
            lines.append(f'- {marker} **{check.name}** — {check.detail}')
        lines.extend(
            [
                '',
                '## Next Actions',
                '- Harden startup reliability (ready handshake + trust gate auto-resolution).',
                '- Add typed lane/session events and failure taxonomy enforcement.',
                '- Enforce green-level contracts and publish benchmark outcomes per run.',
            ]
        )
        return '\n'.join(lines)

    def to_json(self) -> str:
        rows = [
            {
                'name': check.name,
                'passed': check.passed,
                'detail': check.detail,
                'weight': check.weight,
            }
            for check in self.checks
        ]
        passed = sum(1 for check in self.checks if check.passed)
        payload = {
            'score': self.score,
            'passed_checks': passed,
            'total_checks': len(self.checks),
            'checks': rows,
        }
        return json.dumps(payload, indent=2)


def build_readiness_report(repo_root: Path | None = None) -> ReadinessReport:
    root = repo_root or Path(__file__).resolve().parents[1]
    manifest = build_port_manifest()
    command_count = len(PORTED_COMMANDS)
    tool_count = len(PORTED_TOOLS)
    rust_runtime = root / 'rust' / 'crates' / 'runtime' / 'src'
    rust_tools = root / 'rust' / 'crates' / 'tools' / 'src' / 'lib.rs'
    mock_harness = root / 'rust' / 'crates' / 'rusty-claude-cli' / 'tests' / 'mock_parity_harness.rs'
    parity_doc = root / 'PARITY.md'
    roadmap_doc = root / 'ROADMAP.md'
    has_task_commands = any('task' in module.name.lower() for module in PORTED_COMMANDS)
    has_mcp_tools = any('mcp' in module.name.lower() for module in PORTED_TOOLS)
    has_lsp_tools = any('lsp' in module.name.lower() for module in PORTED_TOOLS)

    checks = (
        ReadinessCheck(
            name='Python workspace footprint',
            passed=manifest.total_python_files >= 20,
            detail=f'{manifest.total_python_files} Python files mirrored in src/',
            weight=1,
        ),
        ReadinessCheck(
            name='Command surface parity baseline',
            passed=command_count >= 150,
            detail=f'{command_count} mirrored command entries',
            weight=2,
        ),
        ReadinessCheck(
            name='Tool surface parity baseline',
            passed=tool_count >= 100,
            detail=f'{tool_count} mirrored tool entries',
            weight=2,
        ),
        ReadinessCheck(
            name='Runtime infrastructure present',
            passed=rust_runtime.exists(),
            detail=f'Rust runtime path: {rust_runtime}',
            weight=1,
        ),
        ReadinessCheck(
            name='Roadmap + parity docs present',
            passed=roadmap_doc.exists() and parity_doc.exists(),
            detail='ROADMAP.md and PARITY.md detected in repository root',
            weight=1,
        ),
        ReadinessCheck(
            name='Autonomy-oriented command/tool surface',
            passed=has_task_commands and has_mcp_tools and has_lsp_tools,
            detail='Task commands + MCP/LSP tool entries detected in mirrored surfaces',
            weight=2,
        ),
        ReadinessCheck(
            name='Mock parity harness wired',
            passed=mock_harness.exists() and rust_tools.exists(),
            detail='Rust mock parity harness + tools dispatch source detected',
            weight=1,
        ),
    )
    return ReadinessReport(checks=checks)
