import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
from streamlit_extras.tags import tagger_component 
from utils import read_prof_data,read_google_shcolar_pubs,read_pubs_data_by_prof
from config.config import settings
import json
import ast
import streamlit_antd_components as sac
import streamlit.components.v1 as components
import plotly.express as px
from search.graph import get_coauthor_graph,get_treemap,get_granalur_topics_graph

# Layout of the page
st.set_page_config(page_title="Professor Profile", layout="wide")
prof_data = read_prof_data(settings['PROF_DATA'])
pubs_data,coauthors_data = read_google_shcolar_pubs(settings['SCHOLAR_DATA'])

conf_data= pd.read_csv(settings['CONF_PATH'],index_col=[0])

# print(pubs_data[0])
print(st.session_state)
profid = int(st.session_state.get('profId',0))
print(profid)
prof = prof_data.iloc[profid]
print(prof)
css_body_container = '''
    <style>
        [data-testid="stSidebar"] + section [data-testid="stVerticalBlock"]
        [data-testid="stVerticalBlock"] {
            gap: 0;
        }
    </style>
    '''
st.markdown(css_body_container,unsafe_allow_html=True)
# print(json.loads(prof['cites_per_year']))
# Header
col1, col2 = st.columns([1,6])
with col1:
    picture_url = prof['url_picture'] if not pd.isna(prof['url_picture']) else "../app/static/user_profile.png" 
    st.image(picture_url,use_column_width=True) # Placeholder image; replace with actual profile image
with col2:
    st.subheader(prof['Full Name'])
    st.write(f"""{" , ".join(json.loads(prof.get('affiliations',"").replace("'",'"')))}""")
    st.write(f"Email : {prof['Email']}")
    research_keywords = prof.get('research_keywords',"[]") if not pd.isna(prof.get('research_keywords',"[]")) else "[]"
    tagger_component("Research Interests: ", json.loads(research_keywords.replace("'",'"')),color_name='lightblue')
    st.write()
st.divider()
citations =ast.literal_eval(prof['cites_per_year']) if not pd.isna(prof['cites_per_year']) else {}
# citations = ast.literal_eval()
col1,col2 = st.columns([1,1],gap='large')
# Citations graph
with col1:
    if citations:
        df = pd.DataFrame(citations.items(),columns=['Year','Citations'])
        fig = px.bar(df, x='Year', y='Citations', color_discrete_sequence=['#00c0f2'],text='Citations',text_auto='.2s')
        # Customize the layout
        fig.update_traces(textfont_size=12, textangle=0, textposition="outside", cliponaxis=False)
        fig.update_layout(
            height=350,  # Set the height of the plot
            xaxis_title='Year',
            yaxis_title='Citations',
            xaxis=dict(tickmode='array', tickvals=df['Year']),  # Set custom x-axis tick values
            showlegend=False,  # Remove the legend
            plot_bgcolor='rgba(0,0,0,0)',  # Make the background transparent
            xaxis_tickangle=90,  # Rotate x-axis labels
            xaxis_tickfont=dict(size=12),  # Set fontsize of x-ticks
            yaxis_tickfont=dict(size=12))

        st.plotly_chart(fig, use_container_width=True)
