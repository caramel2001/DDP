import streamlit as st
import streamlit_antd_components as sac
import pandas as pd
from streamlit_extras.tags import tagger_component 

def get_card(entry:pd.Series):
    name = entry['Full Name']
    email = entry['Email']
    interests= entry['research_keywords']
    if pd.isna(interests):
        interests = ""
    else:
        interests = interests.replace("'","").replace("["," ").replace("]","")
    website=entry['personal_websites'] if not pd.isna(entry['personal_websites']) else None
    dr_ntu=entry['profile_link']
    scholar=entry['scholar_id']
    dblp=entry['DBLP_profile_link'] if not pd.isna(entry['DBLP_profile_link']) else None
    profId=entry['profID']
    interests = interests or []
    # Add content inside the container
    # st.image("https://scholar.googleusercontent.com/citations?view_op=view_photo&user=7_AzrLwAAAAJ&citpid=7")
    st.markdown(f"#### {name}")
    st.write(f"Email : {email}")
    st.markdown(f"<div style=width:90%><p style =font-size:10px><b>Research Interests</b>:{interests}</p></div>",unsafe_allow_html=True)
    # # Create a button inside the container
    x = sac.buttons([
    sac.ButtonsItem(icon='person',label='Website',color = "#ccc",href=website,disabled=True if website == "" or pd.isna(website) else False),
        sac.ButtonsItem(icon='building',label='DR NTU',color = "#ccc",href=f'https://dr.ntu.edu.sg/{dr_ntu}',disabled=True if dr_ntu == "" or dr_ntu is None else False),
        sac.ButtonsItem(icon='google',label='Scholar',color = "#ccc",href=f'https://scholar.google.com/citations?user={scholar}',disabled=True if scholar == "" or scholar is None else False),
        sac.ButtonsItem(icon='book',label='DBLP',color = "#ccc",href=dblp,disabled=True if dblp == "" or dblp is None else False),
    ],size='small')
    button = st.button("Select Prof",type='primary',key=f"more-info-prof-id-{profId}")
    if button:
        st.session_state['profId'] = profId


def get_paper_card(entry:dict,id):
    name = entry['title']
    if isinstance(name,dict):
        name = name.get("#text","")
    type = entry['type']
    type = type.replace("_"," ").title()
    paper_link = entry.get("ee",{})
    if isinstance(paper_link,dict):
        paper_link = paper_link.get("#text","")
    elif isinstance(paper_link,list):
        paper_link = paper_link[0]
    authors = entry.get('author',[])
    authors = authors if isinstance(authors,list) else [authors]
    authors = ", ".join([author.get("#text","") for author in authors])
    date = entry['@mdate']
    date = pd.to_datetime(date).strftime("%d %b %Y")
    
    # email = entry['Email']
    st.markdown(f"##### {name}")
    st.markdown(f"Paper Published on : **{date}**")
    st.markdown(f"<div style=width:90%><b>Authors</b>: {authors}</p></div>",unsafe_allow_html=True)
    tagger_component("Paper Type : ", [type],color_name='lightblue')
    paper_id=id
    # # Create a button inside the container
    x = sac.buttons([
    sac.ButtonsItem(icon='newspaper',label='View Paper',color = "#ccc",href=paper_link,disabled=True if paper_link == "" or paper_link is None else False),
    ],size='small',key=f"paperId-{paper_id}")
    if st.button("Select Paper",type='primary',key=f"more-info-paper-id-{paper_id}"):
        st.session_state['paperId'] = paper_id