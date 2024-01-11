from capmonster_python import RecaptchaV2Task, HCaptchaTask
import os


def log_file(site_key, url, tipo):
    with open('arquivos_logs/LOG_CAPMONSTER.txt', 'a+') as f:
        f.write(f'{tipo} - {site_key} - {url}\n')


def recaptcha(site_key, url):
    log_file(site_key, url, 'RECAPTCHA')

    capmonster = RecaptchaV2Task(os.environ.get('API_KEY_CAPMONSTER'))

    task_id = capmonster.create_task(url, site_key)

    result = capmonster.join_task_result(task_id)

    return {'captchaId': 0, 'code': result.get('gRecaptchaResponse')}


def hcaptcha(site_key, url):
    log_file(site_key, url, 'HCAPTCHA')

    capmonster = HCaptchaTask(os.environ.get('API_KEY_CAPMONSTER'))

    task_id = capmonster.create_task(url, site_key)

    result = capmonster.join_task_result(task_id)

    return {'captchaId': 0, 'code': result.get('gRecaptchaResponse')}