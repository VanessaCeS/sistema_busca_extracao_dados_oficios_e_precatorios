import datetime
import json
import os
import requests


url_info_cons = "https://clippingbrasil.com.br/InfoWsScript/service_xml.php"

json_data = {
        "data": '15/08/2023',
        "sigla": f"{os.getenv('sigla')}",
        "user":f"{os.getenv('user')}",
        "pass":f"{os.getenv('password')}"
        }
        
json_string = json.dumps(json_data)
form_data = {
      "json": json_string
  }

response = requests.post(url_info_cons, json=form_data)
print(response.content) 