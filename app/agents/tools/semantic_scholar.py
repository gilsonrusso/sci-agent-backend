import logging
from typing import List, Dict, Any
import httpx

logger = logging.getLogger(__name__)


async def search_academic_papers_s2(query: str, limit: int = 5) -> List[Dict[str, Any]]:
    """
    Pesquisa artigos acadêmicos usando a API oficial do Semantic Scholar (S2).
    Gratuita, rápida e livre de bloqueios de rate-limit severos (100 reqs/5min default).
    """
    logger.info(f"[SemanticScholar] Buscando por: '{query}' limit={limit}")
    url = "https://api.semanticscholar.org/graph/v1/paper/search"

    # URL encoded parameters
    params = {
        "query": query,
        "limit": limit,
        "fields": "title,authors,year,venue,abstract,url,citationCount",
    }

    results = []
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=15.0)
            response.raise_for_status()
            data = response.json()

            papers = data.get("data", [])
            for p in papers:
                # Tratar autores (S2 retorna uma lista de dicionários)
                authors_list = p.get("authors", [])
                authors_str = ", ".join(
                    [a.get("name", "") for a in authors_list if a.get("name")]
                )
                if not authors_str:
                    authors_str = "Autores desconhecidos"

                paper = {
                    "title": p.get("title") or "Título desconhecido",
                    "authors": authors_str,
                    "year": p.get("year"),
                    "venue": p.get("venue") or "",
                    "snippet": p.get("abstract")
                    or "Sem resumo disponível (abstract não indexado).",
                    "url": p.get("url")
                    or f"https://api.semanticscholar.org/CorpusID:{p.get('corpusId')}",
                    "citation_count": p.get("citationCount") or 0,
                }
                results.append(paper)

    except httpx.HTTPStatusError as e:
        logger.error(f"[SemanticScholar] Rate Limit ou Erro HTTP: {e}")
        return [
            {
                "title": "Erro de Conexão na API",
                "authors": "Sistema",
                "year": 2024,
                "venue": "Erro",
                "snippet": f"A API do Semantic Scholar retornou um erro (HTTP {e.response.status_code}). Isso ocorre frequentemente por limites de taxa (Rate Limit). O usuário foi aconselhado a tentar OpenAlex no Frontend.",
                "url": "",
                "citation_count": 0,
            }
        ]
    except Exception as e:
        logger.error(f"[SemanticScholar] Erro na requisição: {e}")
        return [
            {
                "title": "Erro Interno da API",
                "authors": "Sistema",
                "year": 2024,
                "venue": "Erro",
                "snippet": f"Falha ao conectar no Semantic Scholar: {str(e)}",
                "url": "",
                "citation_count": 0,
            }
        ]

    return results
