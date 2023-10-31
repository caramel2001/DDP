import requests
import zlib
import json
import time
from urllib.parse import quote
from pyvis.network import Network
import numpy as np
import networkx as nx
import re
import os
import matplotlib.pyplot as plt
from bs4 import BeautifulSoup
import plotly.express as px
import pandas as pd
from tqdm import tqdm
import plotly.graph_objects as go
import streamlit as st
import matplotlib.colors as mcolors
from matplotlib.cm import ScalarMappable
# from cso_classifier import CSOClassifier
# cc = CSOClassifier(modules = "both", enhancement = "first", explanation = True)
NODE_SIZE_FACTOR = 0.7
CIT_TO_SIZE_EXPONENT = 0.41
CIT_TO_SIZE_SCALAR = 20
LOG_OFFSET_FACTOR = 500
CONFERENCE_NODE_SIZE = 3
PY_2_JS_SCALE = 0.15
NUM_EDGES = 300
STROKE_WIDTH_FACTOR = 0.075
EDGE_OPACITY_PERCENTILE = 0.9
EDGE_OPACITY_POWER = 3
MAX_EDGE_OPACITY = 1

RESPONSE_MAGIC = b'CPGR'  # Connected Papers Graph Response
MINIMAL_LENGTH = 16

STATUS_STRINGS = {
    1: "OK",
    2: "LONG_PAPER",
    3: "IN_PROGRESS",
    4: "NOT_RUN",
    5: "ADDED_TO_QUEUE",
    6: "ERROR",
    7: "OVERLOADED",
    8: "IN_QUEUE",
    9: "NOT_IN_API",
    10: "UNKNOWN"
}


def parse_binary_uuid(binary_uuid):
    naked_uuid = "".join(["{:02x}".format(item) for item in binary_uuid])
    return "-".join([naked_uuid[i:j] for i, j in [(0, 8), (8, 12), (12, 16), (16, 20), (20, len(naked_uuid))]])


def parse_binary_response(paper_id, response):
    buffer = response
    if len(buffer) < MINIMAL_LENGTH:
        return {
            "paper_id": paper_id,
            "status": STATUS_STRINGS[6],
            "err": "Header not found, response too short",
            "data": None
        }

    magic = buffer[:4]
    if magic != RESPONSE_MAGIC:
        return {
            "paper_id": paper_id,
            "status": STATUS_STRINGS[6],
            "err": "Bad magic",
            "data": None
        }

    status = int.from_bytes(buffer[4:8], byteorder='little')
    status_str = STATUS_STRINGS.get(status, STATUS_STRINGS[6])

    buffer = buffer[8:]
    raw_data_length = int.from_bytes(buffer[:4], byteorder='little')
    raw_data_bytes = buffer[4:4 + raw_data_length]

    if len(raw_data_bytes) != raw_data_length:
        return {
            "paper_id": paper_id,
            "status": STATUS_STRINGS[6],
            "err": "Length-value mismatch in protocol",
            "data": {"unparsed_buffer": buffer}
        }

    data = None
    if raw_data_length > 0:
        if status == 1:
            uncompressed_data_bytes = zlib.decompress(raw_data_bytes)
            data_str = uncompressed_data_bytes.decode('utf-8')
            data = json.loads(data_str)
        elif status == 3 and raw_data_length == 4:
            progress_percent = int.from_bytes(raw_data_bytes, byteorder='little')
            data = {"progress": progress_percent}
        else:
            return {
                "paper_id": paper_id,
                "status": status_str,
                "err": "Bad response format",
                "data": {"unparsed_buffer": buffer}
            }

    buffer = buffer[4 + raw_data_length]
    # print(buffer)
    if data and False:
        uuid_length = int.from_bytes(buffer[:4], byteorder='little')
        data["uuid"] = parse_binary_uuid(buffer[4:4 + uuid_length])

    return {
        "paper_id": paper_id,
        "status": status_str,
        "err": None if status_str == "OK" else "Error occurred",
        "data": data
    }

