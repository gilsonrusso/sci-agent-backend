import logging
import asyncio
from typing import List, Dict, Any, Union
from tavily import TavilyClient
from app.core.config import settings

logger = logging.getLogger(__name__)

from langchain_core.tools import tool

# Semáforo para Tavily (opcional, mas bom manter padrão)
TAVILY_SEMAPHORE = asyncio.Semaphore(3)

@tool
async def execute_web_search(query: str, search_depth: str = "advanced", max_results: int = 5) -> Union[List[Dict[str, Any]], str]:
    """
    Realiza uma busca na web ou acadêmica usando o Tavily.
    """
    if not settings.TAVILY_API_KEY:
        return "ERRO_CONFIG: TAVILY_API_KEY não está configurada no ambiente."

    async with TAVILY_SEMAPHORE:
        print(f"\033[1;32m[Tavily] Buscando por: '{query}' depth={search_depth}\033[0m", flush=True)
        try:
            client = TavilyClient(api_key=settings.TAVILY_API_KEY)
            
            # Executa a busca síncrona em um thread para não bloquear o loop de eventos
            loop = asyncio.get_event_loop()
            response = await loop.run_in_executor(
                None, 
                lambda: client.search(
                    query=query, 
                    search_depth=search_depth, 
                    max_results=max_results,
                    include_answer=True
                )
            )
            
            raw_results = response.get("results", [])
            results = []
            
            for r in raw_results:
                results.append({
                    "title": r.get("title") or "Sem título",
                    "url": r.get("url") or "",
                    "snippet": r.get("content") or r.get("snippet") or "Sem resumo disponível.",
                    "authors": ["Web Content"],  # Tavily não retorna autores estruturados como S2
                    "year": None,
                    "score": r.get("score", 0)
                })
            
            logger.info(f"[Tavily] Busca concluída com {len(results)} resultados.")
            return results
            
        except Exception as e:
            logger.error(f"[Tavily] Erro inesperado: {e}")
            return f"ERRO_TAVILY: Falha ao processar busca no Tavily: {str(e)}"
