import logging
import asyncio
from typing import List, Dict, Any, Union
import httpx

logger = logging.getLogger(__name__)

# Semáforo global para evitar muitas requisições paralelas (throttle local)
S2_SEMAPHORE = asyncio.Semaphore(2)

async def search_academic_papers_s2(query: str, limit: int = 5) -> Union[List[Dict[str, Any]], str]:
    """
    Pesquisa artigos acadêmicos usando a API oficial do Semantic Scholar (S2).
    Implementa retries com exponential backoff e controle de concorrência.
    """
    async with S2_SEMAPHORE:
        logger.info(f"[SemanticScholar] Buscando por: '{query}' limit={limit}")
        url = "https://api.semanticscholar.org/graph/v1/paper/search"

        params = {
            "query": query,
            "limit": limit,
            "fields": "title,authors,year,venue,abstract,url,citationCount",
        }

        max_retries = 3
        retry_delay = 2.0  # delay inicial

        for attempt in range(max_retries):
            try:
                async with httpx.AsyncClient() as client:
                    response = await client.get(url, params=params, timeout=15.0)
                    
                    if response.status_code == 429:
                        logger.warning(f"[SemanticScholar] Rate Limit (429) detectado na tentativa {attempt+1}")
                        if attempt < max_retries - 1:
                            wait_time = retry_delay * (2 ** attempt)
                            logger.info(f"[SemanticScholar] Aguardando {wait_time}s antes de tentar novamente...")
                            await asyncio.sleep(wait_time)
                            continue
                        else:
                            return "ERRO_RATE_LIMIT: O Semantic Scholar está sobrecarregado. Por favor, aguarde alguns minutos ou mude para o 'OpenAlex' nas configurações."

                    response.raise_for_status()
                    data = response.json()

                    papers = data.get("data", [])
                    results = []
                    for p in papers:
                        authors_list = p.get("authors", [])
                        paper = {
                            "title": p.get("title") or "Título desconhecido",
                            "authors": [a.get("name", "") for a in authors_list if a.get("name")] or ["Autores desconhecidos"],
                            "year": p.get("year"),
                            "venue": p.get("venue") or "",
                            "snippet": p.get("abstract") or "Sem resumo disponível (abstract não indexado).",
                            "url": p.get("url") or f"https://api.semanticscholar.org/CorpusID:{p.get('corpusId')}",
                            "citation_count": p.get("citationCount") or 0,
                        }
                        results.append(paper)
                    
                    logger.info(f"[SemanticScholar] Busca concluída com {len(results)} resultados.")
                    return results

            except httpx.HTTPStatusError as e:
                logger.error(f"[SemanticScholar] Erro HTTP: {e}")
                return f"ERRO_HTTP_{e.response.status_code}: Falha na comunicação com Semantic Scholar."
            except Exception as e:
                logger.error(f"[SemanticScholar] Erro inesperado: {e}")
                if attempt < max_retries - 1:
                    await asyncio.sleep(retry_delay)
                    continue
                return f"ERRO_CONEXAO: Falha técnica ao acessar a base de dados acadêmica."

    return "ERRO_DESCONHECIDO: Falha ao processar a busca."