@st.cache_data
def get_graph(paper_id):
    print("Getting Data.....")
    status = get_graph_status(paper_id)
    if status['rebuild_available']:
        print("Buildling Graph.....")
        request_graph_build(paper_id)
        time.sleep(5)
    url = f"https://rest.connectedpapers.com/graph_no_build/{paper_id}"
    response = requests.get(url,headers={'user-agent': 'Mozilla/5.0','accept-encoding': 'zip'})
    if response.status_code != 200:
        return None
    resp = parse_binary_response(paper_id,response.content)
    while resp.get('status')=='IN_PROGRESS':
        time.sleep(5)
        response = requests.get(url,headers={'user-agent': 'Mozilla/5.0','accept-encoding': 'zip'})
        resp = parse_binary_response(paper_id,response.content)
    return resp

def request_graph_build(paper_id):
    url= f"https://rest.connectedpapers.com/graph/{paper_id}"
    requests.post(url,headers={'user-agent': 'Mozilla/5.0'})

def get_graph_status(paper_id):
    url = f"https://rest.connectedpapers.com/versions/{paper_id}/1"
    response = requests.get(url,headers={'user-agent': 'Mozilla/5.0'})
    return response.json()

def search_paper(title):
    title = quote(title)
    url = f"https://rest.connectedpapers.com/search/{title}/1"
    response = requests.post(url,headers={'user-agent': 'Mozilla/5.0'})
    if response.status_code != 200:
        return None
    return response.json()

# def classify_abstract(paper):
#     global cc
#     result = cc.run(paper)
#     return result


def plot_coauthor_bar(G):
    fig = px.bar(pd.DataFrame([i[1] for i in G.nodes(data=True)]).groupby('type')[['label']].count().drop('Selected'),text_auto='.0f')
    fig.update_layout(height=400)  # Adjust the height as needed

    # Remove the x and y labels
    fig.update_xaxes(title_text=None)
    fig.update_yaxes(title_text='Count')
    # Remove the legend
    fig.update_layout(showlegend=False)

    # Make the background transparent
    fig.update_layout(plot_bgcolor='rgba(0,0,0,0)')
    return fig


def get_color_map():
    years = [i for i in range(2010,2023)]
    a = np.linspace(0.2,0.9,len(set(years)))
    years = list(set(years))
    years.sort()
    data ={}
    for i in range(len(years)):
        data[years[i]] = f"rgba(13, 110, 253,{a[i]})"
    # Define the data
    fig = plt.figure(figsize=(20, 1))
    # Extract the alpha values from the data
    alphas = [float(color.split(',')[3][:-1]) for color in data.values()]
    # Define a custom colormap with blue color
    cmap = mcolors.LinearSegmentedColormap.from_list("Custom Blue", [(13/255, 110/255, 253/255, alpha) for alpha in alphas])

    # Create a ScalarMappable object
    sm = ScalarMappable(cmap=cmap, norm=plt.Normalize(vmin=min(alphas), vmax=max(alphas)))
    sm.set_array([])  # Set an empty array

    # Create a colorbar
    cbar = plt.colorbar(sm, orientation='horizontal', ticks=[])
    min_year = min(data.keys())
    max_year = max(data.keys())
    cbar.ax.text(0.05, 0, str(min_year),fontsize=12)
    cbar.ax.text(0.95, 0, str(max_year), fontsize=12)
    # Customize the colorbar
    cbar.set_label('Publication Year', rotation=0, fontsize=10)
    ax = plt.gca()  # get current axis
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.set_xticks([])  # remove x ticks
    ax.set_yticks([])  # remove y ticks
    # Display the colorbar
    return fig

