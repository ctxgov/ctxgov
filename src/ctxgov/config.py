from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

try:
    import tomllib
except ModuleNotFoundError:  # pragma: no cover - exercised on Python < 3.11
    tomllib = None


@dataclass(frozen=True)
class VaultSettings:
    project: str
    root: str


@dataclass(frozen=True)
class StorageSettings:
    objects_dir: str
    indexes_dir: str
    reviews_dir: str
    exports_dir: str
    sqlite_path: str


@dataclass(frozen=True)
class PolicySettings:
    default_policy_fixture: str
    backup_receipt_path: str
    require_human_review: bool
    require_backup_for_durable_writes: bool


@dataclass(frozen=True)
class AdapterSettings:
    mode: str
    allow_remote: bool


@dataclass(frozen=True)
class CtxVaultConfig:
    vault: VaultSettings
    storage: StorageSettings
    policy: PolicySettings
    adapters: AdapterSettings


def _require_table(payload: dict, key: str) -> dict:
    value = payload.get(key)
    if not isinstance(value, dict):
        raise ValueError(f"missing or invalid [{key}] table")
    return value


def load_config(path: Path) -> CtxVaultConfig:
    payload = _loads_toml(path.read_text(encoding="utf-8"))

    vault = _require_table(payload, "vault")
    storage = _require_table(payload, "storage")
    policy = _require_table(payload, "policy")
    adapters = _require_table(payload, "adapters")

    return CtxVaultConfig(
        vault=VaultSettings(
            project=str(vault["project"]),
            root=str(vault["root"]),
        ),
        storage=StorageSettings(
            objects_dir=str(storage["objects_dir"]),
            indexes_dir=str(storage["indexes_dir"]),
            reviews_dir=str(storage["reviews_dir"]),
            exports_dir=str(storage["exports_dir"]),
            sqlite_path=str(storage["sqlite_path"]),
        ),
        policy=PolicySettings(
            default_policy_fixture=str(policy["default_policy_fixture"]),
            backup_receipt_path=str(policy["backup_receipt_path"]),
            require_human_review=bool(policy["require_human_review"]),
            require_backup_for_durable_writes=bool(policy["require_backup_for_durable_writes"]),
        ),
        adapters=AdapterSettings(
            mode=str(adapters["mode"]),
            allow_remote=bool(adapters["allow_remote"]),
        ),
    )


def _loads_toml(text: str) -> dict:
    if tomllib is not None:
        return tomllib.loads(text)
    return _loads_simple_toml(text)


def _loads_simple_toml(text: str) -> dict:
    payload: dict[str, dict[str, object]] = {}
    current_table: dict[str, object] | None = None
    for line_number, raw_line in enumerate(text.splitlines(), start=1):
        line = raw_line.split("#", 1)[0].strip()
        if not line:
            continue
        if line.startswith("[") and line.endswith("]"):
            table_name = line[1:-1].strip()
            if not table_name:
                raise ValueError(f"invalid TOML table header on line {line_number}")
            current_table = payload.setdefault(table_name, {})
            continue
        if current_table is None or "=" not in line:
            raise ValueError(f"unsupported TOML syntax on line {line_number}")
        key, raw_value = [part.strip() for part in line.split("=", 1)]
        if not key:
            raise ValueError(f"invalid TOML key on line {line_number}")
        current_table[key] = _parse_simple_toml_value(raw_value, line_number=line_number)
    return payload


def _parse_simple_toml_value(raw_value: str, *, line_number: int) -> object:
    if raw_value in {"true", "false"}:
        return raw_value == "true"
    if raw_value.startswith('"') and raw_value.endswith('"'):
        return raw_value[1:-1]
    raise ValueError(f"unsupported TOML value on line {line_number}")
