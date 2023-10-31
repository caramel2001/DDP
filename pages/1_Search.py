import streamlit as st
import pandas as pd
import os
from config.config import settings
from utils import read_pubs_data,read_prof_data,extract_titles
from search.index import get_embeddings, create_index, query, save_index, load_index
# import streamlit_antd_components as sac
from components.card import get_card,get_paper_card,get_paper_card_google
st.set_page_config(layout="wide")
st.session_state['profId'] = None
st.session_state['PaperId'] = None

# print(settings)
def main():
    # paper_data = read_pubs_data(settings['PAPER_DATA'])
    paper_data = pd.read_json(settings['SCHOLAR_PUBS'])
    # print(paper_data[0])
    prof_data = read_prof_data(settings['PROF_DATA'])

    if not os.path.exists(settings['PROF_INDEX']): # if prof_index not present
        with st.spinner('Indexing Professor Names for Searching'):
            prof_data = pd.read_csv(settings['PROF_DATA'])
            prof_embeddings = get_embeddings('all-MiniLM-L6-v2',prof_data['Full Name'].dropna().tolist())
            prof_index = create_index(prof_embeddings)
            print('index created')
            save_index(prof_index,settings['PROF_INDEX'])
    else:
        prof_index = load_index(None,settings['PROF_INDEX'])

    if not os.path.exists(settings['PAPER_INDEX']): # if paper_index not present
        with st.spinner('Indexing Research papers for Searching'):
            paper_embeddings = get_embeddings('all-MiniLM-L6-v2',paper_data['title'].to_list())
            paper_index = create_index(paper_embeddings)
            
            save_index(paper_index,settings['PAPER_INDEX'])
    else:
        paper_index = load_index(None,settings['PAPER_INDEX'])

    st.subheader('Search Professors and Research Papers')
    option = st.sidebar.selectbox(
    'What would you like to search🔎',
    ('Professor','Research paper'),index=None,placeholder="Please select a search option")
    search_input = None
    if option == 'Professor':
        search_input = st.sidebar.text_input("Search by professor name")
        num_results = st.sidebar.slider("Number of search results", 5, 50, 5)
        sort_order = st.sidebar.selectbox('Sort By',('relevance', 'date','citations'))
    if option == 'Research paper':
        search_input = st.sidebar.text_input("Search by paper title")
        num_results = st.sidebar.slider("Number of search results", 5, 50, 5)
        sort_order = st.sidebar.selectbox('Sort By',('relevance', 'date','citations'))
       
    # page_number = sac.pagination(total=num_results, align='center', jump=True, show_total=True)

    # custom css for Seardch results
    # css_body_container = '''
    # <style>
    #     [data-testid="stSidebar"] + section [data-testid="stVerticalBlock"]
    #     [data-testid="stVerticalBlock"] {
    #         background-color:rgba(255,255,255,1);
    #         border: 1px solid #F51E1E;
    #         border-radius: 5px;
    #         box-shadow: 0 0 5px rgba(0,0,0,0.2);
    #         padding: 20px;
    #         min-height : 0px;
    #         }
    # </style>
    # '''
    # st.markdown(css_body_container,unsafe_allow_html=True)
    if search_input:
        if option == 'Professor':
            # print(prof_input,sort_order)
            results = query(index =prof_index,query_string=search_input,model='all-MiniLM-L6-v2',k=num_results)
            temp =pd.merge(prof_data,results,left_index=True,right_on='ann')
            if sort_order =='relevance':
                temp.sort_values(by='distances',ascending=True,inplace=True)
            # print(temp['personal_websites'])
            # st.dataframe(temp)
            for i in range(0,num_results,3):
                col1, col2, col3 = st.columns(3)
                if not i>=num_results:
                    with col1:
                        get_card(temp.iloc[i])
                if not i+1>=num_results:
                    with col2:
                        get_card(temp.iloc[i+1])
                if not i+2>=num_results:
                    with col3:
                        get_card(temp.iloc[i+2])
            # print(st.session_state.get('profId'))
        if option == 'Research paper':
            # print(search_input,sort_order)
            results = query(index=paper_index,query_string=search_input,model='all-MiniLM-L6-v2',k=num_results)
            # temp =pd.merge(prof_data,results,left_index=True,right_on='ann')
            if sort_order =='relevance':
                results.sort_values(by='distances',ascending=True,inplace=True)
            # print(results)
            # # st.dataframe(temp)
            for i in range(0,num_results,3):
                col1, col2, col3 = st.columns(3,gap='large')
                if not i>=num_results:
                    with col1:
                        get_paper_card_google(paper_data.iloc[int(results.iloc[i]['ann'])].to_dict(),int(results.iloc[i]['ann']))
                        #st.json(paper_data[int(results.iloc[i]['ann'])],expanded=False)
                if not i+1>=num_results:
                    with col2:
                        get_paper_card_google(paper_data.iloc[int(results.iloc[i+1]['ann'])],int(results.iloc[i+1]['ann']))
                        #st.json(paper_data[int(results.iloc[i+1]['ann'])],expanded=False)
                if not i+2>=num_results:
                    with col3:
                        get_paper_card_google(paper_data.iloc[int(results.iloc[i+2]['ann'])],int(results.iloc[i+2]['ann']))
                        #st.json(paper_data[int(results.iloc[i+2]['ann'])],expanded=False)
    print(st.session_state.get('profId'))
    print(st.session_state.get('paperId'))
    # temp  = pd.json_normalize(paper_data)
    # print(temp[temp['title'].str.lower().str.contains("fine-grained physical memory reservation").fillna(False)])
    
if __name__ == '__main__':
    main()