def get_pyvis_graph(paper_id):
    script_path = os.path.abspath(__file__)
    script_dir = os.path.dirname(script_path)
    parent_dir = os.path.dirname(script_dir)
    path = parent_dir+"/data/graphs"
    
    if os.path.exists(f'{path}/{paper_id}.html'):
        print("Graph Already Built")
        return None
    data = get_graph(paper_id)
    data = data['data']
    nodes = list(data['nodes'].values())
    years = [i['year'] for i in nodes]
    a = np.linspace(0.2,0.9,len(set(years)))
    years = list(set(years))
    years.sort()
    color_map ={}
    for i in range(len(years)):
        color_map[years[i]] = f"rgba(13, 110, 253,{a[i]})"
    def split_string_into_lines(input_string, words_per_line=10):
        if input_string is None:
            return ""
        words = re.findall(r'\S+', input_string)
        lines = []
        for i in range(0, len(words), words_per_line):
            line = ' '.join(words[i:i + words_per_line])
            lines.append(line)
        return '\n'.join(lines)
    edge_strengths = [i[2] for i  in data['edges']]
    edge_strengths.sort()
    percentile_index = int(edge_strengths.__len__() * EDGE_OPACITY_PERCENTILE)
    max_edge = edge_strengths[percentile_index]
    draw_strength = [(i[2] / max_edge) ** EDGE_OPACITY_POWER * MAX_EDGE_OPACITY for i in data['edges']]
    min_edge =edge_strengths[max(0, data['edges'].__len__() - NUM_EDGES)]
    edges = []
    for i in data['edges']:
        if i[2] >= min_edge:
            i.append((i[2] / max_edge) ** EDGE_OPACITY_POWER * MAX_EDGE_OPACITY)
            edges.append(i)
    G = nx.Graph()
    # print(nodes)
    for i in nodes:
        cit_count = i.get('citations_length', 0)
        node_size = (NODE_SIZE_FACTOR *(cit_count ** CIT_TO_SIZE_EXPONENT + CIT_TO_SIZE_SCALAR))/(np.log(cit_count + LOG_OFFSET_FACTOR)/np.log(LOG_OFFSET_FACTOR))
        abstract = split_string_into_lines(i['abstract'], words_per_line=15)
        hover_data = f"""Title : {i.get('title','')} \n Pub Date : {i.get('publicationDate',"")} \n  Citations : {i.get('citations_length',None)} \n Authors :  {",".join([j.get('name','') for j in i.get('authors',[])])} \n Abstract : {abstract}"""
        if i['id'] == nodes[0]['id']:
            G.add_node(i['id'],label = f"{i['authors'][0]['name']} et al, {i['year']}",color="#e63946",size=node_size,x=i['pos'][0],y=i['pos'][1],title=hover_data)
            continue
        G.add_node(i['id'],label = f"{i['authors'][0]['name']} et al, {i['year']}",color=color_map[i['year']],size=node_size,x=i['pos'][0],y=i['pos'][1],title=hover_data)
    for i in edges:
        G.add_edge(i[0],i[1],color=f"rgba(20, 33, 61,{i[3]})",title="Similarity : {:.3f}".format(i[2]))
    nt = Network(height="900px", width="100%", bgcolor="rgba(255,255,255,0)", font_color="#1d3557",filter_menu=True,neighborhood_highlight=True,notebook=True,cdn_resources='in_line')
    # populates the nodes and edges data structures
    nt.from_nx(G)
    # nt.toggle_physics(False)
    # nt.show_buttons(filter_=True)
    nt.set_options("""
    const options = {
    "nodes": {
        "borderWidthSelected": 5,
        "opacity": 1,
        "font": {
        "size": 18,
        "face": "verdana"
        },
        "size": null
    },
    "edges": {
        "color": {
        "inherit": true
        },
        "selfReferenceSize": null,
        "selfReference": {
        "angle": 0.7853981633974483
        },
        "smooth": {
        "forceDirection": "none"
        }
    },
    "interaction": {
        "hover": true,
        "multiselect": true,
        "tooltipDelay": 100
    },
    "physics": {
        "forceAtlas2Based": {
        "springLength": 100,
        "avoidOverlap": 0.14
        },
        "minVelocity": 0.75,
        "solver": "forceAtlas2Based"
    }
    }""")
    
    # Get the full path of the current script
    html = nt.generate_html('coauthor.html')
    soup = BeautifulSoup(html, 'html.parser')
    # remove border
    # Define the custom CSS styles
    custom_css = """
    <style>
        .card{
            border: 0;
        }
        #mynetwork {
            border: 0;
        }
    </style>
    """

    # Find the 'div' element with id='mynetwork'
    mynetwork_div = soup.find('div', class_='card')

    # Create a new BeautifulSoup object for the custom CSS
    custom_css_soup = BeautifulSoup(custom_css, 'html.parser')

    # Insert the custom CSS styles before the 'mynetwork' div
    mynetwork_div.insert_before(custom_css_soup)

    # Convert the modified soup object back to an HTML string
    modified_html_string = str(soup)
    with open(f'{path}/{paper_id}.html','w') as f:
        f.write(modified_html_string)

    return data


