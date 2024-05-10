from seleniumwire import webdriver
import time
import requests
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import TimeoutException

#output_dir = '/home/daj/buscador-eje/archivos'

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

def dameIdDeExpediente(cuij):
    url = f'https://eje.juscaba.gob.ar/iol-ui/p/expedientes?identificador={cuij}&open=false&tituloBusqueda=Causas&tipoBusqueda=CAU'
    #start_time = time.perf_counter()
    driver.get(url)
    rq = driver.wait_for_request('/eje.juscaba.gob.ar/iol-api/api/public/expedientes/accesosExpediente.*',10)
    #duracion = time.perf_counter() - start_time
    #print (duracion)
    #print (rq)
    return rq.params.get('expId')

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
    print(response.text)

driver = webdriver.Chrome(options=setDriverOptions())


