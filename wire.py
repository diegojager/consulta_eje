from seleniumwire import webdriver
import re
import time
import json
import requests
from datetime import datetime
import psycopg2
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import TimeoutException

#output_dir = '/home/daj/buscador-eje/archivos'

config_file_path = "db_config.txt"
bufferIds = []
bufferActuacionesAInsertar = []
bufferActuacionesAInsertarSinFechaDiligenciamiento = []
claves_file_path = "claves/clavespaula.txt"
ids = []
claves = []
fechas = []
abogados = []
ids_eje = []


def setDriverOptions():
    options = webdriver.ChromeOptions()
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument("window-size=1920,1080")
    options.add_argument("headless=new")
    # Configuración de preferencias de Chrome
    chrome_prefs = {
        "plugins.always_open_pdf_externally": True,
        #"download.default_directory": output_dir,
        "download.directory_upgrade": True,
        "download.prompt_for_download": False,
        "safebrowsing.enabled": False,
        "profile.default_content_setting_values.automatic_downloads": 1,
        "profile.default_content_setting_values.popups": 0,
        "disable-software-rasterizer": True,
        "disable-dev-shm-usage": True,
    }
    options.add_experimental_option('prefs', chrome_prefs)
    return options


    """
    Retrieves the ID of an expediente from the Eje website based on the provided CUJ.
    Args:
        cuij (str): The CUiJ (Código Único de Identificación de la Justicia) of the expediente.
    Returns:
        str: The ID of the expediente.
    Raises:
        None.

    Note:
        - The function sends a GET request to the Eje website with the provided CUJ.
        - It waits for a request to the '/eje.juscaba.gob.ar/iol-api/api/public/expedientes/accesosExpediente.*' endpoint.
        - The function returns the value of the 'expId' parameter from the request.
    """
def dameIdDeExpediente(cuij):
    url = f'https://eje.juscaba.gob.ar/iol-ui/p/expedientes?identificador={cuij}&open=false&tituloBusqueda=Causas&tipoBusqueda=CAU'
    print(url)
    #start_time = time.perf_counter()
    driver.get(url)
    rq = driver.wait_for_request('/eje.juscaba.gob.ar/iol-api/api/public/expedientes/accesosExpediente.*',10)
    print (rq)
    #duracion = time.perf_counter() - start_time
    #print (duracion)
    #print (rq)
    return rq.params.get('expId')

def cambiarfecha(fechadma):
    f0 = fechadma[:10]
    f1 = f0.split("/")
    #print(f1)
    return f1[2]+'/'+f1[1]+'/'+f1[0] +fechadma[10:]

def insertar_en_buffer(id_juicio, cuij, fecha, abogado, lista_actuaciones):
    print (' lista de actuaciones ')
    print (lista_actuaciones)
    if len(lista_actuaciones):
        abogado = limpiar_nombre_abogado(abogado)
    
    for row in lista_actuaciones:
        ## cada fila es un diccionario con estos datos: {'numero':numero, 'fecha_firma':fecha_firma, 'firmantes':firmantes, 'titulo':titulo, 'fecha_diligenciamiento':fecha_diligenciamiento }   
        print("row")
        print(row['fecha_firma'])
        print(fecha)
        if (row['firmantes'] != abogado) and (row['fecha_firma'] > fecha):
            if (row['fecha_diligenciamiento']):
                fila = ";".join([id_juicio, cuij, row['titulo'], str(row['numero']), row['fecha_firma'], row ['firmantes'],row['fecha_diligenciamiento']])+"\n"
                bufferActuacionesAInsertar.append(fila)
            else:
                fila = ";".join([id_juicio, cuij, row['titulo'], str(row['numero']), row['fecha_firma'], row ['firmantes']])+"\n"
                bufferActuacionesAInsertarSinFechaDiligenciamiento.append(fila)