def get_coauthor_graph(data,prof_data,prof_id,pyvis=False):
    G = nx.Graph()
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
    for i in data:
        if i['scholar_id'] in prof_data['scholar_id'].to_list():
            G.add_node(i['scholar_id'],label=i['name'],color='#03045e',type= 'SCSE')
            continue
        if i['affiliation'] in NTU_KEYWORDS:
            G.add_node(i['scholar_id'],label=i['name'],color='#48cae4',type='NTU(Non-SCSE)')
            continue

        G.add_node(i['scholar_id'],label=i['name'],color='#caf0f8',type='Outside NTU')
    prof =prof_data.loc[prof_id]
    G.add_node(prof['scholar_id'],label=prof['Full Name'],title=prof['Full Name'],color="#e63946",type='Selected')
    for i in data:
        G.add_edge(prof['scholar_id'],i['scholar_id'])
    bar_fig = plot_coauthor_bar(G)
    if pyvis:
        nt = Network(height="350px", width="100%", bgcolor="rgba(255,255,255,0)", font_color="#1d3557",notebook=True,cdn_resources='in_line')
        # populates the nodes and edges data structures
        nt.from_nx(G) 
        nt.toggle_physics(True)
        nt.set_options("""
        const options = {
            
            "nodes": {
                "borderWidth": null,
                "borderWidthSelected": null,
                "opacity": 1,
                "font": {
                "size": 14
                },
                "size": null
            },
            "edges": {
                "color": {
                "inherit": true
                },
                "selfReferenceSize": null,
                "selfReference": {
                "angle": 0.7853981633974483
                },
                "smooth": {
                "forceDirection": "none"
                }
            },
            "physics": {
                "repulsion": {
                "centralGravity": 1.05,
                "springLength": 100
                },
                "minVelocity": 0.75,
                "solver": "repulsion"
            }
            }""")
        html = nt.generate_html('coauthor.html')
        soup = BeautifulSoup(html, 'html.parser')
        # remove border
        # Define the custom CSS styles
        custom_css = """
        <style>
            .card{
                border: 0;
            }
            #mynetwork {
                border: 0;
            }
        </style>
        """

        # Find the 'div' element with id='mynetwork'
        mynetwork_div = soup.find('div', class_='card')

        # Create a new BeautifulSoup object for the custom CSS
        custom_css_soup = BeautifulSoup(custom_css, 'html.parser')

        # Insert the custom CSS styles before the 'mynetwork' div
        mynetwork_div.insert_before(custom_css_soup)

        # Convert the modified soup object back to an HTML string
        modified_html_string = str(soup)
        fig = plt.figure(figsize=(12,1))
        ax = plt.gca()  # get current axis
        ax.spines['right'].set_visible(False)
        ax.spines['top'].set_visible(False)
        ax.spines['left'].set_visible(False)
        ax.spines['bottom'].set_visible(False)
        ax.set_xticks([])  # remove x ticks
        ax.set_yticks([])  # remove y ticks
        # Add a legend
        legend_labels = {'Selected Prof':'#e63946','Current SCSE':'#03045e','NTU': '#48cae4', 'Outside NTU': '#e5e5e5'}
        legend_handles = [plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=color, markersize=10, label=label)
                        for label, color in legend_labels.items()]
        plt.legend(handles=legend_handles, loc='upper right')
        return modified_html_string,fig,bar_fig
    fig = plt.figure(figsize=(10,1))
    layout = nx.kamada_kawai_layout(G)
    nx.draw_networkx_nodes(G, pos=layout,node_color =[i[1]['color'] for i in G.nodes(data=True)] )
    nx.draw_networkx_edges(G, pos=layout)
    labels = {node: data['label'] for node, data in G.nodes(data=True)}
    nx.draw_networkx_labels(G, pos=layout, labels=labels,font_size=9,verticalalignment='top',font_weight='800')
    # # Remove the spine box of the plot
    ax = plt.gca()  # get current axis
    ax.spines['right'].set_visible(False)
    ax.spines['top'].set_visible(False)
    ax.spines['left'].set_visible(False)
    ax.spines['bottom'].set_visible(False)
    ax.set_xticks([])  # remove x ticks
    ax.set_yticks([])  # remove y ticks
    # Add a legend
    legend_labels = {'Selected Prof':'#e63946','SCSE':'#03045e','NTU': '#48cae4', 'Outside NTU': '#e5e5e5'}
    legend_handles = [plt.Line2D([0], [0], marker='o', color='w', markerfacecolor=color, markersize=10, label=label)
                    for label, color in legend_labels.items()]
    plt.legend(handles=legend_handles, loc='upper right')
    return fig,bar_fig


