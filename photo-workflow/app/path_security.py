from __future__

import os
from pathlib import Path


class PathSecurityError(ValueError):
    """Raised when a workflow path violates an allowed-root boundary."""


def canonical(path: str | Path) -> Path:
    return Path(path).expanduser().resolve(strict=False)


def _is_within(root: Path, target: Path) -> bool:
    try:
        target.relative_to(root)
        return True
    except ValueError:
        return False


def _has_symlink_component(path: Path, stop: Path) -> bool:
    current = path
    while current != stop and current != current.parent:
        if current.is_symlink():
            return True
        current = current.parent
    return False


def ensure_within(root: str | Path, target: str | Path, *, allow_missing: bool = True,
                  reject_symlinks: bool = True, require_same_device: bool = False) -> Path:
    root_path = canonical(root)
    target_path = canonical(target)
    if not _is_within(root_path, target_path):
        raise PathSecurityError(f"Path escapes allowed root: {target}")
    if reject_symlinks and _has_symlink_component(Path(target), Path(root)):
        raise PathSecurityError(f"Symlink component is not allowed: {target}")
    if not allow_missing and not target_path.exists():
        raise PathSecurityError(f"Path does not exist: {target}")
    if require_same_device and root_path.exists() and target_path.exists():
        if os.stat(root_path).st_dev != os.stat(target_path).st_dev:
            raise PathSecurityError(f"Mount/device differs from allowed root: {target}")
    return target_path


def validate_publish_target(config: dict, target: str | Path) -> Path:
    paths = config.get("paths", {})
    root = paths.get("publish_root")
    if not root:
        raise PathSecurityError("paths.publish_root is required for publication")
    return ensure_within(root, target, reject_symlinks=True, require_same_device=True)
