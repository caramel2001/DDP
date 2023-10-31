import pandas as pd
import numpy as np
import requests
from bs4 import BeautifulSoup 
from typing import Optional
from tqdm import tqdm
from scholarly import scholarly
import pprint
from typing import Union,List
import xmltodict
import pymongo
import re
import http.cookies
import time 

NTU_KEYWORDS=['Nanyang Technological University, Singapore, Singapore',
 'NTU',
 'Nanyang Technological University (NTU), School of Computer Science and Engineering, Singapore',
 'SCSE',
 'Nanyang Technological University, Singapore (NTU)',
 'School of Computer Engineering, Nanyang Technological University, Singapore, Singapore',
 'Nanyang Technological University, School of Computer Engineering, Singapore',
 'Nanyang Technological University',
 'Nanyang Technological University, Singapore',
 'School of Computer Science and Engineering',
 'Nanyang Technological University, School of Computer Engineering']
# class ArvixClient:
#     """This client is to collect all publicly available papers of the Author and create a Graph connecting all Related Papers and extract Main Research Keywords from abstracts """

class GoogleScholarClient:
    def __init__(self):
        pass

    def get_data_from_name(self,name,sections=['basics', 'indices', 'coauthors'],verbose=False):
        search_query = scholarly.search_author(name)
        first_author_result = next(search_query)
        if verbose:pprint.pprint(first_author_result)
        # Retrieve all the details for the author
        author = scholarly.fill(first_author_result, sections=sections)
        if verbose:pprint.pprint(author)
        return author  
    
    def get_data_from_id(self,id,sections=['basics', 'indices', 'coauthors'],verbose=False):
        search_query = scholarly.search_author_id(id = str(id))
        search_query = scholarly.fill(search_query,sections=sections)
        if verbose:pprint.pprint(search_query)
        return search_query   
    
    def preprocess_data(self,author_result:List[dict])->pd.DataFrame:
        scholarly_df = pd.json_normalize(author_result,max_level=0)
        scholarly_df.drop(columns=['filled','source','url_picture'],inplace=True)
        return scholarly_df
        
    def check_correct_extraction(self,df:pd.DataFrame,DR_ntu_data:pd.DataFrame):
        # first check email domain
        df['check'] = df['email_domain'] == '@ntu.edu.sg'
        # second check : University Sanity check
        for index,row in df.iterrows():
            if row['check']:
                continue
            if not pd.isna(DR_ntu_data.loc[index,'google_scholar_id']) : # base check : if used google scholar ID from DR NTU Personal Page
                df.loc[index,'check']  = True
                continue
            if row['affiliation'] in NTU_KEYWORDS: # second check : University Sanity check
                df.loc[index,'check']  = True
                continue
            if not pd.isna(DR_ntu_data.loc[index,'personal_websites']) and not pd.isna(row['homepage']):
                if row['homepage'] in DR_ntu_data.loc[index,'personal_websites'] or DR_ntu_data.loc[index,'personal_websites'] in row['homepage']:# Third Check: Personal Website check
                    df.loc[index,'check']  = True
                
        return df['check']
    
    @staticmethod
    def transform_scopus_to_scholarly(data:list):
        """Function to transform the data extracted from Scopus to the format of Google Scholar"""
        temp={}
        temp['container_type'] = 'Scopus'
        temp['scopus']=True
        temp['scopus_id']=data[0]['data']['author']['id']
        temp['name'] = data[0]['data']['author']['profile']['preferredName']
        temp['affiliation'] = data[0]['data']['author']['profile']['currentInstitution']['name']
        temp['organization'] = data[0]['data']['author']['profile']['currentInstitution']['id']
        temp['hindex'] = data[1]['data']['author']['metrics']['hindex']
        temp['citedby'] = data[1]['data']['author']['metrics']['citedByCount']
        return temp

    @staticmethod
    def get_scopus_citations(id,cookie_str):
        """Function to get the Scopus citations for a professor using their Scopus ID"""
        cookie_dict = {v.key:v.value for v in http.cookies.SimpleCookie(cookie_str).values()}
        headers={"user-agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36","content-type":"application/json"}
        params={"query":"\n query author ($id: String!) {\n  author(id: $id) {\n    id\n    profile {\n      eid\n      orcId\n      preferredName\n      currentInstitution {\n        id\n        parent\n        name\n        city\n        country\n      }\n    }\n  }\n}\n","variables":{"id":str(id)}}
        response = requests.post("https://api.scopus.com/author-profile-api/author",json=params,headers = headers,cookies=cookie_dict).json()

        params= {"query":"\nquery authorMetrics ($id: String!) {\n  author(id: $id) {\n    metrics {\n      citationCount\n      citedByCount\n      coAuthorsCount\n      documentCount\n      hindex\n    }\n    funding {\n      awardedGrantsCount\n    }\n    preprints {\n      preprintCount\n    }\n  }\n}","variables":{"id":str(id)}}
        response_metrics = requests.post("https://api.scopus.com/author-profile-api/author",json=params,headers = headers,cookies=cookie_dict).json()
        data= GoogleScholarClient.transform_scopus_to_scholarly([response,response_metrics])
        return data
    