def get_conf_id(i):
    if isinstance(i,list):
        if len(i)<=1:
            return None
        return i[1].split('/')[0]
    return None
    
def get_treemap(data,conf_data):
    tqdm.pandas()
    data['conf_id'] = None
    data.loc[data[data['type'].isin(['conference_paper'])].index,'conf_id']=data[data['type'].isin(['conference_paper'])]['crossref'].str.split("conf/").progress_apply(get_conf_id)
    # temp = temp[temp['type'].isin(['conference_paper'])].copy()
    merge_df = data.merge(conf_data.dropna(subset='DBLP'),left_on='conf_id',right_on='DBLP',how='left')
    treemap_df = merge_df.groupby(['type','Rank','DBLP','Acronym','Title'],dropna=False).count().reset_index()[['type','Rank','Acronym','Title','@key']].sort_values(['type','@key'],ascending=False).rename(columns={'@key':'count'})
    # Create a DataFrame from the data
    # Create a treemap using Plotly Express
    treemap_df['Rank'].fillna("Unranked",inplace=True)
    treemap_df['type'] = treemap_df['type'].str.replace("_"," ").str.title()
    treemap_df['Type_Rank'] = treemap_df['type'] + '_' + treemap_df['Rank']
    treemap_df.sort_values('Type_Rank',ascending=True,inplace=True)
    fig = px.treemap(treemap_df.fillna(' '), path=[px.Constant("Research Paper Distribution"),'type', 'Rank', 'Acronym'], values='count',labels='count',maxdepth=3,hover_data=['Title'],color='Type_Rank',color_discrete_sequence=px.colors.sequential.Blues[::-1])

    # Customize the layout (optional)
    fig.update_layout(
        # title='Treemap of Type, Rank, and Acronym',
        margin=dict(l=0, r=0, b=0, t=20),
        width=800,
        height=600,
    )
    fig.update_traces(root_color="lightgrey")
    # fig.update_layout(margin = dict(t=50, l=25, r=25, b=25))
    fig.update_traces(marker=dict(cornerradius=3))
    return fig

