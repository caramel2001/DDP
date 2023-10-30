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

# from cso_classifier import CSOClassifier
# cc = CSOClassifier(modules = "both", enhancement = "first", explanation = True)

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

def get_graph(paper_id):
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
    a = np.linspace(0.5,1,len(set(years)))
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

    G = nx.Graph()
    for i in nodes:
        abstract = split_string_into_lines(i['abstract'], words_per_line=15)
        hover_data = f"""Title : {i['title']} \n Pub Date : {i['publicationDate']} \n  Citations : {i['citations_length']} \n Authors :  {",".join([j['name'] for j in i['authors']])} \n Abstract : {abstract}"""
        if i['id'] == nodes[0]['id']:
            G.add_node(i['id'],label = f"{i['authors'][0]['name']} et al, {i['year']}",color="#e63946",size=i['citations_length']+20,x=i['pos'][0],y=i['pos'][1],title=hover_data)
            continue
        G.add_node(i['id'],label = f"{i['authors'][0]['name']} et al, {i['year']}",color=color_map[i['year']],size=i['citations_length']+20,x=i['pos'][0],y=i['pos'][1],title=hover_data)
    for i in data['edges'][:500]:
        G.add_edge(i[0],i[1],color=f"rgba(20, 33, 61,{i[2]*5})",title="Similarity : {:.3f}".format(i[2]))
    nt = Network(height="900px", width="100%", bgcolor="rgba(255,255,255,0)", font_color="#1d3557",filter_menu=True,neighborhood_highlight=True,notebook=True,cdn_resources='in_line')
    # populates the nodes and edges data structures
    nt.from_nx(G)
    # nt.barnes_hut()
    # for node,i in zip(nt.nodes,nodes):
            
    #         node["title"] = hover_data
    # nt.toggle_physics(True)
    # nt.show_buttons(filter_=True)

    nt.set_options("""
    const options = {
    "nodes": {
        "borderWidthSelected": 5,
        "opacity": 1,
        "font": {
        "size": 24,
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
        "avoidOverlap": 0.4
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



def get_treemap(data,conf_data):
    tqdm.pandas()
    def get_conf_id(i):
        if isinstance(i,list):
            if len(i)<=1:
                return None
            return i[1].split('/')[0]
        return None
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
    fig = px.treemap(treemap_df.fillna(' '), path=[px.Constant("Research Paper Distribution"),'type', 'Rank', 'Acronym'], values='count',labels='count',maxdepth=3,hover_data=['Title'],color='Type_Rank', color_discrete_sequence=px.colors.qualitative.Set3)

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

def get_granalur_topics_graph(scholar_data,scholar_id,year):
    scholar_data['author_id'] = scholar_data.author_pub_id.str.split(":").apply(lambda x: x[0])
    prof_pubs = scholar_data[scholar_data['author_id']==scholar_id]
    temp = pd.json_normalize(prof_pubs[['semantic_topics','pub_year','num_citations']].to_dict('records'),meta=['num_citations','pub_year'],record_path='semantic_topics').groupby([0,'pub_year']).count().sort_values('num_citations',ascending=False)
    temp_after = temp[temp.index.get_level_values(1)>=year].groupby([0]).sum().sort_values('num_citations',ascending=False).head(10)
    temp_before = temp[temp.index.get_level_values(1)<year].groupby([0]).sum().sort_values('num_citations',ascending=False)
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
    chart_df['after'] = num_citations_after
    chart_df.sort_values('before',ascending=False,inplace=True)
    chart_df.fillna(0,inplace=True)

    fig = go.Figure()
    categories = chart_df.index.to_list()
    fig.add_trace(go.Scatterpolar(
        r=chart_df.after.to_list(),
        theta=categories,
        fill='toself',
        name=f'{year} and After'
    ))
    fig.add_trace(go.Scatterpolar(
        r=chart_df.before.to_list(),
        theta=categories,
        fill='toself',
        name=f'Before {year}'
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