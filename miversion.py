import os
import time
import psycopg2
import glob
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import TimeoutException
import shutil
import argparse
from datetime import datetime



# Función para obtener la cantidad total de claves en el archivo
def obtener_total_claves(archivo):
    with open(archivo, 'r', encoding='utf-8') as f:
        return len(f.readlines())

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
"""
SI TENGO EL ID DEL JUICIO, CON ESTO LE PEGO A LA API QUE ME TRAE EL JSON CON LAS ACTUACIONES 
 
EL ULTIMO PARAMETRO, PAGE, ME DICE CUANTAS ACTUACIONES TRAE LA API

https://eje.juscaba.gob.ar/iol-api/api/public/expedientes/actuaciones?filtro=%7B%22cedulas%22%3Atrue%2C%22escritos%22%3Atrue%2C%22despachos%22%3Atrue%2C%22notas%22%3Atrue%2C%22expId%22%3A{ID DEL EXPEDIENTE}%2C%22accesoMinisterios%22%3Afalse%2C%22fechaNotificacionDesde%22%3Anull%2C%22fechaNotificacionHasta%22%3Anull%7D&page=0&size=5
"""
# Función para procesar una clave
def procesar_clave(driver, clave, fecha_limite, abogado, datos_tabla):
    print(f"Procesando clave: {clave}")  # Mostrar la clave que se está procesando

    url = f'https://eje.juscaba.gob.ar/iol-ui/p/expedientes?identificador={clave}&open=false&tituloBusqueda=Causas&tipoBusqueda=CAU'

    # Abrir la página
    driver.get(url)

    # Esperar a que se cargue el elemento específico
    try:
        wait = WebDriverWait(driver, 10)
        elemento_especifico = wait.until(
            EC.visibility_of_element_located((By.XPATH, '//*[@id="alto-app"]/div[2]/mat-sidenav-container/mat-sidenav-content/div/iol-expediente-lista/div/div/div[2]/iol-expediente-tarjeta/div/iol-expediente-tarjeta-encabezado/div/div[2]/div/a/strong')))
    #except TimeoutException:
    except:
        print ('Timeout para '+clave)
        return False
    elemento_especifico.click()

    # Hacer clic en la pestaña de Actuaciones
    pestaña_actuaciones = wait.until(EC.presence_of_element_located((By.XPATH, '//*[@id="mat-tab-label-0-1"]/div')))
    pestaña_actuaciones.click()


    pagina = 1
    while True:
        tabla_filas = wait.until(
            EC.presence_of_all_elements_located((By.XPATH,
                                                '//*[@id="mat-tab-content-0-1"]/div/iol-expediente-actuaciones/div/div[2]/mat-table/mat-row')))

        for fila_index, fila in enumerate(tabla_filas):
            # daj comenta print(f"Página {pagina}, Fila {fila_index + 1}...")  # Mostrar página y fila

            # Reiniciar el contador de serie para cada fila
            numero_serie_ad = 1
            numero_serie_ac = 1

            time.sleep(0.4)  # ver si se puede bajar esta espera

            datos_fila = fila.find_elements(By.TAG_NAME, 'mat-cell')
            datos_fila = [dato.text for dato in datos_fila]
            fecha_firmado = datetime.strptime(datos_fila[2], "%d/%m/%Y %H:%M:%S")
            if fecha_firmado >= fecha and abogado != limpiar_nombre_abogado(datos_fila[3]):
                # Agregar la clave al principio de la fila
                datos_fila.insert(0, clave)
                datos_tabla.append(datos_fila)
                    # Intentar avanzar a la siguiente página
        try:
            boton_siguiente = WebDriverWait(driver, 5).until(
                EC.element_to_be_clickable((By.XPATH,
                                            '//*[@id="mat-tab-content-0-1"]/div/iol-expediente-actuaciones/div/div[2]/mat-paginator/div/div[2]/button[2]')))
            driver.execute_script("arguments[0].scrollIntoView();", boton_siguiente)
            boton_siguiente.click()
            pagina += 1
            
            # Mover el scroll al inicio de la página
            driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.UP) 
            
            time.sleep(1)  # Pausa de 1 segundo antes de continuar
            
        except Exception as e:
            # Si no se encuentra el botón "Siguiente" o no es cliclable, salimos del bucle
            break
        return True

def cambiarfecha(fechadma):
    f0 = fechadma[:10]
    f1 = f0.split("/")
    #print(f1)
    return f1[2]+'/'+f1[1]+'/'+f1[0] +fechadma[10:]

