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

    try:
        import numpy as np
    except ModuleNotFoundError:
        return

    if not hasattr(np, "int"):
        np.int = int  # type: ignore[attr-defined]
    if not hasattr(np, "float"):
        np.float = float  # type: ignore[attr-defined]


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


def normalize_ct_image(
    image: Any,
    window_center: float | None = -600.0,
    window_width: float | None = 1500.0,
) -> Any:
    import numpy as np

    image = image.astype(np.float32)

    if window_center is not None and window_width is not None:
        lower = window_center - window_width / 2.0
        upper = window_center + window_width / 2.0
        image = np.clip(image, lower, upper)
    else:
        lower = float(np.min(image))
        upper = float(np.max(image))

    if upper <= lower:
        return np.zeros(image.shape, dtype=np.uint8)

    image = (image - lower) / (upper - lower)
    return (image * 255.0).clip(0, 255).astype(np.uint8)


def save_raw_grayscale_image(
    image: Any,
    output_path: Path,
    window_center: float | None = -600.0,
    window_width: float | None = 1500.0,
    color_mode: str = "grayscale",
) -> None:
    from PIL import Image

    if color_mode not in {"grayscale", "rgb"}:
        raise ValueError("color_mode deve ser grayscale ou rgb.")

    output_path.parent.mkdir(parents=True, exist_ok=True)
    image_8bit = normalize_ct_image(
        image,
        window_center=window_center,
        window_width=window_width,
    )
    pil_image = Image.fromarray(image_8bit, mode="L")
    if color_mode == "rgb":
        pil_image = pil_image.convert("RGB")

    if output_path.suffix.lower() in {".jpg", ".jpeg"}:
        pil_image.save(output_path, quality=95)
    else:
        pil_image.save(output_path)


def export_first_annotation_images(
    max_slice_thickness: float = 1.0,
    limit: int = 3,
    pad: int = 10,
) -> list[dict[str, Any]]:
    import csv

    import matplotlib

    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    settings = get_settings()
    ensure_data_folders(settings)
    patch_pylidc_runtime_compatibility()

    pl = require_pylidc()

    scans = pl.query(pl.Scan).filter(pl.Scan.slice_thickness < max_slice_thickness)
    scan_ids = [scan.id for scan in scans]
    if not scan_ids:
        raise RuntimeError(f"Nenhum scan encontrado com slice_thickness < {max_slice_thickness}.")

    annotations = (
        pl.query(pl.Annotation)
        .filter(pl.Annotation.scan_id.in_(scan_ids))
        .order_by(pl.Annotation.id)
        .limit(limit)
        .all()
    )
    if not annotations:
        raise RuntimeError("Nenhuma anotacao encontrada para os scans filtrados.")

    export_dir = settings.output_dir / "first_annotations"
    export_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []
    volume_cache: dict[int, Any] = {}

    for index, ann in enumerate(annotations, start=1):
        scan = ann.scan
        if scan.id not in volume_cache:
            volume_cache[scan.id] = scan.to_volume(verbose=False)

        volume = volume_cache[scan.id]
        bbox = ann.bbox(pad=pad)
        crop = volume[bbox]
        z_index = crop.shape[2] // 2

        image_path = export_dir / (
            f"{index:02d}_ann_{ann.id}_scan_{scan.patient_id}_"
            f"malignancy_{ann.malignancy}.png"
        )

        fig, ax = plt.subplots(figsize=(5, 5))
        ax.imshow(crop[:, :, z_index], cmap="gray")
        ax.set_title(f"{scan.patient_id} | ann {ann.id} | {ann.Malignancy}")
        ax.axis("off")
        fig.tight_layout()
        fig.savefig(image_path, dpi=150)
        plt.close(fig)

        rows.append(
            {
                "index": index,
                "annotation_id": ann.id,
                "scan_id": scan.id,
                "patient_id": scan.patient_id,
                "slice_thickness": scan.slice_thickness,
                "malignancy": ann.malignancy,
                "malignancy_label": ann.Malignancy,
                "image_path": str(image_path),
            }
        )

    csv_path = export_dir / "first_annotations_malignancy.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    return rows


