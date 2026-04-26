from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True)
class VaultLayout:
    repo_root: Path
    vault_root: Path
    objects_dir: Path
    indexes_dir: Path
    reviews_dir: Path
    exports_dir: Path
    sqlite_path: Path

    def as_dict(self) -> dict[str, str]:
        return {
            "repo_root": str(self.repo_root),
            "vault_root": str(self.vault_root),
            "objects_dir": str(self.objects_dir),
            "indexes_dir": str(self.indexes_dir),
            "reviews_dir": str(self.reviews_dir),
            "exports_dir": str(self.exports_dir),
            "sqlite_path": str(self.sqlite_path),
        }


def default_layout(
    repo_root: Path,
    vault_root_name: str = ".ctxvault",
    objects_dir_name: str = "objects",
    indexes_dir_name: str = "indexes",
    reviews_dir_name: str = "reviews",
    exports_dir_name: str = "exports",
    sqlite_relative_path: str = "indexes/ctxvault.sqlite3",
) -> VaultLayout:
    vault_root = repo_root / vault_root_name
    return VaultLayout(
        repo_root=repo_root,
        vault_root=vault_root,
        objects_dir=vault_root / objects_dir_name,
        indexes_dir=vault_root / indexes_dir_name,
        reviews_dir=vault_root / reviews_dir_name,
        exports_dir=vault_root / exports_dir_name,
        sqlite_path=vault_root / sqlite_relative_path,
    )
