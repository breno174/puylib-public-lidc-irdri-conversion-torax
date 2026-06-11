from __future__ import annotations

import argparse

from utils import (
    build_pylidc_config,
    ensure_data_folders,
    export_middle_slice,
    get_settings,
    list_scans,
    write_home_pylidc_config,
    write_project_config_example,
)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Exemplo de uso do pylidc com dados LIDC-IDRI em src/data."
    )
    parser.add_argument(
        "--patient-id",
        help="Paciente LIDC-IDRI especifico. Exemplo: LIDC-IDRI-0078.",
    )
    parser.add_argument(
        "--slice-index",
        type=int,
        help="Indice do slice axial que sera exportado. Padrao: slice central.",
    )
    parser.add_argument(
        "--list-only",
        action="store_true",
        help="Lista scans encontrados sem tentar abrir os DICOMs.",
    )
    parser.add_argument(
        "--write-config",
        action="store_true",
        help="Cria o pylidc.conf no diretorio do usuario apontando para src/data/LIDC-IDRI.",
    )
    return parser.parse_args()


def main() -> None:
    args = parse_args()
    settings = get_settings()
    ensure_data_folders(settings)
    example_config = write_project_config_example(settings)

    print(f"Pasta dos DICOMs: {settings.dicom_path}")
    print(f"Pasta de saida: {settings.output_dir}")
    print(f"Exemplo de config gerado em: {example_config}")

    if args.write_config:
        config_file = write_home_pylidc_config(settings)
        print(f"Config do pylidc gravada em: {config_file}")
    elif not settings.config_file.exists():
        print("\nAntes de exportar imagens, crie a config do pylidc com:")
        print("venv\\Scripts\\python.exe src\\main.py --write-config")
        print("\nConteudo esperado:")
        print(build_pylidc_config(settings))

    try:
        scans = list_scans(patient_id=args.patient_id, limit=5)
    except RuntimeError as exc:
        print(f"\n{exc}")
        return

    if not scans:
        print("\nNenhum scan encontrado. Confira se o pylidc foi instalado corretamente.")
        return

    print("\nScans encontrados:")
    for scan in scans:
        print(
            f"- {scan.patient_id}: "
            f"{len(scan.annotations)} anotacoes, "
            f"espessura={scan.slice_thickness}, "
            f"pixel_spacing={scan.pixel_spacing}"
        )

    if args.list_only:
        return

    try:
        output_path = export_middle_slice(
            patient_id=args.patient_id,
            slice_index=args.slice_index,
        )
    except Exception as exc:
        print("\nNao foi possivel exportar a imagem agora.")
        print("Isso e esperado enquanto os DICOMs ainda nao estiverem em src/data/LIDC-IDRI.")
        print(f"Detalhe: {exc}")
        return

    print(f"\nImagem exportada em: {output_path}")


if __name__ == "__main__":
    main()
