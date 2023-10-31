import streamlit as st
import streamlit.components.v1 as components
import pandas as pd
from utils import read_prof_data,read_google_shcolar_pubs
from config.config import settings
import streamlit_antd_components as sac
from search.graph import get_pyvis_graph,get_graph,search_paper,get_color_map
import plotly.express as px
from streamlit_extras.tags import tagger_component 

st.set_page_config(page_title="Research Paper Profile", layout="wide")
st.title("Research Paper Profile")
paperId= st.session_state.get('paperId',0)
scholar_data = pd.read_json(settings['SCHOLAR_PUBS'])
st.subheader(scholar_data.iloc[paperId]['title'])
print(scholar_data.iloc[paperId])
col1,col2 = st.columns([1,1],gap='large')
with col1:
    citations = scholar_data.iloc[paperId]['cites_per_year']
    df = pd.DataFrame(citations.items(),columns=['Year','Citations'])
    fig = px.bar(df, x='Year', y='Citations', color_discrete_sequence=['#00c0f2'],text='Citations')
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
    st.markdown(f"<div style=width:90%>Authors: <b>{scholar_data.iloc[paperId]['author']}</b>:</p></div>",unsafe_allow_html=True)
    with st.expander("See Abstract"):
        st.write(scholar_data.iloc[paperId]['abstract'])
    tagger_component("Extracted Research topics: ",list(map(str.title,scholar_data.iloc[paperId]['semantic_topics'])),color_name='lightblue')
    paper_link = scholar_data.iloc[paperId].get("pub_url","")
    x = sac.buttons([
    sac.ButtonsItem(icon='newspaper',label='View Paper',href=paper_link,disabled=True if paper_link == "" or paper_link is None else False),
    ],key=f"paperId-{paperId}")
st.subheader("Paper Network")
st.write("This is based on refrences and citations of the selected paper and references and citations of the papers that cite the selected paper. The edge weight is the number of papers that cite both the papers. The node size is the number of citations of the paper. The node color represents the Time variable in terms of year of publication. The node label is the title of the paper and Authors. Red Node represents the selected paper. Blue Nodes represent direct connections of the selected paper. Grey Nodes represents all other nodes. The graph is interactive and can be zoomed in and out and dragged around. Hover over the nodes to see the title of the paper and the authors. Hover on the nodes to see the more paper profile data.")

search = search_paper(scholar_data.iloc[paperId]['title'])
print(search['results'][0])
# paperId = "6966e8ba9bf98ff754bf68e8d06493f42ad83cf7"
paperId = search['results'][0]['id']
data = get_pyvis_graph(paper_id=paperId)

HtmlFile = open(f"{settings['GRAPH_PATH']}/{paperId}.html", 'r', encoding='utf-8')
source_code = HtmlFile.read() 
# with st.spinner("Loading Graph..."):
#     # read nx.html 
#     with open("nx.html", "r") as f:
#         text = f.read()t
# print(text)
# soup = BeautifulSoup(text, 'html.parser')
# text  = soup.find('div', {'id': 'mynetwork'})
# print(text.contents)
# st.markdown(text, unsafe_allow_html=True)

components.html(source_code, height = 800,width=None)
fig = get_color_map()
st.pyplot(fig,use_container_width=False)