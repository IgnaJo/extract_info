"""Sistema de nodos modulares para extracción de metadatos."""

from extract_info.pipelines.base import NODE_SPECS, list_nodes, get_node_spec, process_folder
from extract_info.pipelines.retail import retail_process_folder
from extract_info.pipelines.aseguradora import aseguradora_process_folder

__all__ = [
    "NODE_SPECS",
    "list_nodes",
    "get_node_spec",
    "process_folder",
    "retail_process_folder",
    "aseguradora_process_folder",
]