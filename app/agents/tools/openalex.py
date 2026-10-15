import logging
import asyncio
from typing import List, Dict, Any, Union
import httpx

logger = logging.getLogger(__name__)

# Semáforo global para evitar muitas requisições paralelas (throttle local)
OPENALEX_SEMAPHORE = asyncio.Semaphore(5)  # OpenAlex é mais tolerante

async def search_academic_papers_openalex(
    query: str, limit: int = 5
) -> Union[List[Dict[str, Any]], str]:
    """
    Pesquisa artigos acadêmicos usando a API oficial do OpenAlex.
    Implementa retries e controle de concorrência.
    """
    async with OPENALEX_SEMAPHORE:
        print(f"\033[1;36m[OpenAlex] Buscando por: '{query}' limit={limit}\033[0m", flush=True)
        url = "https://api.openalex.org/works"

        params = {
            "search": query,
            "per-page": limit,
        }

        max_retries = 3
        retry_delay = 1.5

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, params=params, timeout=15.0)
                    
                    if response.status_code == 429:
                        logger.warning(f"[OpenAlex] Rate Limit (429) na tentativa {attempt+1}")
                        if attempt < max_retries - 1:
                            await asyncio.sleep(retry_delay * (attempt + 1))
                            continue
                        else:
                            return "ERRO_RATE_LIMIT: O OpenAlex atingiu o limite. Tente novamente em breve."

                    response.raise_for_status()
                    data = response.json()

                    works = data.get("results", [])
                    results = []
                    for w in works:
                        authorships = w.get("authorships", [])
                        abstract_inverted = w.get("abstract_inverted_index")
                        snippet = "Resumo indisponível"
                        if abstract_inverted:
                            try:
                                words = [""] * (max([pos for arr in abstract_inverted.values() for pos in arr]) + 1)
                                for word, positions in abstract_inverted.items():
                                    for pos in positions:
                                        words[pos] = word
                                snippet = " ".join(words)[:500] + "..."
                            except Exception:
                                snippet = "Erro ao processar resumo."

                        venue_str = ""
                        primary_location = w.get("primary_location")
                        if primary_location and primary_location.get("source"):
                            venue_str = primary_location.get("source").get("display_name", "")

                        paper = {
                            "title": w.get("title") or w.get("display_name") or "Título desconhecido",
                            "authors": [a.get("author", {}).get("display_name", "") for a in authorships] or ["Autores desconhecidos"],
                            "year": w.get("publication_year"),
                            "venue": venue_str,
                            "snippet": snippet,
                            "url": w.get("doi") or w.get("id"),
                            "citation_count": w.get("cited_by_count") or 0,
                        }
                        results.append(paper)

                    logger.info(f"[OpenAlex] Busca concluída com {len(results)} resultados.")
                    return results

            except httpx.HTTPStatusError as e:
                logger.error(f"[OpenAlex] Erro HTTP: {e}")
                return f"ERRO_API_OPENALEX: A base retornou erro {e.response.status_code}."
            except Exception as e:
                logger.error(f"[OpenAlex] Erro na requisição: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                return f"ERRO_CONEXAO_OPENALEX: Falha ao conectar ao OpenAlex."

    return "ERRO_DESCONHECIDO"
