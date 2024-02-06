import os
import time
import psycopg2
import glob
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

# Ruta outpu
output_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "pdf_files")

# Función para obtener la cantidad total de claves en el archivo
def obtener_total_claves(archivo):
    with open(archivo, 'r', encoding='utf-8') as f:
        return len(f.readlines())

# Obtener el total de claves en el archivo
total_claves = obtener_total_claves("claves/claves.txt")

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

# Imprimir información sobre las opciones seleccionadas
print(f"Por defecto, no realiza las descargas (-descargas para activar) y procesa todas las claves a menos que se especifique con -procesar xxx")

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




def procesar_contenedor_pdf(driver):
    try:
        WebDriverWait(driver, 1).until(
            EC.presence_of_element_located(
                (By.XPATH, '//*[@id="mat-dialog-13" or starts-with(@id, "/html/body/div[2]/div[6]/div/mat-dialog-container/iol-actuaciones-adjuntos")] | //div[@class="cdk-overlay-backdrop cdk-overlay-dark-backdrop cdk-overlay-backdrop-showing"]')
            )
        )

        # Si el contenedor aparece, pausar el bucle
        print("Contenedor detectado, procesando filas...")
        enlaces_pdf = driver.find_elements(By.XPATH, './/a[contains(translate(text(), "PDF", "pdf"), ".pdf")]')

        for enlace in enlaces_pdf:
            try:
                # Intento hacer clic utilizando el método regular
                enlace.click()
            except:
                # Si falla, intento hacer clic usando JavaScript
                driver.execute_script("arguments[0].click();", enlace)
            print(f"Contenedor detectado, procesando filas...")
            time.sleep(5)

        # Continuar con el bucle principal
        print("Enlaces PDF procesados, continuando el bucle principal...")
        time.sleep(3)
        # Presionar la tecla "Escape" para salir del contenedor
        driver.find_element(By.TAG_NAME, 'body').send_keys(Keys.ESCAPE)

    except NoSuchElementException:
        # Si no hay contenedor, no hacer nada (suprimir la excepción)
        pass
    except Exception as e:
        print(f"Objeto sin contenedor")

def obtener_ultimo_id_ocupado():
    try:
        connection = psycopg2.connect(**db_params)
        cursor = connection.cursor()
        cursor.execute("SELECT MAX(id) FROM novedades_eje;")
        result = cursor.fetchone()
        if result and result[0] is not None:
            return result[0] + 1  # Sumar 1 al último ID ocupado
        else:
            return 1  # Si no hay registros, comenzar desde 1
    except (Exception, psycopg2.Error) as error:
        print(f"Error al obtener el último ID ocupado: {error}")
        return 1  # En caso de error, comenzar desde 1
    finally:
        if connection:
            cursor.close()
            connection.close()


def get_last_filename_and_rename(save_folder, id_registro, numero_serie, tipo_archivo, fila_index, pagina, renombrados):
    time.sleep(2)  # Pausa de 1 segundo antes de continuar
    files = glob.glob(save_folder + '/*')
    if not files:
        return None

    # Calcular el número que se agregará al nombre del archivo
    incremento = (pagina - 1) * 5 + (fila_index - 1)  # Incremento basado en la página y fila

    for file in files:
        # Obtener el nombre y la extensión del archivo original
        file_name, file_extension = os.path.splitext(os.path.basename(file))
        
        # Asignar un valor predeterminado a new_filename
        new_filename = ""

        # Obtener el número de serie del archivo original
        if tipo_archivo == "AD":
            new_filename = f"{id_registro + 1 + incremento}-AD-{numero_serie}.pdf"
        elif tipo_archivo == "AC":
            new_filename = f"{id_registro + 1 + incremento}-AC-{numero_serie}.pdf"

        time.sleep(1)  # Pausa de 1 segundo antes de continuar

        new_path = os.path.join("db", new_filename)
        os.makedirs(os.path.dirname(new_path), exist_ok=True)
        new_path = os.path.abspath(new_path)

        shutil.move(file, new_path)
        renombrados.append(new_filename)  # Agregar el nombre renombrado a la lista

        # Incrementar el número de serie para el siguiente archivo adjunto
        numero_serie += 1

    return renombrados



