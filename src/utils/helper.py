from __future__ import annotations

import os
import sys
import warnings
import configparser
from dataclasses import dataclass
from pathlib import Path
from typing import Any


PROJECT_ROOT = Path(__file__).resolve().parents[2]
SRC_DIR = PROJECT_ROOT / "src"
DATA_DIR = SRC_DIR / "data"
DEFAULT_DICOM_DIR = DATA_DIR / "LIDC-IDRI"
OUTPUT_DIR = DATA_DIR / "output"
ENV_FILE = PROJECT_ROOT / ".env"


@dataclass(frozen=True)
class PylidcSettings:
    """Paths used by the example pylidc workflow."""

    dicom_path: Path
    output_dir: Path
    config_file: Path


def load_env_file(path: Path = ENV_FILE) -> dict[str, str]:
    """Load simple KEY=VALUE pairs without adding a python-dotenv dependency."""
    values: dict[str, str] = {}

    if not path.exists():
        return values

    for raw_line in path.read_text(encoding="utf-8").splitlines():
        line = raw_line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue

        key, value = line.split("=", 1)
        values[key.strip()] = value.strip().strip('"').strip("'")

    return values


def resolve_project_path(value: str | Path) -> Path:
    path = Path(value).expanduser()
    if not path.is_absolute():
        path = PROJECT_ROOT / path
    return path.resolve()


def get_settings() -> PylidcSettings:
    env_values = load_env_file()
    raw_dicom_path = os.environ.get("LIDC_DICOM_PATH") or env_values.get(
        "LIDC_DICOM_PATH",
        str(DEFAULT_DICOM_DIR),
    )
    raw_output_dir = os.environ.get("LIDC_OUTPUT_DIR") or env_values.get(
        "LIDC_OUTPUT_DIR",
        str(OUTPUT_DIR),
    )

    return PylidcSettings(
        dicom_path=resolve_project_path(raw_dicom_path),
        output_dir=resolve_project_path(raw_output_dir),
        config_file=Path.home() / get_pylidc_config_filename(),
    )


def get_pylidc_config_filename() -> str:
    return "pylidc.conf" if sys.platform.startswith("win") else ".pylidcrc"


def get_install_command() -> str:
    python_bin = "venv\\Scripts\\python.exe" if os.name == "nt" else "venv/bin/python"
    return f"{python_bin} -m pip install -r requirements.txt"


def get_run_command(*args: str) -> str:
    python_bin = "venv\\Scripts\\python.exe" if os.name == "nt" else "venv/bin/python"
    suffix = " ".join(args)
    return f"{python_bin} src/main.py {suffix}".rstrip()


def ensure_data_folders(settings: PylidcSettings | None = None) -> None:
    settings = settings or get_settings()
    settings.dicom_path.mkdir(parents=True, exist_ok=True)
    settings.output_dir.mkdir(parents=True, exist_ok=True)


def build_pylidc_config(settings: PylidcSettings | None = None) -> str:
    settings = settings or get_settings()
    return f"[dicom]\npath = {settings.dicom_path}\nwarn = True\n"


def write_project_config_example(settings: PylidcSettings | None = None) -> Path:
    settings = settings or get_settings()
    ensure_data_folders(settings)
    example_path = DATA_DIR / f"{get_pylidc_config_filename()}.example"
    example_path.write_text(build_pylidc_config(settings), encoding="utf-8")
    return example_path


def write_home_pylidc_config(settings: PylidcSettings | None = None) -> Path:
    settings = settings or get_settings()
    settings.config_file.write_text(build_pylidc_config(settings), encoding="utf-8")
    return settings.config_file


def patch_pylidc_runtime_compatibility() -> None:
    if not hasattr(configparser, "SafeConfigParser"):
        configparser.SafeConfigParser = configparser.ConfigParser  # type: ignore[attr-defined]


def require_pylidc() -> Any:
    try:
        patch_pylidc_runtime_compatibility()
        with warnings.catch_warnings():
            warnings.filterwarnings(
                "ignore",
                message="pkg_resources is deprecated as an API.*",
                category=UserWarning,
            )
            import pylidc as pl
    except ModuleNotFoundError as exc:
        raise RuntimeError(
            "A biblioteca pylidc nao esta instalada neste ambiente. "
            f"Instale com: {get_install_command()}"
        ) from exc

    return pl


def list_scans(patient_id: str | None = None, limit: int = 5) -> list[Any]:
    pl = require_pylidc()
    query = pl.query(pl.Scan)

    if patient_id:
        query = query.filter(pl.Scan.patient_id == patient_id)

    return query.limit(limit).all()


def export_middle_slice(patient_id: str | None = None, slice_index: int | None = None) -> Path:
    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    settings = get_settings()
    ensure_data_folders(settings)
    patch_pylidc_runtime_compatibility()

    pl = require_pylidc()
    query = pl.query(pl.Scan)
    if patient_id:
        query = query.filter(pl.Scan.patient_id == patient_id)

    scan = query.first()
    if scan is None:
        raise RuntimeError("Nenhum scan foi encontrado no banco de metadados do pylidc.")

    volume = scan.to_volume()
    z_index = slice_index if slice_index is not None else volume.shape[2] // 2
    if z_index < 0 or z_index >= volume.shape[2]:
        raise ValueError(f"slice_index deve ficar entre 0 e {volume.shape[2] - 1}.")

    annotations = scan.cluster_annotations()
    output_path = settings.output_dir / f"{scan.patient_id}_slice_{z_index:03d}.png"

    fig, ax = plt.subplots(figsize=(6, 6))
    ax.imshow(volume[:, :, z_index], cmap="gray")
    ax.set_title(f"{scan.patient_id} | slice {z_index} | nodulos: {len(annotations)}")
    ax.axis("off")
    fig.tight_layout()
    fig.savefig(output_path, dpi=150)
    plt.close(fig)

    return output_path