def get_treemap(data,conf_data):
    tqdm.pandas()
    data['conf_id'] = None
    data.loc[data[data['type'].isin(['conference_paper'])].index,'conf_id']=data[data['type'].isin(['conference_paper'])]['crossref'].str.split("conf/").progress_apply(get_conf_id)
    # temp = temp[temp['type'].isin(['conference_paper'])].copy()
    merge_df = data.merge(conf_data.dropna(subset='DBLP'),left_on='conf_id',right_on='DBLP',how='left')
    treemap_df = merge_df.groupby(['type','Rank','DBLP','Acronym','Title'],dropna=False).count().reset_index()[['type','Rank','Acronym','Title','@key']].sort_values(['type','@key'],ascending=False).rename(columns={'@key':'count'})
    # Create a DataFrame from the data
    # Create a treemap using Plotly Express
    treemap_df['Rank'].fillna("Unranked",inplace=True)
    treemap_df['type'] = treemap_df['type'].str.replace("_"," ").str.title()
    treemap_df['Type_Rank'] = treemap_df['type'] + '_' + treemap_df['Rank']
    treemap_df.sort_values('Type_Rank',ascending=True,inplace=True)
    fig = px.treemap(treemap_df.fillna(' '), path=[px.Constant("Research Paper Distribution"),'type', 'Rank', 'Acronym'], values='count',labels='count',maxdepth=3,hover_data=['Title'],color='Type_Rank',color_discrete_sequence=px.colors.sequential.Blues[::-1])

    # Customize the layout (optional)
    fig.update_layout(
        # title='Treemap of Type, Rank, and Acronym',
        margin=dict(l=0, r=0, b=0, t=20),
        width=800,
        height=600,
    )
    fig.update_traces(root_color="lightgrey")
    # fig.update_layout(margin = dict(t=50, l=25, r=25, b=25))
    fig.update_traces(marker=dict(cornerradius=3))
    return fig

def get_treemap_data(data,conf_data):
    tqdm.pandas()
    data['conf_id'] = None
    data.loc[data[data['type'].isin(['conference_paper'])].index,'conf_id']=data[data['type'].isin(['conference_paper'])]['crossref'].str.split("conf/").progress_apply(get_conf_id)
    # temp = temp[temp['type'].isin(['conference_paper'])].copy()
    merge_df = data.merge(conf_data.dropna(subset='DBLP'),left_on='conf_id',right_on='DBLP',how='left')
    treemap_df = merge_df.groupby(['type','Rank','DBLP','Acronym','Title'],dropna=False).count().reset_index()[['type','Rank','Acronym','Title','@key']].sort_values(['type','@key'],ascending=False).rename(columns={'@key':'count'})
    # Create a DataFrame from the data
    # Create a treemap using Plotly Express
    treemap_df['Rank'].fillna("Unranked",inplace=True)
    treemap_df['type'] = treemap_df['type'].str.replace("_"," ").str.title()
    treemap_df['Type_Rank'] = treemap_df['type'] + '_' + treemap_df['Rank']
    treemap_df.sort_values('Type_Rank',ascending=True,inplace=True)
    return treemap_df

