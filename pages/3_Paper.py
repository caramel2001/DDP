import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from utils import read_prof_data,read_google_shcolar_pubs
from config.config import settings
import streamlit_antd_components as sac
from search.graph import get_pyvis_graph,get_graph

st.set_page_config(page_title="Research Paper Profile", layout="wide")
pubs_data,coauthors_data = read_google_shcolar_pubs(settings['SCHOLAR_DATA'])

paperId = "6966e8ba9bf98ff754bf68e8d06493f42ad83cf7"
data = get_pyvis_graph(paper_id=paperId)


HtmlFile = open(f"{settings['GRAPH_PATH']}/{paperId}.html", 'r', encoding='utf-8')
source_code = HtmlFile.read() 
# with st.spinner("Loading Graph..."):
#     # read nx.html 
#     with open("nx.html", "r") as f:
#         text = f.read()
# print("Done reading")
# print(text)
# soup = BeautifulSoup(text, 'html.parser')
# text  = soup.find('div', {'id': 'mynetwork'})
# print(text.contents)
# st.markdown(text, unsafe_allow_html=True)

components.html(source_code, height = 900,width=None)
