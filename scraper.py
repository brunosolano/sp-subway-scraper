import requests
import re
from bs4 import BeautifulSoup
import time
import logging
import gspread
from oauth2client.service_account import ServiceAccountCredentials
import os
from email_debug import send_email as send_email
from apscheduler.schedulers.blocking import BlockingScheduler

lines_metro = ['azul', 'verde', 'vermelha', 'amarela', 'lilás', 'prata']
lines_cptm  = ['rubi', 'diamante', 'esmeralda', 'turquesa', 'coral', 'safira', 'jade']
all_lines   = lines_metro + lines_cptm

SPREADSHEET_ID = "1PiypIL4LNgG992EcS0rZzPO_rd639o6jHlhv-KHUX8s"

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.DEBUG)
logger.info('Starting scraper')

def get_page_html(url):
    try:
        page = requests.get(url)
        if page.status_code == 200:
            return page.text
        else:
            return None
    except:
        return None

def init_sheet(SPREADSHEET_ID):
    # use creds to create a client to interact with the Google Drive API
    scope = ['https://spreadsheets.google.com/feeds',
            'https://www.googleapis.com/auth/drive']
    headers = {
            "type": os.environ.get('TYPE', None),
            "project_id": os.environ.get('PROJECT_ID', None),
            "private_key_id": os.environ.get('PRIVATE_KEY_ID', None),
            "private_key": os.environ.get('PRIVATE_KEY', None),
            "client_email": os.environ.get('CLIENT_EMAIL', None),
            "client_id": os.environ.get('CLIENT_ID', None),
            "auth_uri": "https://accounts.google.com/o/oauth2/auth",
            "token_uri": "https://accounts.google.com/o/oauth2/token",
            "auth_provider_x509_cert_url": "https://www.googleapis.com/oauth2/v1/certs",
            "client_x509_cert_url": os.environ.get('CLIENT_x509_CERT_URL', None)
        }
    #logger.info(str(headers))
    creds = ServiceAccountCredentials.from_json_keyfile_dict(headers, scope)
    #creds = ServiceAccountCredentials.from_json_keyfile_name('client_secret.json', scope)
    client = gspread.authorize(creds)
    data_sheet = client.open_by_key(SPREADSHEET_ID).worksheet("data")
    return data_sheet

def get_operation_status(soup, all_lines):

    extracted_status = {line:'' for line in all_lines}

    # Contains all the info we need
    status_column = soup.find(class_="operacao")

    # The 'amarela' line is shown in a special container
    extracted_status['amarela'] = status_column.find(class_="status").text

    # All of the other lines are shown in a more orderly fashion. Metro has a div and CPTM has another one
    lines_containers  = status_column.find_all(class_="linhas")

    for container in lines_containers:
        line_info_divs = container.find_all(class_="info")
        # each info div has two span tags inside: one for line title and one for line status
        for div in line_info_divs:
            line_title  = ''
            line_status = ''
            spans = div.find_all("span")
            line_title = spans[0].text.lower()
            line_status = spans[1].text.lower()
            # now that we have line_title and line_status set, we only have to store it to return later
            extracted_status[line_title] = line_status
        logging.info('Extracted: {}'.format(extracted_status))

    return(extracted_status)

def get_time_data(soup):

    return soup.find('time').text

def check_data(op_status):
    for status in op_status.values():
        if(len(status) < 6 or status == ""):
            send_email(vq_home)
            break

sched = BlockingScheduler()
args = [SPREADSHEET_ID, all_lines]
@sched.scheduled_job('interval', minutes=6, args=args)
def timed_job(SPREADSHEET_ID, all_lines):
    vq_home = get_page_html('http://www.viaquatro.com.br')
    if vq_home is None:
        return

    s = BeautifulSoup(vq_home, 'html.parser')
    time_data = get_time_data(s)
    op_status = get_operation_status(s, all_lines)

    data_sheet = init_sheet(SPREADSHEET_ID)
    check_data(op_status)

    for line in all_lines:
        data_sheet.append_row([time_data, line, op_status[line]])

sched.start()