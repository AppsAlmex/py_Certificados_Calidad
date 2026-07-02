import requests
import base64
from lxml import etree
import urllib3

# Eliminar warning de certificados SSL (solo para pruebas)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def generar_xml_params(params):
    xml = ""

    for nombre, valor in params.items():
        xml += f"""
        <v2:item>
            <v2:name>{nombre}</v2:name>
            <v2:values>
                <v2:item>{valor}</v2:item>
            </v2:values>
        </v2:item>
        """

    return xml


# ============================================================================
# CONFIGURACIÓN
# ============================================================================

HOST = "https://fa-enkq-saasfaprod1.fa.ocs.oraclecloud.com"
URL = f"{HOST}/xmlpserver/services/v2/ReportService"

USER = "appsalmex2"
PASSWORD = "Almex27562020"

REPORT_PATH = "/Custom/Certificados_calidad/XXALMEX_CERTIFICADO_CALIDAD.xdo"

FORMATO = "pdf"

# ============================================================================
# PARÁMETROS DEL REPORTE
# ============================================================================

parametros = {
    "P_EMBARQUE": "256436",
    "P_FORMATO": "1",
    "P_INSPECTOR": "003",
    "P_OBSERVACIONES": "",
    "P_PLANTA_PROD": "MARSHALL, MN",
    "P_TANQUE": "ADMX0106215_221209",
    "P_SELLO1": "951",
    "P_CANTIDAD1": "2",
    "P_SELLO2": "",
    "P_CANTIDAD2": "",
    "P_SELLO3": "",
    "P_CANTIDAD3": "",
    "P_SELLO4": "",
    "P_CANTIDAD4": ""
}

# ============================================================================
# GENERAR XML DE PARÁMETROS
# ============================================================================

xml_params = generar_xml_params(parametros)


# ============================================================================
# SOAP REQUEST
# ============================================================================

soap_request = f"""
<soapenv:Envelope xmlns:soapenv="http://schemas.xmlsoap.org/soap/envelope/"
                  xmlns:v2="http://xmlns.oracle.com/oxp/service/v2">

   <soapenv:Header/>

   <soapenv:Body>
      <v2:runReport>

         <v2:reportRequest>

            <v2:attributeFormat>{FORMATO}</v2:attributeFormat>

            <v2:parameterNameValues>
               <v2:listOfParamNameValues>
                  {xml_params}
               </v2:listOfParamNameValues>
            </v2:parameterNameValues>

            <v2:reportAbsolutePath>{REPORT_PATH.strip()}</v2:reportAbsolutePath>

         </v2:reportRequest>

         <v2:userID>{USER}</v2:userID>
         <v2:password>{PASSWORD}</v2:password>

      </v2:runReport>
   </soapenv:Body>

</soapenv:Envelope>
"""

# ============================================================================
# HEADERS
# ============================================================================

headers = {
    "Content-Type": "text/xml; charset=UTF-8"
}

# ============================================================================
# EJECUTAR REQUEST
# ============================================================================

print("Ejecutando reporte...")

response = requests.post(
    URL,
    data=soap_request.encode("utf-8"),
    headers=headers,
    verify=False,
    timeout=300
)

print(f"HTTP Status: {response.status_code}")

if response.status_code != 200:
    print(response.text)
    raise Exception("Error en la llamada SOAP")

# ============================================================================
# EXTRAER reportBytes
# ============================================================================

ctype = response.headers.get("Content-Type", "")
if "xml" not in ctype.lower():
    print("Respuesta NO es XML. Content-Type:", ctype)
    print(response.text[:2000])
    raise Exception("El servidor devolvio HTML/no-XML (endpoint o auth incorrectos)")

root = etree.fromstring(response.content)

report_bytes = root.xpath(
    "//*[local-name()='reportBytes']/text()"
)

if not report_bytes:
    print(response.text)
    raise Exception("No fue encontrado reportBytes")

archivo_base64 = report_bytes[0]

# ============================================================================
# DECODIFICAR RESULTADO
# ============================================================================

contenido = base64.b64decode(archivo_base64)

# ============================================================================
# GUARDAR ARCHIVO
# ============================================================================

if FORMATO.lower() == "pdf":

    nombre_archivo = "CertificadoCalidad.pdf"

    with open(nombre_archivo, "wb") as f:
        f.write(contenido)

    print(f"Archivo PDF generado: {nombre_archivo}")

elif FORMATO.lower() == "xml":

    nombre_archivo = "CertificadoCalidad.xml"

    with open(nombre_archivo, "wb") as f:
        f.write(contenido)

    print(f"Archivo XML generado: {nombre_archivo}")

elif FORMATO.lower() == "xlsx":

    nombre_archivo = "CertificadoCalidad.xlsx"

    with open(nombre_archivo, "wb") as f:
        f.write(contenido)

    print(f"Archivo XLSX generado: {nombre_archivo}")

else:

    nombre_archivo = f"resultado.{FORMATO}"

    with open(nombre_archivo, "wb") as f:
        f.write(contenido)

    print(f"Archivo generado: {nombre_archivo}")

print("Proceso terminado.")
