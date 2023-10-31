import pandas as pd
import streamlit as st
def transform_data(data):
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

@st.cache_data
def read_pubs_data(path):
    pubs= []
    data = pd.read_json(path)
    # print(data.head())
    for i in data['publication_json'].to_list():
        # print(type(i))
        if isinstance(i,list):
            pubs.extend(i)
            continue
        if pd.isna(i):
            continue
        pubs.extend(i)
    return transform_data(pubs)

@st.cache_data
def read_pubs_data_by_prof(path,profid):
    pubs= []
    data = pd.read_json(path)
    data = data['publication_json'].iloc[profid]
    if data is None:
        return data
    return transform_data(data)

@st.cache_data
def read_pubs_data_by_profs(path,profids):
    pubs= []
    data = pd.read_json(path)
    data = data.iloc[profids]
    for i in data['publication_json'].to_list():
        # print(type(i))
        if isinstance(i,list):
            pubs.extend(i)
            continue
        if pd.isna(i):
            continue
        pubs.extend(i)
    return transform_data(pubs)


def extract_titles(data):
    titles=[]
    for i in data:
        title = i['title']
        if isinstance(title,dict):
            title = title['#text']
        titles.append(title)
    return titles

@st.cache_data
def read_prof_data(path):
    return pd.read_csv(path)

@st.cache_data
def read_google_shcolar_pubs(path):
    scholar_data = pd.read_json(path)
    pubs_data = scholar_data['publications'].to_dict()
    coauthors_data = scholar_data['coauthors'].to_dict()

    return pubs_data,coauthors_data