# Función para insertar datos en la base de datos
def insertar_en_buffer(id_juicio, clave, datos_tabla):
    for row in datos_tabla:
        # Obtener los datos de la fila procesada
        cuij = row[0]  # Clave
        titulo = row[1]
        numero = row[2]
        fecha_firma = row[3]
        firmantes = row[4]
        fecha_diligenciamiento = row[-1]  # Última posición en la fila

        if fecha_firma and fecha_firma.strip():
           fecha_firma = cambiarfecha(fecha_firma)
        else:
           fecha_firma = ''

        if fecha_diligenciamiento and fecha_diligenciamiento.strip():
           fecha_diligenciamiento = cambiarfecha(fecha_diligenciamiento)
        else:
           fecha_diligenciamiento = ''
        fila = ";".join([id_juicio, cuij, titulo, numero, fecha_firma, firmantes, fecha_diligenciamiento])+"\n"
        bufferAInsertar.append(fila)

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

def insertarBufferaBD(db_params, bufferAInsertar):
            
    archivoIntermedio = open("buffer.csv", "w")
    archivoIntermedio.writelines(bufferAInsertar)
    archivoIntermedio.close()

    try:
        connection = psycopg2.connect(**db_params)
        cursor = connection.cursor()
        #[juicio_id, cuij, titulo, numero, fecha_firma, firmantes, fecha_diligenciamiento]
        sql = "COPY novedades_eje (juicio_id, cuij, titulo, numero, fecha_firma, firmantes, fecha_diligenciamiento) FROM STDIN WITH DELIMITER ';' CSV HEADER;"
        with open("buffer.csv", "r") as f:
            cursor.copy_expert(sql, file=f)
        connection.commit()
        print("Se insertaron los datos correctamente.")

    except (Exception, psycopg2.Error) as error:
        print("Error al copiar a la base de datos: ", error)

    finally:
        if connection:
            cursor.close()
            connection.close()


# Ruta output
output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdf_files")

# Obtener el total de claves en el archivo
total_claves = obtener_total_claves("claves/clavespaula.txt")

# Crear un objeto ArgumentParser
parser = argparse.ArgumentParser(description='Procesar expedientes y descargas.')

# Establecer un valor predeterminado para -procesar basado en el total de claves
parser.add_argument('-procesar', type=int, default=total_claves, help='Cantidad de expedientes a procesar (por defecto, procesa todas las claves)')

# Agregar argumento para descargas
parser.add_argument('-descargas', action='store_true', help='Ejecuta las funciones de descarga')

# Obtener los argumentos de la línea de comandos
args = parser.parse_args()

# Acceder al valor del argumento -procesar y -descargas
expedientes_a_procesar = args.procesar
ejecutar_descargas = args.descargas

# Ruta al archivo de configuración
config_file_path = "db_config.txt"

# Cargar la configuración de la base de datos desde el archivo
db_params = cargar_configuracion_db(config_file_path)

# Verificar si se cargó la configuración correctamente
if db_params:
    print("Configuración de la base de datos cargada exitosamente.")
else:
    print("No se pudo cargar la configuración de la base de datos.")

# Configuración de Selenium
options = webdriver.ChromeOptions()
options.add_argument('--disable-gpu')
options.add_argument('--no-sandbox')
options.add_argument("window-size=1920,1080")
options.add_argument("headless=new")
# Configuración de preferencias de Chrome
chrome_prefs = {
    "plugins.always_open_pdf_externally": True,
    "download.default_directory": output_dir,
    "download.directory_upgrade": True,
    "download.prompt_for_download": False,
    "safebrowsing.enabled": False,
    "profile.default_content_setting_values.automatic_downloads": 1,
    "profile.default_content_setting_values.popups": 0,
    "disable-software-rasterizer": True,
    "disable-dev-shm-usage": True,
}
options.add_experimental_option('prefs', chrome_prefs)
driver = webdriver.Chrome(options=options)

claves_file_path = "claves/clavespaula.txt"
ids = []
claves = []
fechas = []
abogados = []

bufferAInsertar = []

with open(claves_file_path, 'r', encoding='utf-8') as f:
    for line in f:
        #print(line)
        juicio_id, clave, fecha_str, abogado = line.split(';')
        ids.append(juicio_id)
        claves.append(clave.strip())
        fechas.append(datetime.strptime(fecha_str.strip(), "%d/%m/%Y"))
        abogados.append(limpiar_nombre_abogado(abogado))

for juicio_id, clave, fecha, abogado in zip(ids[:expedientes_a_procesar], claves[:expedientes_a_procesar], fechas[:expedientes_a_procesar], abogados[:expedientes_a_procesar]):
    datos_tabla = []
    
    if (procesar_clave(driver, clave, fecha, abogado, datos_tabla)):
        insertar_en_buffer(juicio_id, clave, datos_tabla)
        
insertarBufferaBD(db_params, bufferAInsertar)
driver.quit()

print("Proceso completado.")