def limpiar_nombre_abogado(nombre_abogado):
    """
    Función para limpiar el nombre de un abogado en una cadena de texto.

    Recibe como parámetro una cadena de texto con el nombre del abogado,
    y devuelve una cadena con el nombre limpio de espacios en blanco sobrantes,
    caracteres de puntuación y nombres incompletos.

    Los nombres de abogado se suelen escribir con comas o puntos suspensivos
    para separar los apellidos paterno, materno y nombres. Esta función busca
    todos los delimitadores posibles en la cadena de entrada y los utiliza
    para separar los tokens que componen el nombre. Luego, se eliminan los
    espacios en blanco sobrantes de cada token y se dejan solo los tokens que
    tengan al menos un caracter. Finalmente, se devuelve la lista de tokens
    limpios separados por comas.

    Ejemplo:
    >>> limpiar_nombre_abogado('JUAN PEREZ GARCIA, MARIA LUISA')
    'JUAN PEREZ GARCIA, MARIA LUISA'
    >>> limpiar_nombre_abogado('JUAN PEREZ GARCIA ; MARIA LUISA')
    'JUAN PEREZ GARCIA, MARIA LUISA'
    >>> limpiar_nombre_abogado('JUAN PEREZ GARCIA, MARIA LUISA;')
    'JUAN PEREZ GARCIA, MARIA LUISA'

    """
    delim = (',', ';', ' ')
    nombre_abogado = nombre_abogado.upper().strip()
    regex_pattern = '|'.join(map(re.escape, delim))
    tokens = re.split(regex_pattern, nombre_abogado)
    validos = []

    for token in tokens:
        token = token.strip()
        if token:
            validos.append(token)
    return ','.join(validos)

def dameJsonActuaciones(id_expediente):
    start_time = time.perf_counter()
    urlActuaciones = f"https://eje.juscaba.gob.ar/iol-api/api/public/expedientes/actuaciones?filtro=%7B%22cedulas%22%3Atrue%2C%22escritos%22%3Atrue%2C%22despachos%22%3Atrue%2C%22notas%22%3Atrue%2C%22expId%22%3A{id_expediente}%2C%22accesoMinisterios%22%3Afalse%2C%22fechaNotificacionDesde%22%3Anull%2C%22fechaNotificacionHasta%22%3Anull%7D&page=0&size=5"

    payload = {}
    headers = {
      'Cookie': 'TS010cad59=015f5ef245d5d9cfffcee1977a171d7ffb116fbf5d71a08233c5c58cbf33dd7ce83244c4ab118a7982db968c26bc15422808051434'
    }
    response = requests.request("GET", urlActuaciones, headers=headers, data=payload)
    duracion = time.perf_counter() - start_time
    print (duracion)
    #print(response.text)
    return(response.text)

""" devuelve una lista de diccionarios con todas las actuaciones que contiene la respuesta """
def parsear_respuesta_actuaciones(respuesta):
    respuesta.replace('true', '"true"')
    j = json.loads(respuesta)
    actuaciones = j['content']
    ret = []
    for actuacion in actuaciones:
        numero = actuacion['numero']
        fecha_firma = datetime.fromtimestamp(actuacion['fechaFirma']/1000).strftime("%Y-%m-%d %H:%M:%S")
        firmantes = limpiar_nombre_abogado(actuacion['firmantes'])
        titulo = actuacion['titulo']
        if 'fechaNotificacion' in actuacion:
            fecha_diligenciamiento  = datetime.fromtimestamp(actuacion['fechaNotificacion']/1000).strftime("%Y-%m-%d %H:%M:%S")
        else:
            fecha_diligenciamiento = ''
        ret.append({'numero':numero, 'fecha_firma':fecha_firma, 'firmantes':firmantes, 'titulo':titulo, 'fecha_diligenciamiento':fecha_diligenciamiento})
    return ret
 
def cargar_configuracion_db(config_file_path):
    config = {}
    try:
        with open(config_file_path, 'r') as file:
            lines = file.readlines()
            for line in lines:
                key, value = line.strip().split(': ')
                config[key] = value
        return config
    except Exception as e:
        print(f"Error al cargar la configuración de la base de datos: {e}")
        return None    

