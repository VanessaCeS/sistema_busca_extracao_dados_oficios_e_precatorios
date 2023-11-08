from requests import Session
import time
import base64


def quebra_imagem(image_data, is_base64=False):
    api_key = ""

    captcha_data = base64.b64decode(image_data) if is_base64 else image_data

    s = Session()

    response = s.post('http://192.168.88.205/in.php',
                             files={'file': captcha_data},
                             data={'key': api_key, 'method': 'post'})

    if response.text[:2] != 'OK':
        raise Exception('API error: ' + response.text)

    captcha_id = response.text[3:]

    for i in range(1, 25):
        response = s.get(f'http://192.168.88.205/res.php?key={api_key}&action=get&id={captcha_id}')

        if response.text[:2] == 'OK':
            return {'captchaId': captcha_id, 'code': response.text[3:]}

        time.sleep(2)

    raise Exception('API error: Timeout')

