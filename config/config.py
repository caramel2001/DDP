from pathlib import Path

# from base import load_env
# from dotenv import load_dotenv

ROOT_DIR = Path(__file__).parent.parent
# print(ROOT_DIR)
# load_dotenv(ROOT_DIR.joinpath(".env"))

settings = {
    "PAPER_INDEX": str(ROOT_DIR.joinpath("assets/paper.index")),
    "PROF_INDEX": str(ROOT_DIR.joinpath("assets/prof.index")),
    "PAPER_DATA": str(ROOT_DIR.joinpath("data/paper_data.json")),
    "PROF_DATA": str(ROOT_DIR.joinpath("data/prof_data.csv")),
    "SCHOLAR_DATA": str(ROOT_DIR.joinpath("data/scholar.json")),
    "SCHOLAR_PUBS": str(ROOT_DIR.joinpath("data/scholar_publications.json")),
    "GRAPH_PATH": str(ROOT_DIR.joinpath("data/graphs")),
    "CONF_PATH": str(ROOT_DIR.joinpath("data/conf_processed.csv")),
    "CONF_TOPIC_PATH": str(ROOT_DIR.joinpath("data/conference_topic.csv")),

}
