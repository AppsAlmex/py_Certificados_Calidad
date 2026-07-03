"""Parser del XML de BI Publisher -> modelo de datos limpio del certificado.

Separa la DATA (lo que devuelve Oracle) del LAYOUT (como se ve el PDF). Este
modulo NO dibuja nada; solo convierte el XML del data model en objetos faciles de
usar por cualquier plantilla. Aqui vive la logica que hoy esta enterrada en el RTF
(dedup de caracteristicas y orden de categorias), pero en Python editable.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List

from lxml import etree

# Orden y etiqueta de las categorias en el PDF. Editable: cambia aqui el orden o
# los titulos de las secciones sin tocar el resto del codigo.
CATEGORIA_ORDEN = [
    ("SENSORIALES", "CARACTERISTICAS SENSORIALES"),
    ("ANALITICAS", "ESPECIFICACIONES ANALITICAS"),
    ("MICROBIOLOGICAS", "ESPECIFICACIONES MICROBIOLOGICAS"),
    ("METALES PESADOS", "METALES PESADOS"),
    ("OTROS", "OTROS"),
]


@dataclass
class Parametro:
    categoria: str
    caracteristica: str
    valor: str
    minimo: str
    maximo: str
    objetivo: str
    uom: str
    metodo: str
    user_sequence: int = 0
    result_value_num: str = ""


@dataclass
class CertificateData:
    formato: str
    # Encabezado / empresa
    empresa: str = ""
    lugar_expedicion: str = ""
    telefono: str = ""
    titulo: str = ""
    numero_certificado: str = ""
    # Datos del embarque
    producto: str = ""
    fecha_certificado: str = ""
    orden_embarque: str = ""
    equipo: str = ""
    cliente: str = ""
    transportista: str = ""
    sucursal: str = ""
    tanque_carga: str = ""
    planta_productora: str = ""
    parte_cliente: str = ""
    presentacion: str = ""
    fecha_fabricacion: str = ""
    fecha_caducidad: str = ""
    lote: str = ""
    unidades: str = ""
    inspector: str = ""
    observaciones: str = ""
    sellos: str = ""
    parametros: List[Parametro] = field(default_factory=list)
    # Campos extra (leyendas por cliente, etc.) accesibles por las plantillas.
    extra: Dict[str, str] = field(default_factory=dict)

    def parametros_por_categoria(self):
        """Devuelve [(titulo_seccion, [Parametro, ...]), ...] en orden del PDF."""
        result = []
        for clave, titulo in CATEGORIA_ORDEN:
            grupo = [p for p in self.parametros if p.categoria == clave]
            grupo.sort(key=lambda p: p.user_sequence)
            if grupo:
                result.append((titulo, grupo))
        return result


def _text(node, tag: str) -> str:
    if node is None:
        return ""
    el = node.find(tag)
    return (el.text or "").strip() if el is not None and el.text else ""


def parse_certificate(xml: bytes | str) -> CertificateData:
    """Convierte el XML del data model en un ``CertificateData``."""
    if isinstance(xml, str):
        xml = xml.encode("utf-8")
    root = etree.fromstring(xml)

    gen = root.find(".//G_DATOS_GENERALES")
    datos = root.find(".//G_DATOS")

    data = CertificateData(
        formato=_text(gen, "FORMATO") or _text(root, "P_FORMATO"),
        empresa=_text(gen, "ALMIDONES_MEXICANOS"),
        lugar_expedicion=_text(gen, "LUGAR_EXPEDICION"),
        telefono=_text(gen, "TELEFONO_EXPEDICION"),
        titulo=_text(gen, "CERTIFICADO_CALIDAD"),
        numero_certificado=_text(datos, "NUMERO_CERTIFICADO"),
        producto=_text(datos, "PRODUCTO"),
        fecha_certificado=_text(datos, "FECHA_CERTIFICADO"),
        orden_embarque=_text(datos, "NUMERO_EMBARQUE"),
        equipo=_text(datos, "EQUIPO"),
        cliente=_text(datos, "NOMBRE_CLIENTE"),
        transportista=_text(datos, "TRANSPORTISTA"),
        sucursal=_text(datos, "SUCURSAL"),
        tanque_carga=_text(datos, "TANQUE_CARGA"),
        planta_productora=_text(datos, "PLANTA_PRODUCTORA"),
        parte_cliente=_text(datos, "PARTE_CLIENTE"),
        presentacion=_text(datos, "GRANEL"),
        fecha_fabricacion=_text(datos, "FECHA_FABRICACION"),
        fecha_caducidad=_text(datos, "FECHA_CADUCIDAD"),
        lote=_text(datos, "LOTE"),
        unidades=_text(datos, "CANTIDAD_ENVIADA"),
        inspector=_text(datos, "NOMBRE_INSPECTOR"),
        observaciones=_text(datos, "OBSERVACIONES"),
        sellos=_text(root.find(".//G_SELLOS"), "SELLOS"),
    )

    # Leyendas / campos por cliente que las plantillas pueden usar.
    for tag in ("LEYENDA_PEPSI", "LEYENDA_PEPSI_2", "LEYENDA_CUERVO",
                "CERT_CONF_ANALISIS_PEPSI", "CODIGO_SAP_CUERVO", "CANTIDAD_LOTE"):
        data.extra[tag] = _text(datos, tag)

    data.parametros = _parse_parametros(root)
    return data


def _parse_parametros(root) -> List[Parametro]:
    """Extrae y deduplica los parametros (una fila por caracteristica).

    El XML repite cada caracteristica por varios planes de inspeccion. Nos
    quedamos con la que trae el valor medido real (RESULT_VALUE_NUM); si ninguna
    lo trae (p.ej. sensoriales), con la primera.
    """
    seen: Dict[tuple, Parametro] = {}
    for v in root.findall(".//G_VALORES"):
        categoria = _text(v, "CATEGORIA")
        caracteristica = _text(v, "CARACTERISTICA")
        if not caracteristica:
            continue
        key = (categoria, caracteristica)
        rvn = _text(v, "RESULT_VALUE_NUM")
        actual = seen.get(key)
        if actual is not None and not (rvn and not actual.result_value_num):
            continue  # ya tenemos una mejor (o igual) para esta caracteristica
        try:
            seq = int(_text(v, "USER_SEQUENCE") or 0)
        except ValueError:
            seq = 0
        seen[key] = Parametro(
            categoria=categoria,
            caracteristica=caracteristica,
            valor=_text(v, "VALOR"),
            minimo=_text(v, "MINIMO"),
            maximo=_text(v, "MAXIMO"),
            objetivo=_text(v, "OBJETIVO"),
            uom=_text(v, "UOM"),
            metodo=_text(v, "METODO"),
            user_sequence=seq,
            result_value_num=rvn,
        )
    return list(seen.values())
