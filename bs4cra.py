from bs4 import BeautifulSoup
import requests
import re
import pandas as pd
import sys
import time
from urllib.parse import parse_qs, urlsplit

failed = 0
root = 'https://apps.cra-arc.gc.ca'
ref_pages = 'advncdSrch?q.stts=0007&q.cty=Aylmer&q.ordrClmn=NAME&q.ordrRnk=ASC&dsrdPg=1'
hdr = {'User-Agent': 'Mozilla/5.0'}

def get_soup(url):
    global failed
    try:
        sauce = requests.get(url, headers=hdr)
    except :
        return None
    if sauce.status_code != 200:
        print(f'Bad response ({sauce.status_code} from {url}')
        failed += 1
        return None
    soup = BeautifulSoup(sauce.text, 'html.parser')
    return soup

def get_links(url):
    soup = get_soup(url)
    if soup:
        links = set(root+i['href'] for i in soup.find_all('a', href=True) if '/ebci/hacc/srch/pub' in i['href'])
        return links
    else:
        return []

def strip_extras(string):
    return re.sub(r"[\s.:]+", ' ', string).strip()

def get_rows(soup, pref):
    tags = soup.find_all(class_='col-xs-12 col-sm-6 col-md-6 col-lg-3')
    return {(pref, strip_extras(i.text)):strip_extras(i.find_next().text) for i in tags}

def get_finance(soup, pref):
    lines = [re.sub('<[^<]+?>', '', i.text) for i in soup.find_all('th') if '$' in i.text]
    ans = dict()
    for l in lines:
        i = l.split('$')
        value = i[1].split('(')[0].replace(',', '')
        ans[(pref, i[0].strip())] = float(value)
    lines = [i.text for i in soup.find_all(class_='h5 mrgn-lft-md mrgn-tp-md')]
    for l in lines:
        i = l.split('$')
        ans[(pref, strip_extras(i[0]))] = float(i[1].replace(',',''))

    return ans

def parse_page(url):
    ''' Extracts the following data:
    Link
    Identity
        registration no, charity status, effective date, address, city, province, territory, postal code, website, email
    Type
        designation, charity type, category, program and activities
    Revenue
        receipted donations, non-receipted donations, gift from other, government funding, all other, total
    '''
    ans = {('url','url'):url}
    soup = get_soup(url)
    if soup:
        ans.update(get_rows(soup, 'identity'))
        if 'Quick View' in soup.h1.text:
            ans[('identity', 'name')] = soup.h1.text.replace(' — Quick View', '')
            detail_soup = get_soup(root + soup.h1.find_next('a')['href'])
            ans.update(get_rows(detail_soup, 'identity'))
        elif soup.h1.text == 'Detail page':
            ans[('identity', 'name')] = strip_extras(soup.findAll('h2', class_='h3')[0].text)
            ans[('identity', 'Registration no')] = ans[('identity', 'Business/Registration number')]
            del ans[('identity', 'Business/Registration number')]
        else:
            print('Could not find charity name for: ', url)
        ans.update(get_finance(soup, 'financials'))
        
    return ans

def save_result(data, adrs):
    df = pd.DataFrame(data)
    df.columns = pd.MultiIndex.from_tuples(df.columns)
    drops = [
        'SanctionNote this link will load in another window or tab',
        'Business/Registration number',
        "View this charity's quick view information"]
    for d in drops:
        df.drop(('identity', d), axis=1, inplace=True, erros='ignore')
    print('writing to file')
    df.to_csv(adrs, index=False, encoding='utf-8')
    print('done')

if __name__ == '__main__':
    urls = [
        'https://apps.cra-arc.gc.ca/ebci/hacc/srch/pub/advncdSrch?q.stts=0007&q.cty=ottawa&q.ordrClmn=NAME&q.ordrRnk=ASC&dsrdPg=1',
        'https://apps.cra-arc.gc.ca/ebci/hacc/srch/pub/advncdSrch?q.stts=0007&q.cty=gatineau&q.ordrClmn=NAME&q.ordrRnk=ASC&dsrdPg=1',
        'https://apps.cra-arc.gc.ca/ebci/hacc/srch/pub/advncdSrch?q.stts=0007&q.cty=orleans&q.ordrClmn=NAME&q.ordrRnk=ASC&dsrdPg=1',
        'https://apps.cra-arc.gc.ca/ebci/hacc/srch/pub/advncdSrch?q.stts=0007&q.cty=kanata&q.ordrClmn=NAME&q.ordrRnk=ASC&dsrdPg=1',
        'https://apps.cra-arc.gc.ca/ebci/hacc/srch/pub/advncdSrch?q.stts=0007&q.cty=Aylmer&q.ordrClmn=NAME&q.ordrRnk=ASC&dsrdPg=1',
        'https://apps.cra-arc.gc.ca/ebci/hacc/srch/pub/advncdSrch?q.stts=0007&q.cty=Nepean&q.ordrClmn=NAME&q.ordrRnk=ASC&dsrdPg=1',
    ]
    parsed_urls = set()
    parsed_charities = set()
    ans = []
    cnt = 0
    max_parse = sys.maxsize
    # max_parse = 10
    skipped = 0

    while urls and cnt < max_parse:
        url = urls.pop()
        if url in parsed_urls:
            skipped += 1
            continue
        if skipped>0:
            print(f'Skipped {skipped} repetitive url(s)')
        skipped = 0
        parsed_urls.add(url)

        qs = parse_qs(urlsplit(url).query)

        # Move to next pages
        if ('advncdSrch' in url and 
                parse_qs(urlsplit(ref_pages).query).keys() == qs.keys()):
            urls.extend(get_links(url))
            print(f'Expanding on: ({len(urls)}) {url}')
        elif 'dsplyRprtngPrd' in url and qs['selectedCharityBn'][0] not in parsed_charities:
            cnt += 1
            parsed_charities.add(qs['selectedCharityBn'][0])
            print(cnt, 'Parsing: ', url)
            res = parse_page(url)
            ans.append(res)
            time.sleep(1.5)
        
        if cnt%10==0:
            sys.stdout.flush()
        
        if failed >= 10:
            print('Too many failures, stopping the code')
            break
    
    print(f'{cnt} charities parsed')
    save_result(ans, 'cra_charities.csv')
