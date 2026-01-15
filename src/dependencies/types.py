from __future__ import annotations

from dataclasses import dataclass, field


@dataclass
class DependencyGraph:
    ecosystems: dict[str, set[str]] = field(default_factory=dict)
    direct: dict[str, set[str]] = field(default_factory=dict)
    transitive: dict[str, set[str]] = field(default_factory=dict)

    def add_direct(self, ecosystem: str, names: set[str]) -> None:
        if not names:
            return
        self.direct.setdefault(ecosystem, set()).update(names)
        self.ecosystems.setdefault(ecosystem, set()).update(names)

    def add_transitive(self, ecosystem: str, names: set[str]) -> None:
        if not names:
            return
        self.transitive.setdefault(ecosystem, set()).update(names)
        self.ecosystems.setdefault(ecosystem, set()).update(names)