def insertarBufferaBD(db_params, bufferActuacionesAInsertar,bufferActuacionesAInsertarSinFechaDiligenciamiento):
        
    archivoIntermedio = open("/home/pg/buffer.csv", "w")
    archivoIntermedio.writelines(bufferActuacionesAInsertar)
    archivoIntermedio.close()

    archivoIntermedio = open("/home/pg/buffersinfechadiligenciamiento.csv","w")
    archivoIntermedio.writelines(bufferActuacionesAInsertarSinFechaDiligenciamiento)
    archivoIntermedio.close()


    try:
        connection = psycopg2.connect(**db_params)
        cursor = connection.cursor()
        cursor.copy_from(open("/home/pg/buffer.csv", "r"), "novedades_eje", sep=";", columns = ["juicio_id", "cuij", "titulo", "numero", "fecha_firma", "firmantes", "fecha_diligenciamiento"])

        #[juicio_id, cuij, titulo, numero, fecha_firma, firmantes, fecha_diligenciamiento]
        """sql = "COPY novedades_eje (juicio_id, cuij, titulo, numero, fecha_firma, firmantes, fecha_diligenciamiento) FROM STDIN WITH DELIMITER ';' CSV HEADER;"
        with open("/home/pg/buffer.csv", "r") as f:
            cursor.copy_expert(sql, file=f)
            """
        connection.commit()

        cursor.copy_from(open("/home/pg/buffersinfechadiligenciamiento.csv", "r"), "novedades_eje", sep=";", columns = ["juicio_id", "cuij", "titulo", "numero", "fecha_firma", "firmantes"])
        """
        sql = "COPY novedades_eje (juicio_id, cuij, titulo, numero, fecha_firma, firmantes) FROM STDIN WITH DELIMITER ';' CSV HEADER;"
        with open("/home/pg/buffersinfechadiligenciamiento.csv", "r") as f:
            cursor.copy_expert(sql, file=f)
            """
        connection.commit()
        print("Se insertaron los datos correctamente.")

    except (Exception, psycopg2.Error) as error:
        print("Error al copiar a la base de datos: ", error)

    finally:
        if connection:
            cursor.close()
            connection.close()

def procesar_clave( clave, id_eje):
    print(f"Procesando : {clave}")  # Mostrar la clave que se está procesando
    #print(' id eje <'+id_eje+'>')
    if (id_eje == '0'):
       id_eje =  dameIdDeExpediente(clave)
       if (id_eje is None):
            print('NONE!!')
       else:
            print('id eje = '+id_eje)
       bufferIds.append(';'.join([clave, id_eje])+"\n")

    actuacionesDelExpediente = dameJsonActuaciones(id_eje)
    return parsear_respuesta_actuaciones(actuacionesDelExpediente)

def insertarIdsenBD(db_params, bufferIds):
        
    archivoIntermedio = open("/home/pg/bufferIds.csv", "w")
    archivoIntermedio.writelines(bufferIds)
    archivoIntermedio.close()

    try:
        connection = psycopg2.connect(**db_params)
        cursor = connection.cursor()
        #[juicio_id, cuij, titulo, numero, fecha_firma, firmantes, fecha_diligenciamiento]
        sql = "COPY cruce_id_cuij (cuij, expid) FROM STDIN WITH DELIMITER ';' CSV HEADER;"
        with open("/home/pg/bufferIds.csv", "r") as f:
            cursor.copy_expert(sql, file=f)
        connection.commit()
        print("Se insertaron los datos correctamente.")

    except (Exception, psycopg2.Error) as error:
        print("Error al copiar los ids de eje a la base de datos: ", error)

    finally:
        if connection:
            cursor.close()
            connection.close()


db_params = cargar_configuracion_db(config_file_path)
if not db_params:
    print("No se pudo cargar la configuración de la base de datos.")

driver = webdriver.Chrome(options=setDriverOptions())



with open(claves_file_path, 'r', encoding='utf-8') as f:

    for line in f:
        juicio_id, clave, fecha_str, abogado, expId = line.split(';')
        ids.append(juicio_id)
        claves.append(clave.strip())
        fechas.append(datetime.strptime(fecha_str.strip(), "%Y-%m-%d").strftime("%Y-%m-%d %H:%M:%S"))
        abogados.append(limpiar_nombre_abogado(abogado))
        ids_eje.append(expId.strip())
    print ( "A procesar " + str(len(claves)) + " expedientes" )


for juicio_id, clave, fecha, abogado, id_eje in zip(ids, claves, fechas, abogados,ids_eje):
    del driver.requests
    
    if (datos_tabla := procesar_clave(clave, id_eje)):
        print ( 'datos tabla en main ')
        print (datos_tabla)
        insertar_en_buffer(juicio_id, clave, fecha, abogado, datos_tabla)

insertarIdsenBD(db_params, bufferIds) 
insertarBufferaBD(db_params, bufferActuacionesAInsertar,bufferActuacionesAInsertarSinFechaDiligenciamiento)
driver.quit()

print("Proceso completado.")
