
import streamlit as st
st.set_page_config(layout="wide")

markdown_text = """
# Academic Dashboard

Welcome to SCSE academic dashboard, where you can search for professors and research papers, explore information about professors, and view citation graphs of Research Papers.

The Dashboard contains the following pages:
- **SCSE**: View SCSE statistics and conference information.
- **Search**: Search for professors and research papers.
- **Professor**: View detailed information about a selected professor.
- **Paper**: View detailed information about a selected research paper.
- **Compare**: Compare Research Focus and Citations upto 3 professors.

### Search Professors and Papers
#### Professor and Paper Search Engine Pipeline
![Search Engine Image](app/static/image.png)
---

### Professor Profile

- **Indexes**
- **Citations Counts**
- **Publications Counts**
- **Research Interests**
- **Coauthors**
- **Conference Publications**


### SCSE Profile

Display Overall SCSE Statistics and Conference Information.


### Research Paper Information
Get information about a selected research paper, including its title, authors, and abstract.
And a Paper Network Graph to visualize the citation relationships of the selected research paper.


### How to Use
1. Start by using the search engine to look for professors or research papers.
2. Select a professor or paper from the search results. 
3. Explore detailed information and related graphs on the respective professor or paper pages.
"""

# Display the markdown
st.markdown(markdown_text)

# Run the Streamlit app
if __name__ == '__main__':
    

    pass  # Add Streamlit specific configuration here
