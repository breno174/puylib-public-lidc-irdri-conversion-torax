from __future__ import annotations

import argparse

from utils import (
    build_pylidc_config,
    ensure_data_folders,
    export_consensus_annotation_images,
    export_first_annotation_images,
    export_middle_slice,
    get_run_command,
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
        help="Cria a config do pylidc no diretorio do usuario apontando para src/data/LIDC-IDRI.",
    )
    parser.add_argument(
        "--export-first-annotations",
        action="store_true",
        help="Exporta as 3 primeiras anotacoes usando filtro com in_ em scans finos.",
    )
    parser.add_argument(
        "--export-consensus-annotations",
        action="store_true",
        help="Exporta nodulos com pelo menos --min-annotations anotacoes no cluster.",
    )
    parser.add_argument(
        "--min-annotations",
        type=int,
        default=3,
        help="Minimo de anotacoes por cluster para manter o nodulo exportado. Use 4 para exigir mais de 3.",
    )
    parser.add_argument(
        "--image-format",
        choices=("png", "jpg", "jpeg"),
        default="png",
        help="Formato das imagens brutas exportadas.",
    )
    parser.add_argument(
        "--export-scope",
        choices=("slice", "crop"),
        default="slice",
        help="slice exporta a fatia DICOM inteira; crop exporta apenas o recorte do nodulo.",
    )
    parser.add_argument(
        "--color-mode",
        choices=("grayscale", "rgb"),
        default="grayscale",
        help="grayscale salva 1 canal; rgb duplica o canal cinza em 3 canais.",
    )
    parser.add_argument(
        "--window-center",
        type=float,
        default=-600.0,
        help="Centro da janela CT usada para converter para 8-bit. Padrao: lung window.",
    )
    parser.add_argument(
        "--window-width",
        type=float,
        default=1500.0,
        help="Largura da janela CT usada para converter para 8-bit. Padrao: lung window.",
    )
    parser.add_argument(
        "--no-window",
        action="store_true",
        help="Usa min-max da imagem em vez de janela CT fixa.",
    )
    parser.add_argument(
        "--max-slice-thickness",
        type=float,
        default=1.0,
        help="Filtro de scan: slice_thickness menor que este valor.",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="Quantidade de imagens para exportar. Use 0 para exportar tudo.",
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
        print(get_run_command("--write-config"))
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

    if args.export_consensus_annotations:
        window_center = None if args.no_window else args.window_center
        window_width = None if args.no_window else args.window_width

        try:
            rows = export_consensus_annotation_images(
                min_annotations=args.min_annotations,
                limit=args.limit,
                patient_id=args.patient_id,
                image_format=args.image_format,
                export_scope=args.export_scope,
                window_center=window_center,
                window_width=window_width,
                color_mode=args.color_mode,
            )
        except RuntimeError as exc:
            print("\nNao foi possivel exportar os clusters filtrados agora.")
            print("Confira se os DICOMs estao em src/data/LIDC-IDRI e se a config do pylidc foi criada.")
            print(f"Detalhe: {exc}")
            return
        except Exception as exc:
            print("\nNao foi possivel exportar os clusters filtrados por um erro inesperado.")
            print(f"Detalhe: {exc}")
            return

        print(f"\nClusters mantidos com pelo menos {args.min_annotations} anotacoes:")
        for row in rows:
            print(
                f"- {row['patient_id']} | cluster={row['cluster_index']} | "
                f"anotacoes={row['annotation_count']} | "
                f"malignancy={row['malignancy_values']} | "
                f"imagem={row['image_path']}"
            )
        print("\nImagens brutas salvas sem legenda/overlay.")
        return

    if args.export_first_annotations:
        try:
            rows = export_first_annotation_images(
                max_slice_thickness=args.max_slice_thickness,
                limit=args.limit,
            )
        except RuntimeError as exc:
            print("\nNao foi possivel exportar as anotacoes agora.")
            print("Confira se os DICOMs estao em src/data/LIDC-IDRI e se a config do pylidc foi criada.")
            print(f"Detalhe: {exc}")
            return
        except Exception as exc:
            print("\nNao foi possivel exportar as anotacoes por um erro inesperado.")
            print(f"Detalhe: {exc}")
            return

        print("\nPrimeiras anotacoes exportadas:")
        for row in rows:
            print(
                f"- ann {row['annotation_id']} | {row['patient_id']} | "
                f"malignancy={row['malignancy']} ({row['malignancy_label']}) | "
                f"imagem={row['image_path']}"
            )
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
    except RuntimeError as exc:
        print("\nNao foi possivel exportar a imagem agora.")
        print("Confira se os DICOMs estao em src/data/LIDC-IDRI e se a config do pylidc foi criada.")
        print(f"Detalhe: {exc}")
        return
    except Exception as exc:
        print("\nNao foi possivel exportar a imagem por um erro inesperado.")
        print(f"Detalhe: {exc}")
        return

    print(f"\nImagem exportada em: {output_path}")


if __name__ == "__main__":
    main()
