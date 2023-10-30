
import streamlit as st
st.set_page_config(layout="wide")

markdown_text = """
# Academic Dashboard

Welcome to my academic dashboard, where you can search for professors and research papers, explore information about professors, and view citation graphs.

## Search Professors and Papers
### Professor and Paper Search Engine
![Search Engine Image](app/static/image.png)

Use the search engine to find professors and research papers by entering keywords or names.

---

## Professor Information
### Professor Details
View detailed information about a selected professor.

### Coauthor Graph
Explore a graph that visualizes the coauthor relationships of the selected professor.

---

## Research Paper Information
### Research Paper Details
Get information about a selected research paper, including its title, authors, and abstract.

### Citation Graph
Visualize the citation relationships of the selected research paper.

---

## How to Use
1. Start by using the search engine to look for professors or research papers.
2. Select a professor or paper from the search results.
3. Explore detailed information and related graphs on the respective professor or paper pages.

---
"""

# Display the markdown
st.markdown(markdown_text)

# Run the Streamlit app
if __name__ == '__main__':
    

    pass  # Add Streamlit specific configuration here
