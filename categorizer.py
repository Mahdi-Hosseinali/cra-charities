import pandas as pd
import bs4cra as scraper
import requests
from urllib.parse import urlparse

# load_ext autoreload
# %autoreload 2

df = pd.read_csv('cra_charities_complete.csv', header=[0, 1])

urls = list(df[df.identity['Registration no'].isna()].url.url)
updated = []
for url in urls:
    updated.append(scraper.parse_page(url))

# Adding new data and cleaning the dataset
new_df = df.append(updated, ignore_index=True, sort=True)
new_df = new_df[~new_df.identity['Registration no'].isna()]
drops = [
    'SanctionNote this link will load in another window or tab',
    'Business/Registration number',
    "View this charity's quick view information"]
for d in drops:
    df.drop(('identity', d), axis=1, inplace=True, errors='ignore')

new_df.to_csv('cra_charities_complete.csv', index=False)

# Scraping the charity home pages
def url_curator(url):
    url = url.replace('https', '').replace('http','').replace('//', '')
    url = '.'.join(url.split())
    url = 'http://' + url
    return url

def url_validator(url):
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except:
        return False

def get_home_page(row):
    if row.homepage_text:
        print(f"{row['Registration no']} already parsed")
        return row.homepage_text
    url = row['Charity website address'].lower()
    if not url:
        print(f"{row['Registration no']} no Webpage")
        return ''
    print(f"{row['Registration no']} parsing")
    url = url_curator(url)
    if not url_validator(url):
        return ''
    soup = scraper.get_soup(url)
    if soup is None:
        print(f'Could not reach to {url}')
        return ''
    
    for script in soup(["script", "style"]):
        script.extract()
    return scraper.strip_extras(soup.get_text()).lower()

df = new_df
df[('identity', 'Charity website address')].fillna('', inplace=True)
df[('identity', 'homepage_text')] = ''
# df[('identity', 'homepage_text')] = df['identity'].apply(get_home_page, axis=1)
ans = df.iloc[:50]['identity'].apply(get_home_page, axis=1)
df.loc[:50, ('identity', 'homepage_text')] = ans
print(ans)

df.to_csv('cra_charities_url.csv', index=False)

# def tag_visible(element):
#     if element.parent.name in ['style', 'script', 'head', 'title', 'meta', '[document]']:
#         return False
#     if isinstance(element, Comment):
#         return False
#     return True
    
# def text_from_html(url):
#     soup = BeautifulSoup(requests.get(url).text, 'html.parser')
#     texts = soup.findAll(text=True)
#     visible_texts = filter(tag_visible, texts)  
#     return u" ".join(t.strip() for t in visible_texts)