def export_consensus_annotation_images(
    min_annotations: int = 3,
    limit: int = 3,
    patient_id: str | None = None,
    pad: int = 10,
    image_format: str = "png",
    export_scope: str = "slice",
    window_center: float | None = -600.0,
    window_width: float | None = 1500.0,
    color_mode: str = "grayscale",
) -> list[dict[str, Any]]:
    import csv

    settings = get_settings()
    ensure_data_folders(settings)
    patch_pylidc_runtime_compatibility()

    if image_format.lower() not in {"png", "jpg", "jpeg"}:
        raise ValueError("image_format deve ser png, jpg ou jpeg.")
    if export_scope not in {"slice", "crop"}:
        raise ValueError("export_scope deve ser slice ou crop.")
    if color_mode not in {"grayscale", "rgb"}:
        raise ValueError("color_mode deve ser grayscale ou rgb.")

    extension = "jpg" if image_format.lower() == "jpeg" else image_format.lower()

    pl = require_pylidc()
    query = pl.query(pl.Scan).order_by(pl.Scan.id)
    if patient_id:
        query = query.filter(pl.Scan.patient_id == patient_id)

    export_dir = settings.output_dir / f"consensus_min_{min_annotations}"
    export_dir.mkdir(parents=True, exist_ok=True)

    rows: list[dict[str, Any]] = []

    for scan in query:
        clusters = scan.cluster_annotations(verbose=False)
        kept_clusters = [
            (cluster_index, cluster)
            for cluster_index, cluster in enumerate(clusters, start=1)
            if len(cluster) >= min_annotations
        ]

        if not kept_clusters:
            continue

        volume = scan.to_volume(verbose=False)

        for cluster_index, cluster in kept_clusters:
            representative = cluster[0]
            bbox = representative.bbox(pad=pad)
            z_slice = bbox[2]
            z_index = int((z_slice.start + z_slice.stop - 1) / 2)

            if export_scope == "crop":
                image = volume[bbox][:, :, volume[bbox].shape[2] // 2]
            else:
                image = volume[:, :, z_index]

            malignancy_values = [ann.malignancy for ann in cluster]
            malignancy_labels = [ann.Malignancy for ann in cluster]
            annotation_ids = [ann.id for ann in cluster]

            image_path = export_dir / (
                f"{len(rows) + 1:03d}_{scan.patient_id}_cluster_{cluster_index}_"
                f"anns_{len(cluster)}.{extension}"
            )

            save_raw_grayscale_image(
                image,
                image_path,
                window_center=window_center,
                window_width=window_width,
                color_mode=color_mode,
            )

            rows.append(
                {
                    "index": len(rows) + 1,
                    "patient_id": scan.patient_id,
                    "scan_id": scan.id,
                    "cluster_index": cluster_index,
                    "annotation_count": len(cluster),
                    "annotation_ids": ";".join(str(value) for value in annotation_ids),
                    "malignancy_values": ";".join(str(value) for value in malignancy_values),
                    "malignancy_labels": ";".join(malignancy_labels),
                    "representative_annotation_id": representative.id,
                    "slice_index": z_index,
                    "export_scope": export_scope,
                    "image_format": extension,
                    "window_center": window_center,
                    "window_width": window_width,
                    "color_mode": color_mode,
                    "image_path": str(image_path),
                }
            )

            if limit > 0 and len(rows) >= limit:
                break

        if limit > 0 and len(rows) >= limit:
            break

    if not rows:
        raise RuntimeError(
            f"Nenhum cluster encontrado com pelo menos {min_annotations} anotacoes."
        )

    csv_path = export_dir / "consensus_annotations.csv"
    with csv_path.open("w", newline="", encoding="utf-8") as csv_file:
        writer = csv.DictWriter(csv_file, fieldnames=list(rows[0].keys()))
        writer.writeheader()
        writer.writerows(rows)

    return rows
