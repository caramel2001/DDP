import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from utils import read_prof_data,read_google_shcolar_pubs,read_pubs_data_by_prof
from config.config import settings
import plotly.express as px
import ast
from search.graph import get_generalized_topics_multiple

st.set_page_config(page_title="CompareProfessor Profiles", layout="wide")
st.title("Compare Professors")

prof_data = read_prof_data(settings['PROF_DATA'])

def format_funct(id):
    return prof_data.iloc[id]['Full Name']
options = st.multiselect("Select a Professors to compare",prof_data.index.to_list(),max_selections=3,format_func=format_funct)
profs = [prof_data.iloc[id] for id in options]
# print(profs)


dfs = []
for prof in profs:
    citations =ast.literal_eval(prof['cites_per_year']) if not pd.isna(prof['cites_per_year']) else {}
    df = pd.DataFrame(citations.items(),columns=['Year','Citations'])
    df['Prof'] = prof['Full Name']
    dfs.append(df)
if dfs:
    dblp_data= [read_pubs_data_by_prof(settings['PAPER_DATA'],i) for i in options]
    st.subheader('Citations And Publications')
    df = pd.concat(dfs,axis=0)
    # print(df)
    fig = px.line(df, x='Year', y='Citations',color='Prof',markers='o')
    # Customize the layout
    # fig.update_traces(textfont_size=12, textangle=0, textposition="outside", cliponaxis=False)
    fig.update_layout(
        height=350,  # Set the height of the plot
        xaxis_title='Year',
        yaxis_title='Citations',
        xaxis=dict(tickmode='array', tickvals=df['Year']),  # Set custom x-axis tick values
        showlegend=True,  # Remove the legend
        plot_bgcolor='rgba(0,0,0,0)',  # Make the background transparent
        xaxis_tickangle=90,  # Rotate x-axis labels
        xaxis_tickfont=dict(size=12),  # Set fontsize of x-ticks
        yaxis_tickfont=dict(size=12))
    
    st.plotly_chart(fig, use_container_width=True)
    dfs=[]
    for index,data in enumerate(dblp_data):
        if data is None:
            continue
        data = pd.json_normalize(data,max_level=0)
        data = data.groupby(['year']).count()[['@key']].reset_index().rename(columns={'@key':'Publication Count'})
        data['Prof'] = profs[index]['Full Name']
        dfs.append(data)
    df = pd.concat(dfs,axis=0)
    # df = 
    fig = px.bar(df, x='year', y='Publication Count',color='Prof',barmode='group',text='Publication Count')
    fig.update_traces(textfont_size=12, textangle=0, textposition="outside", cliponaxis=False)
    fig.update_layout(
        height=350,  # Set the height of the plot
        xaxis_title='Year',
        yaxis_title='Publication Count',
        xaxis=dict(tickmode='array'),  # Set custom x-axis tick values
        showlegend=True,  # Remove the legend
        plot_bgcolor='rgba(0,0,0,0)',  # Make the background transparent
        xaxis_tickangle=90,  # Rotate x-axis labels
        xaxis_tickfont=dict(size=12),  # Set fontsize of x-ticks
        yaxis_tickfont=dict(size=12))


    st.plotly_chart(fig, use_container_width=True)
    st.subheader('Conferences')

    st.subheader('Research Focus')
    
    conf_data= pd.read_csv(settings['CONF_PATH'],index_col=[0])
    conf_topic =  pd.read_csv(settings['CONF_TOPIC_PATH'],index_col=[0])
    fig = get_generalized_topics_multiple(dblp_data,conf_data,conf_topic,profs)
    st.plotly_chart(fig, use_container_width=True)