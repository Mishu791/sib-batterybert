# scripts/config.py

# These are the ONLY keywords that confirm a paper is SIB-relevant
# Every gate in the pipeline uses this same list
SIB_TITLE_KEYWORDS = [
    "sodium-ion battery",
    "sodium-ion batteries",
    "na-ion battery",
    "na-ion batteries",
    "sodium ion battery",
    "sodium ion batteries",
    "sodium battery",
    "hard carbon" ,         # always SIB context in battery papers
    "prussian blue analogue",
    "prussian blue analog",
    "nasicon",
    "p2-type",
    "o3-type",
    "p3-type",
    "sodium cathode",
    "sodium anode",
    "sodium electrolyte",
    "na-ion storage",
    "sodium storage",
]

# Phrase queries for APIs — specific enough to avoid false positives
CROSSREF_QUERIES = [
    "sodium-ion battery cathode",
    "sodium-ion battery anode",
    "sodium-ion battery electrolyte",
    "hard carbon sodium anode",
    "NASICON sodium battery",
    "Prussian blue analogue sodium",
    "P2-type layered oxide sodium",
    "O3-type sodium cathode",
    "Na-ion battery cathode",
]

SS_QUERIES = [
    "sodium-ion battery cathode materials",
    "sodium-ion battery hard carbon anode",
    "NASICON sodium electrolyte",
    "Prussian blue sodium storage",
    "P2 type layered oxide sodium-ion",
]

OA_QUERIES = [
    "sodium-ion battery",
    "Na-ion battery cathode",
    "hard carbon sodium anode",
    "NASICON sodium battery",
    "Prussian blue sodium",
]
