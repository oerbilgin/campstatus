from bs4 import BeautifulSoup
import update_campstatus as uc
import requests
import re
import pandas as pd

URLS = {
    'Stanislaus': 'https://www.fs.usda.gov/activity/stanislaus/recreation/camping-cabins/?recid=14833&actid=29',
    'Tahoe': 'https://www.fs.usda.gov/activity/tahoe/recreation/camping-cabins/?recid=55444&actid=29',
    'El Dorado': 'https://www.fs.usda.gov/activity/eldorado/recreation/camping-cabins/?recid=71008&actid=29'
}

def get_campground_urls(forest_url):
    r = requests.get(forest_url)
    soup = BeautifulSoup(r.text, 'html.parser')
    urls = []
    url_pref = 'https://www.fs.usda.gov'
    for i in soup.find_all(re.compile("h\d")):
        if 'Campground Camping Areas' in i.contents:
            for j in i.find_next_siblings('ul'):
                for k in j.findAll('a'):
                    url = k.get('href')
                    s = k.contents[0].string
                    if s is not None:
                        if s.endswith('Campground'):
                            if not url.endswith('.pdf') and url is not None:
                                url = url_pref + url
                                urls.append([s, url])
    return urls

def get_campground_data(url):
    r = requests.get(url)
    soup=BeautifulSoup(r.text, 'html.parser')
    table_data = {}
    for i in soup.find_all(re.compile("h\d")):
        if 'At a Glance' in i.contents:
            for j in i.find_next_siblings('div'):
                for k in j.findChildren('tr'):
                    header = k.find('th').string.replace(':', '')
                    content = k.find('td').get_text().replace(u'\xa0', '').strip()
                    if table_data.get(header) is None:
                        table_data[header] = [content]
                    else:
                        table_data[header].append(content)
    status = uc.get_campground_status(url)
    table_data['Status'] = status
    table_data['URL'] = url
    return pd.DataFrame(table_data)

def scrape_campsite_data(urls):
    rows = []
    for campground, camp_url in urls:
        data = get_campground_data(camp_url)
        data['Campground'] = campground
        rows.append(data)
    df = pd.concat(rows).reset_index(drop=True)
    return df

def munge_reservations(cell):
    if pd.isnull(cell):
        return ''
    fcfs = False
    res = False
    seasonal = False
    if re.match('(?i).*first.{1,4}come.{1,4}first.{1,4}serve', cell) is not None:
        fcfs = True
    elif 'no reservations' in cell.lower():
        fcfs = True
    elif cell.lower() in ['no','none.']:
        fcfs = True
        
    if 'for reservations' in cell.lower():
        res = True
    elif 'recreation.gov' in cell.lower():
        res = True
    elif cell.lower()[:3] == 'yes':
        res = True
    elif cell.lower() in ['recreation.pge.com',]:
        res = True
    
    if 'winter' in cell.lower() or 'summer' in cell.lower():
        seasonal = True
    
    if seasonal:
        return 'seasonal'
    
    if fcfs and res:
        return 'both'
    elif fcfs:
        return 'fcfs'
    elif res:
        return 'reservations only'
    else:
        print cell
        return cell

def munge_fees(cell):
    if pd.isnull(cell):
        return ''
    fees = re.findall('\$\d+\.{0,1}\d*', cell)
    if len(fees) == 0:
        if 'no fee' in cell.lower():
            fee = '$0'
        elif 'donation' in cell.lower():
            fee = '$0'
        elif cell.lower() in ['free', 'none']:
            fee = '$0'
        else:
            fee = cell
            print cell
    else:
        fee = fees[0]
    
    return fee

def munge_water(cell):
    if pd.isnull(cell):
        return ''
    water = False
    if cell.lower() == 'potable':
        water =  True
    elif 'is available' in cell.lower() and 'untreated' not in cell.lower():
        water = True
    elif 'piped water' in cell.lower():
        water = True
    elif cell.lower() in ['potable water', 'yes']:
        water = True

    return water

def munge_restrooms(cell):
    if pd.isnull(cell):
        return ''
    vault = False
    flush = False
    if 'vault' in cell.lower():
        vault = True
    elif cell.lower() in ['yes']:
        vault=True
    
    if 'flush' in cell.lower():
        flush = True
    
    if vault and flush:
        restroom = 'Both'
    elif vault:
        restroom = 'Vault'
    elif flush:
        restroom = 'Flush'
    elif cell.lower() == 'no':
        restroom = 'None'
    else:
        restroom = cell
        print cell
        
    return restroom

def munge_campground_data(df):
    print 'Munging reservations...'
    df.loc[:, 'Reservations'] = df['Reservations'].apply(munge_reservations)
    print 'Munging fees...'
    df.loc[:, 'Fees'] = df['Fees'].apply(munge_fees)
    print 'Munging water...'
    df.loc[:, 'Potable Water'] = df['Water'].apply(munge_water)
    print 'Munging restrooms...'
    df.loc[:, 'Restroom'] = df['Restroom'].apply(munge_restrooms)
    df.fillna('', inplace=True)
    columns = [
        'Campground',
        'Status',
        'Fees',
        'Open Season',
        'Reservations',
        'Restroom',
        'Potable Water',
        'Usage',
        'Water',
        'URL'
        ]
    return df[columns]

if __name__ == '__main__':
    collect = []
    for forest, url in URLS.iteritems():
        print 'scraping {} National Forest'.format(forest)
        urls = get_campground_urls(url)
        df = scrape_campsite_data(urls)
        df = munge_campground_data(df)
        df.loc[:, 'Forest'] = forest
        collect.append(df)
    final = pd.concat(collect)
    final.to_csv('./scraped_campgrounds.csv', index=False)

