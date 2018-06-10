"""Summary

Attributes:
    url_pref (str): prefix for the forest service

"""
from bs4 import BeautifulSoup
import update_campstatus as uc
import requests
import re
import pandas as pd
import config

url_pref = 'https://www.fs.usda.gov'

def get_campground_urls(forest_url):
    """Retrieves all the urls for campgrounds in a national forest.
    
    Args:
        forest_url (str): URL to the camping-cabins page of the NFS site
    
    Returns:
        list(list(str, )): with the inner list's first element being
            the campground name, and the second element being the URL
            for the campground.
    
    See Also:
        * :func:`scrape_all_forests`

    """
    r = requests.get(forest_url)
    soup = BeautifulSoup(r.text, 'html.parser')
    urls = []
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

def find_tag_containing_text(tag, text):
    """BeautifulSoup find_all function to find tags that contain a text pattern
    
    Since find_all does not take any args, it must be wrapped with
    another function so that the text pattern can be passed.
    
    Args:
        tag (bs4.element.tag): Tag from BeautifulSoup parsed HTML site.
        text (str): text to search a tag's elements for. Case insensitive.
    
    Returns:
        bool: True when the text was found in the tag's contents, False
            if not.
    
    See Also:
        * :func:`find_elevation_div`
        * :func:`find_latitude_div`
        * :func:`find_longitude_tag`

    """
    result = False
    for x in tag.contents:
        try:
            if text.lower() in x.lower():
                result = True
        except:
            pass
    return result

def find_campground_a(tag):
    """Helper to find tags about campgrounds.
    
    Args:
        tag (bs4.element.tag): Tag from BeautifulSoup parsed HTML site.
    
    Returns:
        bool: True when the text 'Campground Camping' was found in the tag's contents,
            False if not.

    See Also:
        * :func:`find_value`
    """
    return find_tag_containing_text(tag, 'Campground Camping')

def find_elevation_div(tag):
    """Helper to find tags about elevation.
    
    Args:
        tag (bs4.element.tag): Tag from BeautifulSoup parsed HTML site.
    
    Returns:
        bool: True when the text 'elevation' was found in the tag's contents,
            False if not.

    See Also:
        * :func:`find_value`
    """
    return find_tag_containing_text(tag, 'elevation :')

def find_latitude_div(tag):
    """Helper to find tags about elevation.
    
    Args:
        tag (bs4.element.tag): Tag from BeautifulSoup parsed HTML site.
    
    Returns:
        bool: True when the text 'latitude' was found in the tag's contents,
            False if not.

    See Also:
        * :func:`find_value`
    """
    return find_tag_containing_text(tag, 'latitude :')

def find_longitude_tag(tag):
    """Helper to find tags about elevation.
    
    Args:
        tag (bs4.element.tag): Tag from BeautifulSoup parsed HTML site.
    
    Returns:
        bool: True when the text 'longitude' was found in the tag's contents,
            False if not.

    See Also:
        * :func:`find_value`
    """
    return find_tag_containing_text(tag, 'longitude :') 

def find_value(soup, tag_function):
    """Gets the value in the element after the first found tag.

    This is used to scrape the table in the campground's side bar that
    contains elevation, latitude, and longitude data. These data are
    in divs, not an HTML table. For example, the data for elevation is
    in the div after the div that contains the text "elevation". This
    function finds the first tag containing certain text, then returns
    the contents of the first sibling after that element.
    
    Args:
        soup (bs4.BeautifulSoup): Parsed HTML text of campground website.
        tag_function (func): function to find tags whose contents
            contain the desired text.
    
    Returns:
        str: Contents of the element after the tag that contains the
            searched-for text.

    Examples:
        >>> find_value(soup, find_elevation_tag)
        '5,000 ft'
    
    See Also:
        * :func:`get_campground_data`
    """
    tag = soup.find_all(tag_function)[0]
    val = tag.findNextSiblings()[0].text.strip()
    return val

def get_campground_data(url):
    """Scrapes all the desired data for a campground.

    Collects all of the data in the "At a Glance" section of the
    campground webpage, and elevation, longitude, and latitude on the
    side of the webpage and stores it in a dictionary. The dictionary
    is then converted to a pandas.DataFrame, which will eventually be
    a row in the final table.
    
    Args:
        url (str): URL to the campground webpage.
    
    Returns:
        pandas.DataFrame: single-row table with columns of all the
            data that was scraped.

    See Also:
        * :func:`scrape_campsite_data`
    """
    # parse the html
    r = requests.get(url)
    soup=BeautifulSoup(r.text, 'html.parser')

    # get the 'at a glance' table data
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

    # get the data from the sidebar
    side_div_funcs = {
    'Elevation': find_elevation_div,
    'Longitude': find_longitude_tag,
    'Latitude': find_latitude_div,
    }
    for label, tag_func in side_div_funcs.iteritems():
        try:
            val = find_value(soup, tag_func)
        except Exception as e:
            val = pd.np.nan
        table_data[label] = val

    # get the open/closed status
    status = uc.get_campground_status(url)
    table_data['Status'] = status
    table_data['URL'] = url
    return pd.DataFrame(table_data)

