"""Bundle registry: workflows/activities grouped by name, each on its own task queue."""

from collections.abc import Callable
from dataclasses import dataclass


@dataclass(frozen=True)
class Bundle:
    name: str
    workflows: list[type]
    activities: list[Callable]
    task_queue: str = ""

    @property
    def effective_task_queue(self) -> str:
        return self.task_queue or self.name


REGISTRY: dict[str, Bundle] = {}


def register(bundle: Bundle) -> None:
    if bundle.name in REGISTRY:
        raise ValueError(f"Bundle {bundle.name!r} is already registered")
    REGISTRY[bundle.name] = bundle


def resolve(names: list[str] | None) -> list[Bundle]:
    if not names:
        return list(REGISTRY.values())
    unknown = [name for name in names if name not in REGISTRY]
    if unknown:
        valid = ", ".join(sorted(REGISTRY)) or "(none registered)"
        raise ValueError(f"Unknown bundle(s) {unknown}; valid bundles: {valid}")
    return [REGISTRY[name] for name in names]


__all__ = ["Bundle", "REGISTRY", "register", "resolve"]
