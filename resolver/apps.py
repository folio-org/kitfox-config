"""B.8 + Gap #5 — descriptor-derived app data (injected input, FAR stand-in).

available  = required+optional NAMES from platform-descriptor.json (versions ignored).
deployed   = available − unioned excludes.
UI cascade = per excluded app, its uiModules names (for the pipeline's cascade, Epic F).
presence   = modules of a set of apps (Gap #5 gating of config.kb / config.worldcat).

App descriptors are matched by NAME, ignoring version (names-not-versions, §0)."""

from __future__ import annotations

import json
from dataclasses import dataclass
from pathlib import Path


@dataclass
class AppIndex:
    available: list[str]
    _modules: dict[str, list[str]]     # app name -> backend module names
    _ui_modules: dict[str, list[str]]  # app name -> UI module names

    @classmethod
    def load(cls, platform_descriptor: Path, app_descriptors_dir: Path) -> "AppIndex":
        desc = json.loads(Path(platform_descriptor).read_text())
        apps = desc.get("applications", {})
        names = [a["name"] for a in apps.get("required", [])] + [
            a["name"] for a in apps.get("optional", [])
        ]
        available = sorted(set(names))

        modules: dict[str, list[str]] = {}
        ui_modules: dict[str, list[str]] = {}
        ddir = Path(app_descriptors_dir)
        if ddir.exists():
            for f in sorted(ddir.glob("*.json")):
                doc = json.loads(f.read_text())
                app_name = doc.get("name")
                if not app_name:
                    continue
                modules[app_name] = sorted(m["name"] for m in doc.get("modules", []))
                ui_modules[app_name] = sorted(m["name"] for m in doc.get("uiModules", []))
        return cls(available=available, _modules=modules, _ui_modules=ui_modules)

    def deployed(self, exclude: list[str]) -> list[str]:
        excluded = set(exclude or [])
        return sorted(a for a in self.available if a not in excluded)

    def excluded_ui_modules(self, excluded_apps: list[str]) -> dict[str, list[str]]:
        return {app: self._ui_modules.get(app, []) for app in (excluded_apps or [])}

    def modules_of(self, apps: list[str]) -> set[str]:
        present: set[str] = set()
        for app in apps or []:
            present.update(self._modules.get(app, []))
        return present
