from search.graph import get_generalized_topics_data,get_granalur_topics_graph_data
import networkx as nx
import community
import pyvis
import pickle
from config.config import settings
from bs4 import BeautifulSoup

def get_community(prof_data,scholar_data,dblp_data,conf_data,conf_topic):
    professors_granular={}
    for index,i in enumerate(prof_data['scholar_id']):
        if pd.isna(i):
            continue
        topic = topics = get_granalur_topics_graph_data(scholar_data,i,year=2018,citation_count=False)

        professors_granular[prof_data.iloc[index]['Full Name']] = topics.index.to_list()
    professors={}
    for index,i in enumerate(dblp_data):
        if i is None:
            continue
        prof_pubs = transform_data(i)
        topics,values = get_generalized_topics_data(pd.json_normalize(prof_pubs,max_level=0),conf_data,conf_topic)
        if 'General Computer Science' in topics:
            topics.remove('General Computer Science')
        professors[prof_data.iloc[index]['Full Name']] = topics[:2]

    # Create an empty graph
    G = nx.Graph()

    # Add nodes for professors
    G.add_nodes_from(professors.keys())

    # Add weighted edges based on shared research interests
    for prof1, interests1 in professors.items():
        for prof2, interests2 in professors.items():
            if prof1 != prof2:
                if G.has_edge(prof2,prof1):
                        continue
                intrests = set(interests1) & set(interests2)
                shared_interests = len(set(interests1) & set(interests2))
                if shared_interests > 1:
                    print(prof1,prof2,intrests)
                    G.add_edge(prof1, prof2, weight=shared_interests-1)

    # Add weighted edges based on shared research interests
    for prof1, interests1 in professors_granular.items():
        for prof2, interests2 in professors_granular.items():
            if prof1 != prof2:
                shared_interests = len(set(interests1) & set(interests2))
                # print(shared_interests)
                if shared_interests > 4:
                    if G.has_edge(prof2,prof1):
                        continue
                    print(prof1,prof2,shared_interests)
                    G.add_edge(prof1, prof2, weight=shared_interests-3)
    
    partition = community.best_partition(G)

    # 1. Identify the singleton communities
    singleton_communities = [com for com, nodes in partition.items() if list(partition.values()).count(nodes) == 1]
    # Add weighted edges based on shared research interests
    for prof1, interests1 in professors_granular.items():
        if prof1 not in singleton_communities:
            continue
        for prof2, interests2 in professors_granular.items():
            if prof1 != prof2:
                shared_interests = len(set(interests1) & set(interests2))
                # print(shared_interests)
                if shared_interests > 2:
                    if G.has_edge(prof2,prof1):
                        continue
                    print(prof1,prof2,shared_interests)
                    G.add_edge(prof1, prof2, weight=shared_interests-3)
    professors={}
    for index,i in enumerate(dblp_coauthors['publication_json']):
        if i is None:
            continue
        prof_pubs = transform_data(i)
        topics,values = get_generalized_topics_data(pd.json_normalize(prof_pubs,max_level=0),conf_data,conf_topic)
        if 'General Computer Science' in topics:
            topics.remove('General Computer Science')
        professors[prof_data.iloc[index]['Full Name']] = topics[:5]
        
    # Add weighted edges based on shared research interests
    for prof1, interests1 in professors.items():
        if prof1 not in singleton_communities:
            continue
        for prof2, interests2 in professors.items():
            if prof1 != prof2:
                if G.has_edge(prof2,prof1):
                        continue
                intrests = set(interests1) & set(interests2)
                shared_interests = len(set(interests1) & set(interests2))
                if shared_interests >= 4:
                    print(prof1,prof2,intrests)
                    G.add_edge(prof1, prof2, weight=shared_interests-3)
    partition = community.best_partition(G)
    G.add_edge("Anwitaman Datta","Huang Shell Ying",weight=1)
    with open(settings['COMMUNITY'], 'wb') as f:
        pickle.dump(G, f, pickle.HIGHEST_PROTOCOL)
        
def get_community_graph():
    with open(settings['COMMUNITY'], 'rb') as f:
        g = pickle.load(f)

    # Create a pyvis network object
    net = pyvis.network.Network(notebook=True)
    net.from_nx(g)
    net.set_options("""
    const options = {
    "nodes": {
        "borderWidth": null,
        "borderWidthSelected": null,
        "opacity": 1,
        "font": {
        "size": 28
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
        "forceAtlas2Based": {
        "centralGravity": 0.025,
        "springLength": 100,
        "avoidOverlap": 0.19
        },
        "minVelocity": 0.75,
        "solver": "forceAtlas2Based"
    }
    }
    """)
    # Get the full path of the current script
    html = net.generate_html('community.html')
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
    return modified_html_string