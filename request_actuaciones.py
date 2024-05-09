import requests

url = "https://eje.juscaba.gob.ar/iol-api/api/public/expedientes/actuaciones?filtro=%7B%22cedulas%22%3Atrue%2C%22escritos%22%3Atrue%2C%22despachos%22%3Atrue%2C%22notas%22%3Atrue%2C%22expId%22%3A2815608%2C%22accesoMinisterios%22%3Afalse%2C%22fechaNotificacionDesde%22%3Anull%2C%22fechaNotificacionHasta%22%3Anull%7D&page=0&size=5"

payload = {}
headers = {
  'Cookie': 'TS010cad59=015f5ef245d5d9cfffcee1977a171d7ffb116fbf5d71a08233c5c58cbf33dd7ce83244c4ab118a7982db968c26bc15422808051434'
}

response = requests.request("GET", url, headers=headers, data=payload)

print(response.text)
