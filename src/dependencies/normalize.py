from __future__ import annotations


def normalize_package_name(name: str, ecosystem: str | None, normalize_names: bool = True) -> str:
    cleaned = name.strip()
    if not normalize_names:
        return cleaned
    lowered = cleaned.lower()
    ecosystem_name = (ecosystem or "").lower()
    if ecosystem_name in {"pip", "pypi"}:
        return lowered.replace("_", "-").replace(".", "-")
    if ecosystem_name == "npm":
        return lowered.replace("_", "-")
    return lowered
