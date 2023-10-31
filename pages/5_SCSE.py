import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from utils import read_prof_data,read_google_shcolar_pubs,read_pubs_data
from config.config import settings
import streamlit_antd_components as sac
from search.graph import get_pyvis_graph,get_graph,search_paper,get_color_map,get_generalized_topics_data,get_treemap_data
import plotly.express as px
from streamlit_extras.tags import tagger_component 
import ast
import plotly.graph_objects as go

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
dblp_data = read_pubs_data(settings['PAPER_DATA'])
dblp_data = pd.json_normalize(dblp_data,max_level=0)
dblp_data.drop_duplicates(subset=['@key'],inplace=True)
print(dblp_data.shape)
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
    print(treemap_df)
    fig = px.pie(treemap_df_grouped, values='count', names=treemap_df_grouped.index, color_discrete_sequence=px.colors.qualitative.Set2,title='Conference Paper Rank Distribution')

    st.plotly_chart(fig, use_container_width=True)
with col2:
    st.dataframe(treemap_df.groupby(['Rank','Acronym']).sum().reset_index().sort_values(by='count',ascending=False),use_container_width=True)