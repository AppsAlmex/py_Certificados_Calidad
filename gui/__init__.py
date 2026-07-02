"""Capa de presentacion (GUI).

Depende del nucleo ``certificados`` pero NO contiene logica de negocio: solo
recoge datos del usuario, delega en el core y muestra resultados. Se puede borrar
por completo sin afectar el procesamiento por linea de comandos (``main.py``).
"""
from .controller import BatchController, QueueLogHandler

__all__ = ["BatchController", "QueueLogHandler"]
