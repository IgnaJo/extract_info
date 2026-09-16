"""Registro y auto-discovery de nodos disponibles."""

from __future__ import annotations

import importlib
import logging
import os
import pkgutil
from typing import Dict, List, Optional, Type

from extract_info.gui.nodes.base import BaseNode

logger = logging.getLogger(__name__)


class NodeRegistry:
    """Registry centralizado de nodos de extracción.

    Descubre automáticamente nodos en el paquete nodes/ y permite
    registrar nodos personalizados.
    """

    _nodes: Dict[str, Type[BaseNode]] = {}
    _instances: Dict[str, BaseNode] = {}

    @classmethod
    def discover(cls) -> None:
        """Descubre automáticamente nodos en el paquete actual."""
        package_path = os.path.dirname(__file__)

        for _, module_name, _ in pkgutil.iter_modules([package_path]):
            if module_name.startswith("_") or module_name in ("base", "registry"):
                continue

            try:
                module = importlib.import_module(
                    f"extract_info.gui.nodes.{module_name}"
                )

                for attr_name in dir(module):
                    attr = getattr(module, attr_name)
                    if (
                        isinstance(attr, type)
                        and issubclass(attr, BaseNode)
                        and attr is not BaseNode
                        and not getattr(attr, "__abstractmethods__", None)
                    ):
                        instance = attr()
                        cls._nodes[instance.name] = attr
                        logger.debug("Nodo descubierto: %s", instance.name)

            except Exception as e:
                logger.warning("Error descargando módulo %s: %s", module_name, e)

    @classmethod
    def register(cls, node_class: Type[BaseNode]) -> None:
        """Registra un nodo manualmente.

        Args:
            node_class: Clase que implementa BaseNode.
        """
        instance = node_class()
        cls._nodes[instance.name] = node_class
        logger.info("Nodo registrado manualmente: %s", instance.name)

    @classmethod
    def get_node(cls, name: str) -> Optional[BaseNode]:
        """Obtiene una instancia del nodo por nombre.

        Args:
            name: Nombre del nodo.

        Returns:
            Instancia del nodo o None si no existe.
        """
        if name not in cls._instances:
            if name not in cls._nodes:
                return None
            cls._instances[name] = cls._nodes[name]()

        return cls._instances[name]

    @classmethod
    def get_node_class(cls, name: str) -> Optional[Type[BaseNode]]:
        """Obtiene la clase del nodo por nombre.

        Args:
            name: Nombre del nodo.

        Returns:
            Clase del nodo o None si no existe.
        """
        return cls._nodes.get(name)

    @classmethod
    def list_nodes(cls) -> List[str]:
        """Retorna lista de nombres de nodos disponibles.

        Returns:
            Lista de nombres de nodos.
        """
        if not cls._nodes:
            cls.discover()
        return sorted(cls._nodes.keys())

    @classmethod
    def get_all_nodes(cls) -> Dict[str, Type[BaseNode]]:
        """Retorna diccionario de todos los nodos registrados.

        Returns:
            Dict con nombre → clase del nodo.
        """
        if not cls._nodes:
            cls.discover()
        return cls._nodes.copy()

    @classmethod
    def clear(cls) -> None:
        """Limpia el registry (útil para tests)."""
        cls._nodes.clear()
        cls._instances.clear()
