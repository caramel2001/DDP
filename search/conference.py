import pandas as pd
import requests
from bs4 import BeautifulSoup
from tqdm import tqdm
def get_conference_data(year=2021,path = 'data/conference.csv'):
    dfs = []
    for i in tqdm(range(1,21)):
        url = f'http://portal.core.edu.au/conf-ranks/?search=&by=all&source=CORE{year}&sort=aacronym&page={i}'
        df = pd.read_html(url)[0]

        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table')

        links = []
        for tr in table.findAll("tr")[1:]:
            trs = tr.findAll("td")
            flag = 1
            for each in trs:
                try:
                    link = each.find('a')['href']
                    flag=0
                    links.append(link)
                    break
                except:
                    pass
            if flag==1:
                links.append(None)

        df['DBLP'] = links
        df['DBLP'] = df['DBLP'].str.split("/").apply(lambda x :x[-1] if isinstance(x,list) else None)
        dfs.append(df)
    conf = pd.concat(dfs,axis=0)
    conf.to_csv(path)
    return conf

def get_conference_data_all(path = 'data/conference.csv'):
    dfs = []
    for i in tqdm(range(1,46)):
        url = f'http://portal.core.edu.au/conf-ranks/?search=&by=all&source=all&sort=atitle&page={i}'
        df = pd.read_html(url)[0]

        response = requests.get(url)
        soup = BeautifulSoup(response.text, 'html.parser')
        table = soup.find('table')

        links = []
        for tr in table.findAll("tr")[1:]:
            trs = tr.findAll("td")
            flag = 1
            for each in trs:
                try:
                    link = each.find('a')['href']
                    flag=0
                    links.append(link)
                    break
                except:
                    pass
            if flag==1:
                links.append(None)

        df['DBLP'] = links
        df['DBLP'] = df['DBLP'].str.split("/").apply(lambda x :x[-1] if isinstance(x,list) else None)
        dfs.append(df)
    conf = pd.concat(dfs,axis=0)
    conf.to_csv(path)
    return conf