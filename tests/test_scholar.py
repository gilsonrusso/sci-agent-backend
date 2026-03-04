import pytest
from unittest.mock import patch, MagicMock
from app.agents.tools.scholar import search_academic_papers

# Mock data mimicking scholarly's return structure
MOCK_PUB_1 = {
    "bib": {
        "title": "The Impact of Machine Learning in Modern Science",
        "author": ["Doe, J.", "Smith, A."],
        "pub_year": "2024",
        "venue": "Journal of AI",
        "abstract": "This paper explores the foundational aspects of...",
    },
    "pub_url": "https://example.com/paper1",
    "num_citations": 145,
}

MOCK_PUB_2 = {
    "bib": {
        "title": "Advanced Techniques in Machine Learning",
        "author": ["Johnson, B."],
        "pub_year": "2023",
        "venue": "Conference on Deep Learning",
        "abstract": "A comprehensive review of recent advances in...",
    },
    "pub_url": "https://example.com/paper2",
    "num_citations": 56,
}


@pytest.mark.asyncio
@patch("app.agents.tools.scholar.scholarly")
@patch(
    "app.agents.tools.scholar.random.uniform", return_value=0.01
)  # Fix delays to speed up test
async def test_search_academic_papers_success(mock_uniform, mock_scholarly):
    """Test successful fetching of academic papers with mock data."""
    # Setup the mock generator that scholarly uses
    mock_generator = iter([MOCK_PUB_1, MOCK_PUB_2])
    mock_scholarly.search_pubs.return_value = mock_generator

    # Execute
    results = await search_academic_papers("machine learning", limit=2)

    # Assertions
    assert len(results) == 2
    assert results[0]["title"] == "The Impact of Machine Learning in Modern Science"
    assert results[0]["citation_count"] == 145
    assert results[0]["snippet"] == "This paper explores the foundational aspects of..."

    assert results[1]["title"] == "Advanced Techniques in Machine Learning"
    assert results[1]["authors"] == ["Johnson, B."]


@pytest.mark.asyncio
@patch("app.agents.tools.scholar.scholarly")
@patch("app.agents.tools.scholar.random.uniform", return_value=0.01)
async def test_search_academic_papers_handles_stop_iteration(
    mock_uniform, mock_scholarly
):
    """Test behavior when scholarly returns fewer results than the limit."""
    # Only 1 item in generator, but we ask for 5
    mock_generator = iter([MOCK_PUB_1])
    mock_scholarly.search_pubs.return_value = mock_generator

    # Execute
    results = await search_academic_papers("machine learning", limit=5)

    # Assertions
    assert len(results) == 1
    assert results[0]["title"] == "The Impact of Machine Learning in Modern Science"


@pytest.mark.asyncio
@patch("app.agents.tools.scholar.scholarly")
@patch("app.agents.tools.scholar.random.uniform", return_value=0.01)
async def test_search_academic_papers_handles_api_exception(
    mock_uniform, mock_scholarly
):
    """Test behavior when scholarly raises an exception (e.g., blocked by Google)."""
    # Setup scholarly to raise an Exception
    mock_scholarly.search_pubs.side_effect = Exception(
        "Cannot Fetch from Google Scholar"
    )

    # Execute and Assert
    with pytest.raises(Exception, match="Cannot Fetch from Google Scholar"):
        await search_academic_papers("machine learning")
