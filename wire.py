from seleniumwire import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.common.exceptions import NoSuchElementException
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.common.action_chains import ActionChains
from selenium.common.exceptions import StaleElementReferenceException
from selenium.common.exceptions import TimeoutException

output_dir = '/home/daj/buscador-eje/archivos'

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

url = 'https://eje.juscaba.gob.ar/iol-ui/p/expedientes?identificador=J-01-00093845-5/2022-0&open=false&tituloBusqueda=Causas&tipoBusqueda=CAU'
 

driver.get(url)
