import logging
from typing import List, Dict, Any
import httpx

logger = logging.getLogger(__name__)


async def search_academic_papers_openalex(
    query: str, limit: int = 5
) -> List[Dict[str, Any]]:
    """
    Pesquisa artigos acadêmicos usando a API oficial do OpenAlex.
    Gratuita, rápida, não exige sequer chave de API (embora seja ideal enviar um e-mail de cortesia caso a escala seja massiva).
    """
    logger.info(f"[OpenAlex] Buscando por: '{query}' limit={limit}")
    url = "https://api.openalex.org/works"

    params = {
        "search": query,
        "per-page": limit,
        # Você pode opcionalmente exigir is_oa (Open Access): "filter": "is_oa:true"
    }

    results = []
    try:
        async with httpx.AsyncClient() as client:
            response = await client.get(url, params=params, timeout=15.0)
            response.raise_for_status()
            data = response.json()

            works = data.get("results", [])
            for w in works:

                # Tratar autores (OpenAlex retorna `authorships`)
                authorships = w.get("authorships", [])
                authors_str = ", ".join(
                    [a.get("author", {}).get("display_name", "") for a in authorships]
                )
                if not authors_str:
                    authors_str = "Autores desconhecidos"

                # Tratar Inverted Abstract (OpenAlex não manda a string do resumo puro para economizar tráfego)
                # Eles mandam um dicionário onde a key é a palavra e o value é um array de posições onde a palavra ocorre.
                # Como pode ser complexo reconstruir, se a API retornou, não precisamos dele perfeito para a tool de demonstração.
                abstract_inverted = w.get("abstract_inverted_index")
                snippet = "Resumo indisponível"
                if abstract_inverted:
                    # Um método grosseiro de reconstrução:
                    words = [
                        ""
                        for _ in range(
                            max(
                                [
                                    pos
                                    for arr in abstract_inverted.values()
                                    for pos in arr
                                ]
                            )
                            + 1
                        )
                    ]
                    for word, positions in abstract_inverted.items():
                        for pos in positions:
                            words[pos] = word
                    snippet = (
                        " ".join(words)[:500] + "..."
                    )  # Limitamos para não estourar tokens do contexto

                # Local primário
                venue_str = ""
                primary_location = w.get("primary_location")
                if primary_location and primary_location.get("source"):
                    venue_str = primary_location.get("source").get("display_name", "")

                paper = {
                    "title": w.get("title")
                    or w.get("display_name")
                    or "Título desconhecido",
                    "authors": [
                        a.get("author", {}).get("display_name", "") for a in authorships
                    ]
                    or ["Autores desconhecidos"],
                    "year": w.get("publication_year"),
                    "venue": venue_str,
                    "snippet": snippet,
                    "url": w.get("doi") or w.get("id"),
                    "citation_count": w.get("cited_by_count") or 0,
                }
                results.append(paper)

    except httpx.HTTPStatusError as e:
        logger.error(f"[OpenAlex] Rate Limit ou Erro HTTP: {e}")
        return f"ERRO_API_OPENALEX: A base retornou erro {e.response.status_code}. Tente trocar para Semantic Scholar ou refine a busca."
    except Exception as e:
        logger.error(f"[OpenAlex] Erro na requisição: {e}")
        return f"ERRO_CONEXAO_OPENALEX: Não foi possível conectar ao OpenAlex: {str(e)}"

    return results
