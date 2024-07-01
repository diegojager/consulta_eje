from seleniumwire import webdriver
import re
import time
import json
import requests
from datetime import datetime
import psycopg2
from selenium.common.exceptions import TimeoutException

#output_dir = '/home/daj/buscador-eje/archivos'
ahora = datetime.now()
salida = open('horario.txt','a')
salida.write(ahora.strftime("%d/%m/%Y, %H:%M:%S")+"\n")
salida.close()

config_file_path = "db_config.txt"
bufferIds = []
bufferActuacionesAInsertar = []
bufferActuacionesAInsertarSinFechaDiligenciamiento = []
claves_file_path = "/home/crono/claves/clavesdeldia.txt"
ids = []
claves = []
fechas = []
abogados = []
clientes = []
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
    ##print(url)
    #start_time = time.perf_counter()
    try:
        driver.get(url)
        rq = driver.wait_for_request('/eje.juscaba.gob.ar/iol-api/api/public/expedientes/accesosExpediente.*',10)
    except TimeoutException:
        return None

    #print (rq)
    #duracion = time.perf_counter() - start_time
    #print (duracion)
    #print (rq)
    return rq.params.get('expId')

def cambiarfecha(fechadma):
    f0 = fechadma[:10]
    f1 = f0.split("/")
    #print(f1)
    return f1[2]+'/'+f1[1]+'/'+f1[0] +fechadma[10:]

def insertar_en_buffer(id_juicio, cuij, fecha, abogado, cliente, lista_actuaciones):
    #print (' lista de actuaciones ')
    #print (lista_actuaciones)
    if len(lista_actuaciones):
        abogado = limpiar_nombre_abogado(abogado) 
    
    for row in lista_actuaciones:
        ## cada fila es un diccionario con estos datos: {'numero':numero, 'fecha_firma':fecha_firma, 'firmantes':firmantes, 'titulo':titulo, 'fecha_diligenciamiento':fecha_diligenciamiento }   
        #print("row")
        #print(row['fecha_firma'])
        #print(fecha)
        if (row['firmantes'] != abogado) and (row['fecha_firma'] > fecha):
            if (row['fecha_diligenciamiento']):
                fila = ";".join([id_juicio, cliente, cuij, row['titulo'], str(row['numero']), row['fecha_firma'], row ['firmantes'],row['fecha_diligenciamiento']])+"\n"
                bufferActuacionesAInsertar.append(fila)
            else:
                fila = ";".join([id_juicio, cliente, cuij, row['titulo'], str(row['numero']), row['fecha_firma'], row ['firmantes']])+"\n"
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
    #start_time = time.perf_counter()
    urlActuaciones = f"https://eje.juscaba.gob.ar/iol-api/api/public/expedientes/actuaciones?filtro=%7B%22cedulas%22%3Atrue%2C%22escritos%22%3Atrue%2C%22despachos%22%3Atrue%2C%22notas%22%3Atrue%2C%22expId%22%3A{id_expediente}%2C%22accesoMinisterios%22%3Afalse%2C%22fechaNotificacionDesde%22%3Anull%2C%22fechaNotificacionHasta%22%3Anull%7D&page=0&size=5"

    payload = {}
    headers = {
      'Cookie': 'TS010cad59=015f5ef245d5d9cfffcee1977a171d7ffb116fbf5d71a08233c5c58cbf33dd7ce83244c4ab118a7982db968c26bc15422808051434'
    }
    response = requests.request("GET", urlActuaciones, headers=headers, data=payload)
    #duracion = time.perf_counter() - start_time
    #print (duracion)
    #print(response.text)
    return(response.text)