# Función para procesar una clave
def procesar_clave(driver, clave, fecha_limite, datos_tabla, output_dir):
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

            time.sleep(0.4)

            try:
                if ejecutar_descargas:  # Condición para ejecutar descargas
                    elemento_adjunto = fila.find_element(By.XPATH, './/i[@mattooltip="Adjunto"]')
                    if elemento_adjunto:
                        actions = ActionChains(driver)
                        actions.move_to_element_with_offset(elemento_adjunto, 5, 5)  # Mover el cursor al centro del elemento
                        actions.click()
                        actions.perform()

                        procesar_contenedor_pdf(driver)
                        time.sleep(0.5)

                        tipo_archivo = "AD"
                        nombre_archivo = get_last_filename_and_rename(output_dir, id_registro_actual, numero_serie_ad, tipo_archivo, fila_index, pagina, renombrados)
                        time.sleep(1)
                        
                        datos_fila = fila.find_elements(By.TAG_NAME, 'mat-cell')
                        datos_fila = [dato.text for dato in datos_fila if dato.text not in ['description', 'attach_file']]
                        time.sleep(0.5)
                        datos_fila.insert(0, clave)
                        datos_fila.append(nombre_archivo)

                        numero_serie_ad += 1
            except NoSuchElementException:
                pass

            try:
                if ejecutar_descargas:  # Condición para ejecutar descargas
                    elemento_actuacion = fila.find_element(By.XPATH, './/i[@mattooltip="Descripcion"]')
                    if elemento_actuacion:
                        actions = ActionChains(driver)
                        actions.move_to_element_with_offset(elemento_actuacion, 5, 5)
                        actions.click()
                        actions.perform()

                        driver.switch_to.window(driver.window_handles[0])

                        tipo_archivo = "AC"
                        nombre_archivo = get_last_filename_and_rename(output_dir, id_registro_actual, numero_serie_ac, tipo_archivo, fila_index, pagina, renombrados)
                        time.sleep(1)

                        datos_fila = fila.find_elements(By.TAG_NAME, 'mat-cell')
                        datos_fila = [dato.text for dato in datos_fila if dato.text not in ['description', 'attach_file']]
                        time.sleep(0.5)
                        datos_fila.insert(0, clave)
                        datos_fila.append(nombre_archivo)

                        numero_serie_ac += 1
            except NoSuchElementException:
                pass

            datos_fila = fila.find_elements(By.TAG_NAME, 'mat-cell')
            datos_fila = [dato.text for dato in datos_fila]
            fecha_firmado = datetime.strptime(datos_fila[2], "%d/%m/%Y %H:%M:%S")
            if fecha_firmado >= fecha:
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

def asociar_archivos_a_registros(db_params, db_folder, renombrados):
    try:
        connection = psycopg2.connect(**db_params)
        cursor = connection.cursor()

        for archivo in renombrados:
            # Extraer información del nombre del archivo
            archivo_info = archivo.split('-')
            if len(archivo_info) != 3:
                continue  # El nombre de archivo no tiene el formato esperado

            id_registro = int(archivo_info[0])
            tipo_archivo = archivo_info[1]

            # Determinar la columna a actualizar
            columna = "adjuntos" if tipo_archivo == "AD" else "actuaciones"

            # Verificar si el archivo debe reemplazarse por un espacio en blanco
            if archivo_info[2] in ["attach_file", "description"]:
                archivo = " "  # Reemplazar por espacio en blanco

            # Verificar si la fila (ID) existe en la base de datos
            cursor.execute(f"SELECT id, {columna} FROM public.novedades_eje WHERE id = {id_registro};")
            resultado = cursor.fetchone()

            if resultado:
                # Obtener el valor actual de la columna
                columna_valor_actual = resultado[1]
                if columna_valor_actual is None:
                    columna_valor_actual = ""

                # Agregar el nombre del archivo a la columna, separado por comas
                columna_valor_actual += (" , " if columna_valor_actual else "") + archivo

                # Actualizar la columna correspondiente con los nombres de archivo
                update_query = f"UPDATE public.novedades_eje SET {columna} = %s WHERE id = {id_registro};"
                cursor.execute(update_query, (columna_valor_actual,))
                connection.commit()
                print(f"Archivo {archivo} asociado al registro con ID {id_registro} en la columna {columna}.")
            else:
                print(f"No se encontró el registro con ID {id_registro} para el archivo {archivo}.")

    except (Exception, psycopg2.Error) as error:
        print("Error al asociar archivos a registros en la base de datos:", error)

    finally:
        if connection:
            cursor.close()
            connection.close()

