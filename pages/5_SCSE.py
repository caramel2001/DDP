import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from utils import read_prof_data,read_google_shcolar_pubs,read_pubs_data,read_pubs_data_by_profs
from config.config import settings
import streamlit_antd_components as sac
from search.graph import get_generalized_topics_data,get_treemap_data
from search.community import get_community_graph
import plotly.express as px
import ast
import plotly.graph_objects as go

# Extracted using community detection algorithm and ChatGPT to identiy the labels of the communities
RESEARCH_GROUPS = {
    'Hardware' :[2,4,29,70,15,50,39,62,51],
    'Cypersecurity' : [82,35,71,37,40,45,28,73],
    'AI and Machine Learning' : [17,60,5,48,82,19,49,53,26,77,58,56,85,79,75,62,63],
    'Data Analytics and Mining': [43,12,64,76,63,47,22],
    'ComputerVision': [32,41,36,9,44,80,42,11,13,38,33,7,6,14,52,25,10],
    'Human Computer Interaction': [57,18,59,54,1,84,20],
    'Networks': [46,83,34,78,16,65,0,68,30,31],
    'Distributed Computing': [21,66,14,3,77],
    'Bioinformatics': [27,69,23],
}
st.set_page_config(page_title="SCSE", layout="wide")
research_group = st.sidebar.multiselect("Select Research Groups",list(RESEARCH_GROUPS.keys()),default=None)
st.title("SCSE")
prof_data = read_prof_data(settings['PROF_DATA'])
scholar_data = pd.read_json(settings['SCHOLAR_PUBS'])
print(scholar_data.head())
if research_group:
    ids = []
    for i in research_group:
        ids.extend(RESEARCH_GROUPS[i])
    # print(prof_data.index)
    scholar_data['author_id'] = scholar_data.author_pub_id.str.split(":").apply(lambda x: x[0])
    scholar_ids= prof_data.iloc[ids]['scholar_id'].to_list()
    scholar_data = scholar_data[scholar_data['author_id'].isin(scholar_ids)]
citation_last_year = scholar_data['cites_per_year'].apply(lambda x : x.get('2022',0) if not pd.isna(x) else 0).sum()
total_citations = scholar_data['cites_per_year'].apply(lambda x : sum(list(x.values())) if not pd.isna(x) else 0).sum()

citation_ytd = scholar_data['cites_per_year'].apply(lambda x : x.get('2023',0) if not pd.isna(x) else 0).sum()

num_publications =  scholar_data[scholar_data['pub_year']==2023].shape[0]
num_publications_last =  scholar_data[scholar_data['pub_year']==2022].shape[0]
pubs_percent = (num_publications-num_publications_last)*100/num_publications_last

percent = (citation_ytd-citation_last_year)*100/citation_last_year
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
# col1,col2 = st.columns([3,1])
# with col1:
#     dblp_data = read_pubs_data(settings['PAPER_DATA'])
#     dblp_data = pd.json_normalize(dblp_data,max_level=0)
#     dblp_data.drop_duplicates(subset=['@key'],inplace=True)
#     print(dblp_data.shape)
#     conf_data= pd.read_csv(settings['CONF_PATH'],index_col=[0])
#     conf_topic =  pd.read_csv(settings['CONF_TOPIC_PATH'],index_col=[0])
#     df = get_generalized_topics_data(dblp_data,conf_data,conf_topic)
#     df = pd.DataFrame(zip(df[0],df[1]),columns=['Research Area','Count'])
#     print(df)
#     fig = px.pie(df, values='Count', names='Research Area', color_discrete_sequence=px.colors.qualitative.Set2)
#     fig.update_layout(
#     legend=dict(
#         # orientation="h",  # Set legend orientation to horizontal
#         # yanchor="bottom",  # Anchor the legend to the bottom
#         # y=-2,  # Adjust the Y position for fine-tuning
#         xanchor="left",  # Anchor point for X position
#         x=-0.5  # Adjust the X position for fine-tuning
#     )
# )

#     st.plotly_chart(fig, use_container_width=True)
# Create a stacked bar chart
if research_group:
    dblp_data =read_pubs_data_by_profs(settings['PAPER_DATA'],ids)
else:
    dblp_data = read_pubs_data(settings['PAPER_DATA'])

dblp_data = pd.json_normalize(dblp_data,max_level=0)
dblp_data.drop_duplicates(subset=['@key'],inplace=True)
# print(dblp_data.shape)
conf_data= pd.read_csv(settings['CONF_PATH'],index_col=[0])
conf_topic =  pd.read_csv(settings['CONF_TOPIC_PATH'],index_col=[0])
df = get_generalized_topics_data(dblp_data,conf_data,conf_topic)
df = pd.DataFrame(zip(df[0],df[1]),columns=['Research Area','Count'])
fig = px.bar(df, y='Research Area', x='Count',barmode='stack', title='Distribution of Papers Across Resaerch Areas')
fig.update_layout(
    xaxis_title='Research Area',
    yaxis_title='Publication Count',
    plot_bgcolor='rgba(0,0,0,0)',  # Make the background transparent
    xaxis_tickangle=90,  # Rotate x-axis labels
    xaxis_tickfont=dict(size=12),  # Set fontsize of x-ticks
    yaxis_tickfont=dict(size=12))
st.plotly_chart(fig, use_container_width=True)
# Show the stacked bar chart
col1,col2 = st.columns([1,1],gap='large')
with col1:
    treemap_df = get_treemap_data(dblp_data,conf_data)
    treemap_df= treemap_df[treemap_df['type']=='Conference Paper']
    treemap_df_grouped = treemap_df.groupby('Rank').sum()
    # print(treemap_df)
    fig = px.pie(treemap_df_grouped, values='count', names=treemap_df_grouped.index, color_discrete_sequence=px.colors.qualitative.Set2,title='Conference Paper Rank Distribution')

    st.plotly_chart(fig, use_container_width=True)
with col2:
    st.dataframe(treemap_df.groupby(['Rank','Acronym']).sum().reset_index().sort_values(by='count',ascending=False),use_container_width=True)

st.subheader('Community/Research Groups Detection')
community  = get_community_graph()
components.html(community, height = 800,width=None)