def scrape_campsite_data(urls):
    """Creates a table of campground data given a list of campground URLs.
    
    Args:
        urls (list(str, )): list of URLs pointing to campground webpages
    
    Returns:
        pandas.DataFrame: Table of all the aggregated data from all
            the campgrounds pointed to by `urls`. Each row is one
            campground.

    See Also:
        * :func:`scrape_all_forests`
    """
    rows = []
    for campground, camp_url in urls:
        data = get_campground_data(camp_url)
        data['Campground'] = campground
        rows.append(data)
    df = pd.concat(rows).reset_index(drop=True)
    return df

def munge_reservations(cell):
    """Summary
    
    Args:
        cell (TYPE): Description
    
    Returns:
        TYPE: Description
    """
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
    """Summary
    
    Args:
        cell (TYPE): Description
    
    Returns:
        TYPE: Description
    """
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
    """Summary
    
    Args:
        cell (TYPE): Description
    
    Returns:
        TYPE: Description
    """
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
    """Summary
    
    Args:
        cell (TYPE): Description
    
    Returns:
        TYPE: Description
    """
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

def munge_elevation(cell):
    """Summary
    
    Args:
        cell (TYPE): Description
    
    Returns:
        TYPE: Description
    """
    if pd.isnull(cell):
        return ''
    elif cell == '':
        return ''
    else:
        elev_str = ''.join(re.findall('\d*', cell))
        try:
            elev_int = int(elev_str)
        except:
            print cell
            elev_int = '???'
    return elev_int

def munge_campground_data(df):
    """Summary
    
    Args:
        df (TYPE): Description
    
    Returns:
        TYPE: Description
    """
    # 'Munging reservations...'
    df.loc[:, 'Reservations'] = df['Reservations'].apply(munge_reservations)
    # 'Munging fees...'
    df.loc[:, 'Fees'] = df['Fees'].apply(munge_fees)
    # 'Munging water...'
    df.loc[:, 'Potable Water'] = df['Water'].apply(munge_water)
    # 'Munging restrooms...'
    df.loc[:, 'Restroom'] = df['Restroom'].apply(munge_restrooms)
    # 'Munging elevation...'
    df.loc[:, 'Elevation'] = df['Elevation'].apply(munge_elevation)

    df.fillna('', inplace=True)

    # empty dataframe containing all the desired columns
    coltable = pd.DataFrame(columns=config.campgrounds_final_table_columns)
    df = pd.concat([coltable, df])

    return df[config.campgrounds_final_table_columns]

def get_forest_rec_url(forest_name, recreation_type='camping-cabins'):
    """Retrieves the url for the website listing all the campgrounds
    or trailheads.

    The output of this function can be piped directly to scrape_all_forests()
    
    Args:
        forest_names (list(str, )): List of strings of the names of
            the national forests that you want to scrape. Not case
            sensitive, but must match what is in the config file lookup
        recreation_type (str, optional): either camping-cabins or hiking
    
    Returns:
        dict: key is the forest_name and value is url pointing to the
            main page that contains links to each campground or hiking
            trail in the forest.
    
    """
    url = (
        'https://www.fs.usda.gov/activity/{}/recreation/{}'
        .format(forest_name, recreation_type))
    r = requests.get(url)
    soup = BeautifulSoup(r.text, 'html.parser')
    tag = soup.find_all(find_campground_a)[0]

    if tag.get('href') is None:
        tag = tag.findParent('a')
    suffix = tag.get('href')
    url = url_pref + suffix
    return url

def scrape_all_forests(URLS):
    """Summary
    
    Args:
        URLS (TYPE): Description
    
    Returns:
        TYPE: Description
    """
    collect = []
    for forest, url in URLS.iteritems():
        print 'scraping {} National Forest'.format(forest)
        urls = get_campground_urls(url)
        df = scrape_campsite_data(urls)
        df = munge_campground_data(df)
        df.loc[:, 'Forest'] = forest
        collect.append(df)
    final = pd.concat(collect)
    return final

def main():
    # make the forest urls
    forest_urls = {}
    for forest in config.forests_to_scrape:
        full_name = config.AllNationalForests[forest]
        url = get_forest_rec_url(forest)
        forest_urls[full_name] = url
    print 'These forests will be scraped:'
    print forest_urls.keys()
    print
    final = scrape_all_forests(forest_urls)
    final.to_csv('./scraped_campgrounds.csv', index=False)

if __name__ == '__main__':
    main()