class DBLPCLient:
    def __init__(self):
        self.search_author ="https://dblp.org/search/author/api"
        self.search_author_orcid ="https://dblp.org/search/author/inc"
        self.orcid_url = "https://dblp.org/search/publ/api"
        self.svg_url = "https://dblp.org/search/yt/svg"
        self.headers = {"user-agent":"Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/116.0.0.0 Safari/537.36"}

    def transform_data(self,data):
        """This function transforms the Data extracted from DBLP into more JSON friendly format"""
        # Define a mapping of DBLP entry types
        type_mapping = {
            'article': 'journal_article',
            'inproceedings': 'conference_paper',
            'proceedings': 'conference_proceedings',
            'book': 'book',
            'incollection': 'book_chapter',
            'phdthesis': 'phd_thesis',
            'mastersthesis': 'masters_thesis',
        }


        # Function to add 'type' key-value pair
        def add_type_to_item(item):
            item_type = next(iter(item.keys()))  # Get the article type
            item_data = item[item_type]
            item_data['type'] = type_mapping.get(item_type, 'unknown')  # Add 'type' key
            return item_data

        # Transform the data
        transformed_data = [add_type_to_item(item) for item in data]
        return transformed_data
    
    def get_author(self,name,orcid=None,h=1):
        """Function to get DBLP data for a professor name/orcid using their search API"""

        if orcid:
            orcid = orcid.split("/")[-1]
            print("getting data using ORCID")
            params= {
                    "eid":f"ORCID:{orcid}",
                    "h":1,
                }
            response = requests.get(self.search_author_orcid,params=params,headers=self.headers)
            if response.status_code ==429: # too many requests
                print("Sleeping for 60 seconds")
                time.sleep(60)
                print(response.status_code)
            response = requests.get(self.search_author_orcid,params=params,headers=self.headers)
            soup = BeautifulSoup(response.text,'html.parser')
            data =self.get_data_from_orchid(soup)
            if data is not None:
                return data
        params= {
            "q":name,
            "h":h,
            'format':'json',
            'compl':'score'
        }
        response = requests.get(self.search_author,params=params,headers=self.headers)
        if response.status_code ==429: # too many requests
            print("Sleeping for 60 seconds")
            time.sleep(60)
            response = requests.get(self.search_author,params=params,headers=self.headers)
            print(response.status_code)
        try:
            data = response.json()
            return data['result']['hits']
        except requests.JSONDecodeError as e : # response is not a JSON readable
            return None
    
    @staticmethod
    def get_data_from_orchid(soup:BeautifulSoup):
        """Function to get the data of a professor from DBLP when queries using ORCID Search"""
        if soup.find('ul',class_='result-list').find('li'):
            name = soup.find('ul',class_='result-list').find('li').text.strip()
            page = soup.find('ul',class_='result-list').find('li').a['href']
        else:
            return None
        return {'hit': [{'@score': '-1', # score -1 means a perfect match
                '@id': None,
                'info': {'author': name,
                    'aliases':None,
                    'notes': None,
                    'url': page
                    },
                'url': None}]}


    def get_dblb_data(self,names:Union[List,pd.Series],orcids:Union[List,pd.Series],h=1)->pd.DataFrame:
        """Function to get DBLP data for a list of professor names"""
        responses = []
        for name,orcid in tqdm(zip(names,orcids)):
            if pd.isna(orcid):
                result = self.get_author(name=name,h=1)
                responses.append(result)
            else:
                result = self.get_author(name=name,orcid=orcid,h=1)
                responses.append(result)
        self.response = responses
        df = pd.json_normalize([i if (i is not None) and ('hit' in i) else None for i in responses])['hit']
        # extract data from json record path 'hit using pandas json_noramlize method and handle exceptions case of no hits from DBLB search 
        DBLB_data = pd.concat(df.apply(lambda x : pd.json_normalize(x[0]) if not pd.isna(x) else pd.DataFrame({"url":None},index=[0])).to_list())
        DBLB_data.reset_index(inplace=True,drop=True)
        DBLB_data.index.name='profID'
        DBLB_data.rename(columns={'info.url':'page_url','info.author':'author'},inplace=True)
        return DBLB_data
    
    def store_dblp_data(self,url,prof_id,collection:Optional[pymongo.collection.Collection]=None):
        """Function to store DBLP data in MongoDB for a professor's Research Papers and meta info"""
        if pd.isna(url): # do DBLP URL found from search
            print(f'DBLP data for Professor {prof_id} not present.')
            # insert a empty dict with prof_id as key
            parsed_data={'profID':prof_id}
            if collection:
                collection.insert_one(parsed_data)
            return parsed_data
        
        dblp_xml_data = self.get_data(url)
        # Parse the XML data
        parsed_data = xmltodict.parse(dblp_xml_data)
        parsed_data = parsed_data['dblpperson']
        # Add the professor's ID to the parsed data
        parsed_data['profID'] = prof_id
        if collection:
            # Insert the data into MongoDB
            collection.insert_one(parsed_data)
            print(f'DBLP data for Professor {prof_id} stored in MongoDB.')
        return parsed_data
    
    def get_json_dblp_data(self,url,prof_id):
        """Function to get JSON DBLP data for a professor's Research Papers and meta info"""
        data=[]
        if pd.isna(url): # do DBLP URL found from search
            print(f'DBLP data for Professor {prof_id} not present.')
            # insert a empty dict with prof_id as key
            parsed_data={'profID':prof_id}
            data.append(parsed_data)
            return
        
        dblp_xml_data = self.get_data(url)
        # Parse the XML data
        parsed_data = xmltodict.parse(dblp_xml_data)
        parsed_data = parsed_data['dblpperson']
        # Add the professor's ID to the parsed data
        parsed_data['profID'] = prof_id

        data.append(parsed_data)

        return  data
    
    def retrieve_dblp_data(self,prof_id,collection:pymongo.collection.Collection):
        """Function to retrieve DBLP data for a professor based on prof_id"""
        data = collection.find_one({'profID': prof_id})
        return data

    def get_data(self,url):
        """Function to get the XML data from DBLP"""
        response = requests.get(f"{url}.xml",headers=self.headers)
        if response.status_code == 429:
            print("Sleeping for 60 seconds")
            time.sleep(60)
            response = requests.get(f"{url}.xml",headers=self.headers)

        return response.text

    def get_orcid(self,name,dblp_id):
        """Function to get the ORCID of a professor from DBLP"""
        if pd.isna(name):
            return None
        name=name.replace(" ","_")
        params= {
            "q":f"author:{name}:",
            "h":1,
            'format':'json',
            'compl':f'orcid:{dblp_id}'
        }
        response = requests.get(self.orcid_url,params=params)
        if response.status_code ==429: # too many requests
            print("Sleeping for 60 seconds")
            time.sleep(60)
            response = requests.get(self.orcid_url,params=params)
            print(response.status_code)
        response=response.json()
        try:
            completions = response['result']['completions']['c']
            if completions is None:
                return ""
            if not isinstance(response['result']['completions']['c'],list):
                if completions['text'].split(":")[-1]!='no_orcid':
                    return completions['text'].split(":")[-1]
                else:
                    return ""
            for c in completions:
                if c['text'].split(":")[-1]!='no_orcid':
                    return c['text'].split(":")[-1]
        except KeyError:
            return ""
        return ""
        
    def get_svg_citations(self,name:str):
        """Function to get the SVG element for the citations graph of a professor from DBLP"""
        if pd.isna(name):
            return None
        name=name.replace(" ","_")
        params= {
            "q":f"author:{name}:",
        }
        response = requests.get(self.svg_url,params=params)
        if response.status_code ==429: # too many requests
            print("Sleeping for 60 seconds")
            time.sleep(60)
            response = requests.get(self.svg_url,params=params)
            print(response.status_code)
        # response=response.json()
        xml_text = response.text
        soup = BeautifulSoup(xml_text, "xml")
        svg_element =soup.find('svg')
        # Check if the SVG element is found
        if svg_element is not None:
            # Convert the SVG element back to a string
            svg_string = str(svg_element)
            return svg_string
        else:
            return None


