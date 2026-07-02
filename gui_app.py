"""Lanzador de la interfaz grafica.

    python gui_app.py

Toda la logica de negocio vive en el paquete ``certificados`` (nucleo). Esta GUI
solo lo consume; para ejecucion por consola usa ``main.py``.
"""
from gui.app import launch

if __name__ == "__main__":
    launch()