def get_granalur_topics_graph(scholar_data,scholar_id,year,citation_count = False):
    scholar_data['author_id'] = scholar_data.author_pub_id.str.split(":").apply(lambda x: x[0])
    prof_pubs = scholar_data[scholar_data['author_id']==scholar_id]
    if citation_count:
        temp = pd.json_normalize(prof_pubs[['semantic_topics','pub_year','num_citations']].to_dict('records'),meta=['num_citations','pub_year'],record_path='semantic_topics').groupby([0,'pub_year']).mean().sort_values('num_citations',ascending=False)
    else:
        temp = pd.json_normalize(prof_pubs[['semantic_topics','pub_year','num_citations']].to_dict('records'),meta=['num_citations','pub_year'],record_path='semantic_topics').groupby([0,'pub_year']).count().sort_values('num_citations',ascending=False)
    temp_after = temp[temp.index.get_level_values(1)>=year].groupby([0]).sum().sort_values('num_citations',ascending=False).head(10)
    # print(temp_after)
    temp_before = temp[temp.index.get_level_values(1)<year].groupby([0]).sum().sort_values('num_citations',ascending=False)
    # print(temp_before)
    temp_before = temp_before.loc[set(temp_after.index).intersection(set(temp_before.index))]
    temp_before.index = temp_before.index.str.title()
    temp_after.index = temp_after.index.str.title()
    num_citations_after = temp_after.num_citations
    num_citations_before = temp_before.num_citations
    topics_after = temp_after.index
    topics_before = temp_before.index
    #set index name to 0
    chart_df = pd.DataFrame(index=topics_after)
    chart_df.index.name = 0
    chart_df['before'] = num_citations_before
    chart_df['before'] = chart_df['before']/chart_df['before'].sum()
    chart_df['after'] = num_citations_after
    chart_df['after'] = chart_df['after']/chart_df['after'].sum()
    chart_df.sort_values('before',ascending=False,inplace=True)
    chart_df.fillna(0,inplace=True)

    fig = go.Figure()
    categories = chart_df.index.to_list()
    fig.add_trace(go.Scatterpolar(
        r=chart_df.after.to_list(),
        theta=categories,
        fill='toself',
        name=f'{year} and After',
        line=dict(color='#e63946'),  # Set the line color
        marker=dict(color='#e63946'),  # Set the marker (area) color
    ))
    fig.add_trace(go.Scatterpolar(
        r=chart_df.before.to_list(),
        theta=categories,
        fill='toself',
        name=f'Before {year}',
        line=dict(color='#457b9d'),  # Set the line color
        marker=dict(color='#457b9d'),  # Set the marker (area) color
    ))

    fig.update_layout(
    polar=dict(
        radialaxis=dict(
        visible=True,
        )),
    showlegend=True,
    legend=dict(
        x=1,  # Set the x position to center the legend horizontally
        y=1.25,    # Set the y position to place the legend at the bottom
    ),
    height=400,
    width=300,
    margin=dict(l=100, r=100, b=20, t=80),
    )

    return fig

def get_granalur_topics_graph_data(scholar_data,scholar_id,year,citation_count = False):
    scholar_data['author_id'] = scholar_data.author_pub_id.str.split(":").apply(lambda x: x[0])
    prof_pubs = scholar_data[scholar_data['author_id']==scholar_id]
    if citation_count:
        temp = pd.json_normalize(prof_pubs[['semantic_topics','pub_year','num_citations']].to_dict('records'),meta=['num_citations','pub_year'],record_path='semantic_topics').groupby([0,'pub_year']).mean().sort_values('num_citations',ascending=False)
    else:
        temp = pd.json_normalize(prof_pubs[['semantic_topics','pub_year','num_citations']].to_dict('records'),meta=['num_citations','pub_year'],record_path='semantic_topics').groupby([0,'pub_year']).count().sort_values('num_citations',ascending=False)
    temp_after = temp[temp.index.get_level_values(1)>=year].groupby([0]).sum().sort_values('num_citations',ascending=False).head(10)
    # print(temp_after)
    temp_before = temp[temp.index.get_level_values(1)<year].groupby([0]).sum().sort_values('num_citations',ascending=False)
    # print(temp_before)
    temp_before = temp_before.loc[set(temp_after.index).intersection(set(temp_before.index))]
    temp_before.index = temp_before.index.str.title()
    temp_after.index = temp_after.index.str.title()
    num_citations_after = temp_after.num_citations
    num_citations_before = temp_before.num_citations
    topics_after = temp_after.index
    topics_before = temp_before.index
    #set index name to 0
    chart_df = pd.DataFrame(index=topics_after)
    chart_df.index.name = 0
    chart_df['before'] = num_citations_before
    chart_df['before'] = chart_df['before']/chart_df['before'].sum()
    chart_df['after'] = num_citations_after
    chart_df['after'] = chart_df['after']/chart_df['after'].sum()
    chart_df.sort_values('after',ascending=False,inplace=True)
    chart_df.fillna(0,inplace=True)

    
    return chart_df