with col2:
    if not pd.isna(prof['scholar_id']):
        st.write("Profile Links")
        x = sac.buttons([
                sac.ButtonsItem(icon='person',label='Dashboard',color = "#ccc",href="#"),
                sac.ButtonsItem(icon='person',label='Website',color = "#ccc",href=prof['personal_websites'],disabled=True if pd.isna(prof['personal_websites']) else False),
                sac.ButtonsItem(icon='building',label='DR NTU',color = "#ccc",href=f'https://dr.ntu.edu.sg/{prof["profile_link"]}',disabled=True if pd.isna(prof['profile_link']) else False),
                sac.ButtonsItem(icon='google',label='Scholar',color = "#ccc",href=f'https://scholar.google.com/citations?user={prof["scholar_id"]}',disabled=True if pd.isna(prof['scholar_id']) else False),
                sac.ButtonsItem(icon='book',label='DBLP',color = "#ccc",href=prof['DBLP_profile_link'],disabled=True if pd.isna(prof['DBLP_profile_link']) else False),
            ],size='small')
        st.write("Citation Table")
        # Data for the table
        data = {
            "All": [int(prof['citedby']), int(prof['hindex']), int(prof['i10index'])],
            "Since 2018": [int(prof['citedby5y']), int(prof['hindex5y']), int(prof['i10index5y'])]
        }
        # Columns for the table
        columns = ["", "All", "Since 2018"]

        # Convert data to a format suitable for displaying in Streamlit
        table_data = [["Citations", data["All"][0], data["Since 2018"][0]],
                    ["h-index", data["All"][1], data["Since 2018"][1]],
                    ["i10-index", data["All"][2], data["Since 2018"][2]]]
        # Display the table in Streamlit
        st.table(pd.DataFrame(table_data, columns=columns))


st.divider()
# st.session_state['page'] = 1
st.subheader("Publications")
df = pd.json_normalize(pubs_data[profid])[['bib.title','bib.pub_year','num_citations','bib.citation']].rename(columns={'bib.title':'Title','bib.pub_year':'Year','num_citations':'Cited By Count','bib.citation':'Source'})
col1,col2 = st.columns([1,1])
with col1:
    # st.selectbox("Sort",('Year','Citation Count'))
    bool_citation=sac.switch(label='Sort By Citation Count(Default : By Year)',value=True, align='start', size='default')
    if bool_citation:
        df.sort_values(by='Cited By Count',ascending=False,inplace=True)
    else:
        df.sort_values(by='Year',ascending=False,inplace=True)
with col2:
    st.session_state['page'] = sac.pagination(total=df.shape[0], align='end', jump=False, show_total=False,circle=True)

st.dataframe(df.iloc[st.session_state.get('page',1)*10-10:st.session_state.get('page',1)*10])

col1,col2 = st.columns([1,1])
with col1:
    st.subheader("Co-Authors Network")
    pyvis=True
    if pyvis:
        html,fig,bar_fig= get_coauthor_graph(coauthors_data[profid],prof_data,prof_id=profid,pyvis=pyvis)
        st.pyplot(fig,use_container_width=True)
        components.html(html, height = 350,width=None)
        st.plotly_chart(bar_fig,use_container_width=True)

    else:
        fig,bar_fig = get_coauthor_graph(coauthors_data[profid],prof_data,prof_id=profid)
        st.pyplot(fig,use_container_width=True)
        st.plotly_chart(bar_fig,use_container_width=True)

with col2:
    st.subheader("Top Co-Authors")

st.divider()
col1,col2 = st.columns([1,1])
with col1:
    st.subheader("Generalized Research Focus")

with col2:
    st.subheader("Fine-Grained Research Focus")
    if pd.isna(prof['scholar_id']):
        st.warning("No Google Scholar Data Found")
    else:
        st.markdown("<br>",unsafe_allow_html=True)
        st.write("These topics are classfied on CSO Ontology Dataset on Title + Abstract of the publications")
        st.markdown("<br>",unsafe_allow_html=True)
        year = st.slider("Select Before Year",min_value=2015,max_value=2023,value=2020)
        st.markdown("<br>",unsafe_allow_html=True)
        scholar_data = pd.read_json(settings['SCHOLAR_PUBS'])
        fig = get_granalur_topics_graph(scholar_data,prof['scholar_id'],year = year)
        st.plotly_chart(fig,use_container_width=True)
        st.markdown("<p style='text-align: center;'>Number of Publications top 10 topics</p>", unsafe_allow_html=True)

st.divider()

dblp_data= read_pubs_data_by_prof(settings['PAPER_DATA'],profid)
dblp_data = pd.json_normalize(dblp_data,max_level=0)
st.subheader("Publications Distribution")
fig = get_treemap(dblp_data,conf_data)
st.plotly_chart(fig,use_container_width=True)