""" devuelve una lista de diccionarios con todas las actuaciones que contiene la respuesta """
def parsear_respuesta_actuaciones(respuesta):
    respuesta.replace('true', '"true"')
    try:
        j = json.loads(respuesta)
    except Exception as e:
        print(f"Error {e} al parsear la respuesta: {respuesta}")
        return []

    if not ('content') in j:
        return []

    actuaciones = j['content']
    ret = []
    for actuacion in actuaciones:
        #print('ACTUACION :') 
        #print(actuacion)
        if ('numero') in actuacion:
            numero = actuacion['numero']
        else:
            numero = 0
        fecha_firma = '' if not('fechaFirma') in actuacion else datetime.fromtimestamp(actuacion['fechaFirma']/1000).strftime("%Y-%m-%d %H:%M:%S")
        firmantes = '' if not ('firmantes') in actuacion else limpiar_nombre_abogado(actuacion['firmantes'])
        if 'fechaNotificacion' in actuacion:
            fecha_diligenciamiento  = datetime.fromtimestamp(actuacion['fechaNotificacion']/1000).strftime("%Y-%m-%d %H:%M:%S")
        else:
            fecha_diligenciamiento = ''
        if ('titulo' in actuacion):
            titulo = actuacion['titulo']
            ret.append({'numero':numero, 'fecha_firma':fecha_firma, 'firmantes':firmantes, 'titulo':titulo, 'fecha_diligenciamiento':fecha_diligenciamiento})
    #print (ret)
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
        cursor.copy_from(open("/home/pg/buffer.csv", "r"), "novedades_eje", sep=";", columns = ["juicio_id", "sys_cliente_id","cuij", "titulo", "numero", "fecha_firma", "firmantes", "fecha_diligenciamiento"])

        cursor.copy_from(open("/home/pg/buffersinfechadiligenciamiento.csv", "r"), "novedades_eje", sep=";", columns = ["juicio_id","sys_cliente_id", "cuij", "titulo", "numero", "fecha_firma", "firmantes"])
        connection.commit()
        print("Se insertaron los datos correctamente.")

    except (Exception, psycopg2.Error) as error:
        print("Error al copiar a la base de datos: ", error)

    finally:
        if connection:
            cursor.close()
            connection.close()

def procesar_clave( clave, id_eje):
    #print(f"Procesando : {clave}")  # Mostrar la clave que se está procesando
    #print(' id eje <'+id_eje+'>')
    if (id_eje == '0'):
       id_eje =  dameIdDeExpediente(clave)
       if (id_eje is None):
            print(clave +' NONE!!')
            return None
       bufferIds.append(';'.join([clave, id_eje])+"\n")
    if (id_eje):
        actuacionesDelExpediente = dameJsonActuaciones(id_eje)
        return parsear_respuesta_actuaciones(actuacionesDelExpediente)
    else:
        return None

def insertarIdsenBD(db_params, bufferIds):
        
    archivoIntermedio = open("/home/pg/bufferIds.csv", "w")
    archivoIntermedio.writelines(bufferIds)
    archivoIntermedio.close()

    try:
        connection = psycopg2.connect(**db_params)
        cursor = connection.cursor()
        cursor.copy_from(open("/home/pg/bufferIds.csv", "r"), "cruce_id_cuij", sep=";", columns = ["cuij", "expid"])
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
        juicio_id, clave, fecha_str, abogado, sys_cliente_id, expId = line.split(';')
        ids.append(juicio_id)
        claves.append(clave.strip())
        fechas.append(datetime.strptime(fecha_str.strip(), "%Y-%m-%d").strftime("%Y-%m-%d %H:%M:%S"))
        abogados.append(limpiar_nombre_abogado(abogado))  # verificar, me parece que este llamado a limpiar_nombre_abogado sobra
        clientes.append(sys_cliente_id)
        ids_eje.append(expId.strip())
    print ( "A procesar " + str(len(claves)) + " expedientes" )

contador = 0
for juicio_id, clave, fecha, abogado, cliente, id_eje in zip(ids, claves, fechas, abogados, clientes,ids_eje):
    del driver.requests
    if (datos_tabla := procesar_clave(clave, id_eje)):
        #print ( 'datos tabla en main ')
        #print (datos_tabla)
        insertar_en_buffer(juicio_id, clave, fecha, abogado, cliente, datos_tabla)
        contador+=1
        if (contador % 50 == 0):
            print(f"Ultima procesada : {clave}")  # Mostrar la clave que se está procesando
            print (' insertados ' + str(contador) + ' expedientes' )
            insertarBufferaBD(db_params, bufferActuacionesAInsertar,bufferActuacionesAInsertarSinFechaDiligenciamiento)
            insertarIdsenBD(db_params, bufferIds) 
            bufferActuacionesAInsertar.clear()
            bufferIds.clear()           
            bufferActuacionesAInsertarSinFechaDiligenciamiento.clear()

insertarIdsenBD(db_params, bufferIds)   
insertarBufferaBD(db_params, bufferActuacionesAInsertar,bufferActuacionesAInsertarSinFechaDiligenciamiento)
driver.quit()
ahora = datetime.now()
salida = open('horario.txt','a')
salida.write(ahora.strftime("%d/%m/%Y, %H:%M:%S"))
salida.close()
print("Proceso completado.")
