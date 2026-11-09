"""Entry point para CLI: python -m extract_info"""

from __future__ import annotations

import argparse
import logging
import sys

from extract_info.batch import list_pipelines, process_batch_pipeline
from extract_info.csv_writer import write_pipeline_csvs


def setup_logging(verbose: bool) -> None:
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        datefmt="%H:%M:%S",
    )


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Motor de extracción de metadatos desde PDFs a CSV"
    )
    parser.add_argument(
        "--input", "-i", required=True, help="Carpeta raíz que contiene subcarpetas con PDFs"
    )
    parser.add_argument(
        "--output", "-o", required=True, help="Carpeta donde se generarán los CSV"
    )
    parser.add_argument(
        "--pipeline",
        "-p",
        choices=list_pipelines(),
        default="retail",
        help="Pipeline de extracción a usar (default: retail)",
    )
    parser.add_argument(
        "--verbose", "-v", action="store_true", help="Modo verbose/debug"
    )
    parser.add_argument(
        "--workers", "-w", type=int, default=None, help="Número de procesos paralelos"
    )
    parser.add_argument(
        "--unified", "-u", action="store_true",
        help="Generar un único CSV unificado en lugar de un CSV por carpeta"
    )
    args = parser.parse_args()

    setup_logging(args.verbose)
    logger = logging.getLogger(__name__)

    logger.info("Input: %s", args.input)
    logger.info("Output: %s", args.output)
    logger.info("Pipeline: %s", args.pipeline)

    folder_results = process_batch_pipeline(
        args.input,
        pipeline=args.pipeline,
        max_workers=args.workers,
    )

    if not folder_results:
        logger.warning("No se procesaron documentos.")
        sys.exit(0)

    total_docs = sum(len(r.rows) for r in folder_results)
    logger.info("Total documentos procesados: %d", total_docs)

    csv_paths = write_pipeline_csvs(
        folder_results, args.output, unified=args.unified
    )
    logger.info("CSVs generados: %d", len(csv_paths))
    for path in csv_paths:
        logger.info("  → %s", path)


if __name__ == "__main__":
    main()
