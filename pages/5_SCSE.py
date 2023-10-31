import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from utils import read_prof_data,read_google_shcolar_pubs
from config.config import settings
import streamlit_antd_components as sac
from search.graph import get_pyvis_graph,get_graph,search_paper,get_color_map
import plotly.express as px
from streamlit_extras.tags import tagger_component 
import ast

st.set_page_config(page_title="SCSE", layout="wide")
st.title("SCSE")

scholar_data = pd.read_json(settings['SCHOLAR_PUBS'])

citation_last_year = scholar_data['cites_per_year'].apply(lambda x : x.get('2022',0) if not pd.isna(x) else 0).sum()
total_citations = scholar_data['cites_per_year'].apply(lambda x : sum(list(x.values())) if not pd.isna(x) else 0).sum()

citation_ytd = scholar_data['cites_per_year'].apply(lambda x : x.get('2023',0) if not pd.isna(x) else 0).sum()

num_publications =  scholar_data[scholar_data['pub_year']==2023].shape[0]
num_publications_last =  scholar_data[scholar_data['pub_year']==2022].shape[0]
pubs_percent = (num_publications-num_publications_last)/num_publications_last

percent = (citation_ytd-citation_last_year)/citation_last_year
# scholar_data['num_citations'].apply(lambda x : as)
# citation_ytd = scholar_data[scholar_data['pub_year']==2023]['num_citations'].sum()
col1, col2, col3,col4 = st.columns(4)
col1.metric("Total Citations", f"{total_citations}")
col2.metric("Citations (YTD)", f"{citation_ytd}", f"{percent:.2f} %")
col3.metric("Total Number Of Publications", f"{scholar_data.shape[0]}")
col4.metric("Number Of Publications (YTD)", f"{num_publications}", f"{pubs_percent:.2f}%")

cites = pd.json_normalize(scholar_data['cites_per_year'])
cites = cites[[str(i) for i in range(2010,2023)]].copy()
df = pd.DataFrame(cites.sum(),columns=['Citations']).reset_index().rename(columns={'index':'Year'})
fig = px.bar(df, x='Year', y='Citations',text='Citations')
fig.update_traces(textfont_size=12, textangle=0, textposition="outside", cliponaxis=False)
fig.update_layout(
    height=350,  # Set the height of the plot
    xaxis_title='Year',
    yaxis_title='Citations',
    xaxis=dict(tickmode='array'),  # Set custom x-axis tick values
    showlegend=True,  # Remove the legend
    plot_bgcolor='rgba(0,0,0,0)',  # Make the background transparent
    xaxis_tickangle=90,  # Rotate x-axis labels
    xaxis_tickfont=dict(size=12),  # Set fontsize of x-ticks
    yaxis_tickfont=dict(size=12))


st.plotly_chart(fig, use_container_width=True)
st.subheader('Conferences')