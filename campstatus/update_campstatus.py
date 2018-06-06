from bs4 import BeautifulSoup
import requests
import re
import gspread
import json
from oauth2client import file, client, tools

SCOPES = ['https://www.googleapis.com/auth/spreadsheets']
SECRETS = 'client_secret.json'
# NFS website(s)
FOREST_URLS = [
    'https://www.fs.usda.gov/activity/eldorado/recreation/camping-cabins/?recid=71008&actid=29' # El Dorado
]
# Google sheet key
# for sheet https://docs.google.com/spreadsheets/d/19TrtOtNcBHffXP1NFfz_XB_7xb3LbexpjVSGjyKpHWo/edit#gid=0
SHEET_KEY = "19TrtOtNcBHffXP1NFfz_XB_7xb3LbexpjVSGjyKpHWo"

def authenticate():
    flow = client.flow_from_clientsecrets(SECRETS, SCOPES)
    creds = tools.run_flow(flow, store)
    return creds

def open_camping_sheet(key):
    """Opens the google sheet object"""
    # Setup the Sheets API
    store = file.Storage('credentials.json')
    creds = store.get()
    if not creds or creds.invalid:
        creds = authenticate()
    f = gspread.authorize(creds) # authenticate with Google
    sheet = f.open_by_key(key).sheet1
    return sheet

def update_sheet(sheet, campground_name, status, status_col=1):
    """Updates the appropriate cell with campground status"""
    try:
        cell = sheet.find(re.compile('(?i){}'.format(campground_name)))
    except Exception as e:
        if type(e).__name__ == 'CellNotFound':
            print '{} not found in sheet'.format(campground_name)
            return None
    row = cell.row
    current_status = sheet.cell(row, status_col).value
    sheet.update_cell(row, status_col, status)

def get_campground_status(url):
    """Gets campground status from the campground webpage"""
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    for i in soup.find_all('strong'):
        if 'Area Status: ' in i.contents:
            return i.next_sibling.strip()

def update_campground_status(sheet):
    for furl in FOREST_URLS:
        r = requests.get(furl)
        soup=BeautifulSoup(r.text, 'html.parser')
        campgrounds = []
        url_pref = 'https://www.fs.usda.gov'
        for i in soup.find_all(re.compile("h\d")):
            if 'Campground Camping Areas' in i.contents:
                for j in i.find_next_siblings('ul'):
                    for k in j.findAll('a'):
                        url = k.get('href')
                        if not url.endswith('.pdf') and url is not None:
                            url = url_pref + url
                            status = get_campground_status(url)
                            campname = k.getText().split(' Campground')[0]
                            update_sheet(sheet, campname, status)

def main():
    print 'opening sheet'
    sheet = open_camping_sheet(SHEET_KEY)
    print 'updating based on website'
    update_campground_status(sheet)
    
if __name__ == '__main__':
    main()