# Función para insertar datos en la base de datos
def insertar_datos_en_db(db_params, clave, datos_tabla):
    try:
        connection = psycopg2.connect(**db_params)
        cursor = connection.cursor()

        for row in datos_tabla:
            # Obtener los datos de la fila procesada
            cuij = row[0]  # Clave
            titulo = row[1]
            numero = row[2]
            fecha_firma = row[3]
            firmantes = row[4]
            fecha_diligenciamiento = row[-1]  # Última posición en la fila
            # Validar que la fecha de firma no esté vacía y tenga un formato válido antes de insertarla
            if fecha_firma and fecha_firma.strip():
                # Intentar insertar la fecha en ambos formatos posibles
                try:
                    fecha_firma = pd.to_datetime(fecha_firma, format='%d/%m/%Y %H:%M:%S').date()
                except ValueError:
                    try:
                        fecha_firma = pd.to_datetime(fecha_firma, format='%d/%m/%Y').date()
                    except ValueError:
                        fecha_firma = None
            else:
                fecha_firma = None

            # Validar que la fecha de diligenciamiento no esté vacía y tenga un formato válido antes de insertarla
            if fecha_diligenciamiento and fecha_diligenciamiento.strip():
                # Intentar insertar la fecha en ambos formatos posibles
                try:
                    fecha_diligenciamiento = pd.to_datetime(fecha_diligenciamiento, format='%d/%m/%Y %H:%M:%S').date()
                except ValueError:
                    try:
                        fecha_diligenciamiento = pd.to_datetime(fecha_diligenciamiento, format='%d/%m/%Y').date()
                    except ValueError:
                        fecha_diligenciamiento = None
            else:
                fecha_diligenciamiento = None

            # Insertar datos en la tabla "public.novedades_eje"
            insert_novedades_query = """
            INSERT INTO public.novedades_eje (cuij, titulo, numero, fecha_firma, firmantes, fecha_diligenciamiento)
            VALUES (%s, %s, %s, %s, %s, %s) RETURNING id;
            """
            values_novedades_eje = (
                cuij,
                titulo,
                numero,
                fecha_firma,
                firmantes,
                fecha_diligenciamiento
            )
            cursor.execute(insert_novedades_query, values_novedades_eje)
            inserted_id = cursor.fetchone()[0]

            # Realizar commit después de cada inserción
            connection.commit()

            print(f"Fila insertada con ID: {inserted_id}")

    except (Exception, psycopg2.Error) as error:
        print("Error al trabajar con la base de datos:", error)

    finally:
        if connection:
            cursor.close()
            connection.close()
            print("Conexión a la base de datos cerrada.")

claves_file_path = "claves/claves.txt"
claves = []
fechas = []

with open(claves_file_path, 'r', encoding='utf-8') as f:
    for line in f:
        print(line)
        clave, fecha_str = line.split(';')
        claves.append(clave.strip())
        fechas.append(datetime.strptime(fecha_str.strip(), "%d/%m/%Y"))

# Inicializar la lista renombrados en el ámbito global
renombrados = []

for clave, fecha in zip(claves[:expedientes_a_procesar], fechas[:expedientes_a_procesar]):
    datos_tabla = []
    id_registro_actual = obtener_ultimo_id_ocupado()  # Actualizar el ID para cada clave
    renombrados = []  # Reiniciar la lista renombrados para cada clave
    if (procesar_clave(driver, clave, fecha, datos_tabla, output_dir)):  # Ahora también pasamos la fecha a procesar_clave
        insertar_datos_en_db(db_params, clave, datos_tabla)
        # Actualizar id_registro_actual después de insertar los datos en la base de datos
        id_registro_actual = obtener_ultimo_id_ocupado()
        asociar_archivos_a_registros(db_params, datos_tabla, renombrados)  # Pasa la lista renombrados como argumento


# Crear un DataFrame de pandas con los datos de la tabla
df = pd.DataFrame(datos_tabla)

# Cerrar el navegador
driver.quit()

print("Proceso completado.")
