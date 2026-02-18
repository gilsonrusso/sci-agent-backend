from typing import List, Dict, Any


def search_scholar_mock(query: str) -> List[Dict[str, Any]]:
    """
    Simulates a search on Google Scholar.
    Returns static data for now to avoid API costs.
    """
    print(f"[MOCK TOOL] Searching Scholar for: {query}")
    return [
        {
            "title": f"The Impact of {query} in Modern Science",
            "authors": ["Doe, J.", "Smith, A."],
            "year": 2024,
            "url": "https://example.com/paper1",
            "snippet": "This paper explores the foundational aspects of...",
            "citation_count": 145,
        },
        {
            "title": f"Advanced Techniques in {query}",
            "authors": ["Johnson, B."],
            "year": 2023,
            "url": "https://example.com/paper2",
            "snippet": "A comprehensive review of recent advances in...",
            "citation_count": 56,
        },
        {
            "title": f"{query}: A Systematic Review",
            "authors": ["Brown, C.", "Davis, D."],
            "year": 2022,
            "url": "https://example.com/paper3",
            "snippet": "We analyze 500 papers published between 2010 and 2020...",
            "citation_count": 320,
        },
        {
            "title": "Methodologies for Researching Complex Systems",
            "authors": ["Wilson, E."],
            "year": 2023,
            "url": "https://example.com/paper4",
            "snippet": " proposing a new framework for analysis...",
            "citation_count": 89,
        },
        {
            "title": f"Future Trends in {query}",
            "authors": ["Garcia, M."],
            "year": 2025,
            "url": "https://example.com/paper5",
            "snippet": "Prediction of future directions based on current data...",
            "citation_count": 12,
        },
    ]