def get_generalized_topics(data,conf,conf_topics):
    tqdm.pandas()
    data['conf_id'] = None
    data.loc[data[data['type'].isin(['conference_paper'])].index,'conf_id']=data[data['type'].isin(['conference_paper'])]['crossref'].str.split("conf/").progress_apply(get_conf_id)
    merge_df = data.merge(conf.dropna(subset='DBLP'),left_on='conf_id',right_on='DBLP',how='left')
    conf_topics_dict = pd.Series(index=conf_topics['Area']).to_dict()
    conf_topics_dict.update(merge_df.merge(conf_topics[['Acronym','Area']],left_on='Acronym',right_on='Acronym',how='left').groupby(['Area']).count()[['@key']].rename(columns={'@key':'count'})['count'].to_dict())
    topics = pd.Series(conf_topics_dict).sort_values(ascending=False).dropna().index.to_list()
    values = pd.Series(conf_topics_dict).sort_values(ascending=False).dropna().to_list()
    
    fig = go.Figure(data=go.Scatterpolar(
        r=values,
        theta=topics,
        fill='toself'
    ))

    fig.update_layout(
    polar=dict(
        radialaxis=dict(
        visible=True
        ),
    ),
    height=400,
    width=300,
    showlegend=False,
    margin=dict(l=150, r=150, b=20, t=80),
    )
    return fig

def get_generalized_topics_data(data,conf,conf_topics):
    tqdm.pandas()
    data['conf_id'] = None
    data.loc[data[data['type'].isin(['conference_paper'])].index,'conf_id']=data[data['type'].isin(['conference_paper'])]['crossref'].str.split("conf/").progress_apply(get_conf_id)
    merge_df = data.merge(conf.dropna(subset='DBLP'),left_on='conf_id',right_on='DBLP',how='left')
    conf_topics_dict = pd.Series(index=conf_topics['Area']).to_dict()
    conf_topics_dict.update(merge_df.merge(conf_topics[['Acronym','Area']],left_on='Acronym',right_on='Acronym',how='left').groupby(['Area']).count()[['@key']].rename(columns={'@key':'count'})['count'].to_dict())
    topics = pd.Series(conf_topics_dict).sort_values(ascending=False).dropna().index.to_list()
    values = pd.Series(conf_topics_dict).sort_values(ascending=False).dropna().to_list()
    
    return topics,values
    
def get_generalized_topics_multiple(datas,conf,conf_topics,profs):
    tqdm.pandas()
    fig = go.Figure()
    categories = None
    for index,data in enumerate(datas):
        if data is None:
            continue
        data = pd.json_normalize(data,max_level=0)
        print(data.columns)
        data['conf_id'] = None
        data.loc[data[data['type'].isin(['conference_paper'])].index,'conf_id']=data[data['type'].isin(['conference_paper'])]['crossref'].str.split("conf/").progress_apply(get_conf_id)
        merge_df = data.merge(conf.dropna(subset='DBLP'),left_on='conf_id',right_on='DBLP',how='left')
        conf_topics_dict = pd.Series(index=conf_topics['Area'].unique()).to_dict()
        conf_topics_dict.update(merge_df.merge(conf_topics[['Acronym','Area']],left_on='Acronym',right_on='Acronym',how='left').groupby(['Area']).count()[['@key']].rename(columns={'@key':'count'})['count'].to_dict())
        topics = pd.Series(conf_topics_dict).dropna().index.to_list()
        values = pd.Series(conf_topics_dict).dropna()
        values = (values / values.sum())*100
        fig.add_trace(go.Barpolar(
            r=values,
            theta=topics,
            # fill='toself',
            name=profs[index]['Full Name'],
            # hover template to diaply name
            hovertemplate = f"<b>{profs[index]['Full Name']}</b><br>" +
                            "Topic: %{theta}<br>" +
                            "Paper : %{r:.2f}%<br>" +
                            "<extra></extra>",
        ))

    fig.update_layout(
    polar=dict(
        radialaxis=dict(
        visible=True
        ),
    ),
    height=400,
    width=300,
    showlegend=True,
    margin=dict(l=100, r=100, b=40, t=100),
    )
    fig.update_layout(
        title='Paper Percenatge Distribution Across Research Areas',
        font_size=12,
        legend_font_size=14,
        polar_radialaxis_ticksuffix='%',
        polar_angularaxis_rotation=90,

    )
    return fig