class DrNTUClient:
    def __init__(self):
        self.search_url = "https://dr.ntu.edu.sg/simple-search"
        self.base_url = "https://dr.ntu.edu.sg"

    def get_profile_links_data(self,schoolId:Optional[str]=None):
        """Extract URL of profiles for each Researcher in NTU from DR NTU website using the simple-search API

        Args:
            schoolId (Optional[str], optional): School ID from jquery of the website. Example ou00030 for SCSE. Defaults to None then we extract all research profiles

        Returns:
            pd.DataFrame
        """
        if schoolId:
            params = {"filterquery":schoolId,
            "filtername": "school",
            "filtertype": "authority",
            "location": "researcherprofiles",
            "sort_by": "bi_sort_4_sort",
            "rpp": 50,
            "etal": 0,
            "start": 0, # this parameter represents the offset to performing indexing of page
            "order": "ASC"}
        else:
            params = {
            "location": "researcherprofiles",
            "sort_by": "bi_sort_4_sort",
            "rpp": 50,
            "etal": 0,
            "start": 0, # this parameter represents the offset to performing indexing of page
            "order": "ASC"}
        datas=[]
        response =requests.get(self.search_url,params=params)
        # text of the second last button and last button is next button
        number_of_pages = int(BeautifulSoup(response.text,'html.parser').find('ul',attrs={'class':'pagination pull-right'}).find_all('li')[-2].text)
        for i in range(number_of_pages):
            params['start'] = i*50
            response =requests.get(self.search_url,params=params)
            # here we are finding the profile links using BeautifulSoup and we remove first element
            # because the first element is the link of the Header of the table
            profile_links = [i['href'] for i in BeautifulSoup(response.text,'html.parser').find_all("table")[0].find_all("a", href=True)[1:]]
            table = pd.read_html(response.text)[0]
            table['profile_link'] = profile_links
            datas.append(table)
        return pd.concat(datas).reset_index()
    
    def get_data_from_a_profile(self,profile_url,publication=False)->dict:
        """For each profile URL form DR NTU extracts research_keywords,biography,researchinterests,current_projects,personal_websites

        Args:
            profile_url (_type_): DR NTU personal website URL

        Returns:
            dict
        """
        response = requests.get(profile_url)
        response.raise_for_status()
        soup = BeautifulSoup(response.text,'html.parser')
        research_keywords = self.get_research_keywords(soup)
        biography = soup.find('div',attrs={'id':'biographyDiv'}).text.strip() if soup.find('div',attrs={'id':'biographyDiv'}) else ""
        researchinterests = soup.find('div',attrs={'id':'researchinterestsDiv'}).text.strip() if soup.find('div',attrs={'id':'researchinterestsDiv'}) else ""
        current_projects = self.get_current_projects(soup)
        personal_websites =self.get_personal_website(soup)
        email = soup.find('div', id="emailDiv").text.strip() if soup.find('div', id="emailDiv") else ""
        orcid = self.get_orcid(soup)
        # getting bibliometrics (google scholar url and scopus url)
        link = soup.find('li',attrs={'data-tabname':'selectedPublications'}).find('a')['href']
        response = requests.get(f'https://dr.ntu.edu.sg/{link}')
        soup = BeautifulSoup(response.text,'html.parser')
        bilbliometrics = soup.find('div',attrs={'id':'custombiblio'})
        google_scholar = bilbliometrics.find('div',attrs={'id':'googlescholarlinkDiv'}) if bilbliometrics else None
        google_scholar =  google_scholar.find('a')['href'] if google_scholar else None
        scopus = bilbliometrics.find('div',attrs={'id':'scopuslinkDiv'}) if bilbliometrics else None
        scopus =  scopus.find('a')['href'] if scopus else None
        data = {'research_keywords':research_keywords,'biography':biography,'researchinterests':researchinterests,'current_projects':current_projects,'personal_websites':personal_websites,'email':email,'orcid':orcid,'google_scholar':google_scholar,'scopus':scopus}

        # getting journal articles 
        if publication:
            publication = self.get_publication_data(soup)
            data.update(publication)

        return data

    def get_all_data_profs(self,publication=False,**kwargs)->pd.DataFrame:
        """Iterative function that extracts all profile links from Search Page and collects data from each page

            **kwargs : Additonal Keyword arguements for get_profile_links_data method such as school filter
        Returns:
            pd.DataFrame: _description_
        """
        profiles_df = self.get_profile_links_data(**kwargs)
        result=[]
        for link in tqdm(profiles_df['profile_link']):
            if pd.isna(link):# if link was not retireved or null
                result.append({})
                continue
            result.append(self.get_data_from_a_profile(profile_url=f'{self.base_url}{link}',publication=publication))
        return pd.concat([profiles_df,pd.DataFrame(result)],axis=1)
    
    @staticmethod
    def extract_scholar_user_id(url):
        """Function to extract the user ID from the Google Scholar URL using Regular Expressions"""
        if url is None:
            return None
        # Regular expression pattern to extract the user ID
        pattern = r'user=([A-Za-z0-9_-]+)'
        match = re.search(pattern, url)
        if match:
            user_id = match.group(1)
            return user_id
        else:
            return None
    
    @staticmethod
    def extract_scopus_ids(url):
        if pd.isna(url):
            return None
        match = re.search(r'authorId=(\d+)', url)
        author_id=None
        if match:
            author_id = match.group(1)
        return author_id
    # methods to extract element from Soup while performing sanity checks
    @staticmethod
    def get_current_projects(soup:BeautifulSoup):
        """Function to extract the current projects from the profile page of a professor"""
        element = soup.find('div',attrs={'id':'collapseOnecurrentprojects'})
        if element:
            return [i.text.strip() for i in element.find_all('li')]
        else:# no current projects element 
            return []
    @staticmethod
    def get_research_keywords(soup:BeautifulSoup):
        """Function to extract the research keywords from the profile page of a professor"""
        element = soup.find('div',attrs={'id':'researchkeywords'})
        if element:
            return [i.text.strip() for i in element.find_all('a')]
        else:# no current projects element 
            return []
    @staticmethod
    def get_personal_website(soup:BeautifulSoup):
        """Function to extract the personal website from the profile page of a professor"""
        element = soup.find('div',attrs={'id':'personalsiteDiv'})
        if element and 'website' in element.find('a').text.strip().lower():
            return element.find('a')['href']
        else:# no current projects element 
            return ""     
   
    @staticmethod
    def get_publication_data(soup:BeautifulSoup):
        """Function to extract the publication and conference data from the profile page of a professor"""
        publication = soup.find('div',attrs={'id':'facultyjournalDiv'})
        conference = soup.find('div',attrs={'id':'facultyconfDiv'})
        publication = publication.text.strip() if publication else None
        conference = conference.text.strip() if conference else None
        
        # In DR NTU the format of Publication is very inconsistent and hence we are not extracting it as a list rather a chucnk of text. This will help us check validity of data extrcated from Google Scholar and DBLP.
        return {'publication':publication,'conference':conference}
        
   
    @staticmethod
    def get_orcid(soup:BeautifulSoup):
        """Function to extract the ORCID from the profile page of a professor"""
        element = soup.find('div',attrs={'id':'personalsiteDiv'})

        if element and len(element.find_all('a')) == 2 and element.find_all('a')[1].text.strip() == 'ORCID':
            return element.find_all('a')[1]['href']
        else:# no current projects element 
            return ""