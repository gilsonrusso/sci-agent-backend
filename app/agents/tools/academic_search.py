import logging
import asyncio
from typing import List, Dict, Any, Union
from langchain_core.tools import tool
from app.agents.tools.semantic_scholar import search_academic_papers_s2
from app.agents.tools.openalex import search_academic_papers_openalex

logger = logging.getLogger(__name__)

@tool
async def execute_academic_search(query: str, limit: int = 5) -> Union[List[Dict[str, Any]], str]:
    """
    Executa uma busca bibliográfica em bases de dados acadêmicas (Semantic Scholar e OpenAlex).
    A ferramenta tenta primeiro o Semantic Scholar e usa o OpenAlex como fallback em caso de erro.
    """
    logger.info(f"[AcademicSearch] Iniciando busca unificada para: {query}")
    
    # 1. Tenta Semantic Scholar
    try:
        results = await search_academic_papers_s2(query, limit)
        
        # Se retornou uma lista com resultados, sucesso!
        if isinstance(results, list) and len(results) > 0:
            logger.info(f"[AcademicSearch] Sucesso no Semantic Scholar ({len(results)} resultados)")
            return results
        
        # Se retornou erro de Rate Limit, vamos pro Fallback
        if isinstance(results, str) and "RATE_LIMIT" in results:
            logger.warning("[AcademicSearch] Semantic Scholar retornou Rate Limit. Tentando OpenAlex...")
        elif isinstance(results, list) and len(results) == 0:
            logger.info("[AcademicSearch] Semantic Scholar não encontrou resultados. Tentando OpenAlex...")
        else:
            logger.warning(f"[AcademicSearch] Semantic Scholar falhou com: {results}. Tentando OpenAlex...")
            
    except Exception as e:
        logger.error(f"[AcademicSearch] Exceção no Semantic Scholar: {str(e)}")

    # 2. Fallback para OpenAlex
    try:
        logger.info(f"[AcademicSearch] Executando Fallback OpenAlex para: {query}")
        fallback_results = await search_academic_papers_openalex(query, limit)
        
        if isinstance(fallback_results, list):
            logger.info(f"[AcademicSearch] Sucesso no OpenAlex ({len(fallback_results)} resultados)")
            return fallback_results
        
        return f"ERRO_TOTAL: Ambas as bases falharam. Semantic Scholar: {results if 'results' in locals() else 'Exception'}. OpenAlex: {fallback_results}"
        
    except Exception as e:
        logger.error(f"[AcademicSearch] Exceção total no fallback: {str(e)}")
        return f"ERRO_FATAL: Falha crítica na orquestração de busca: {str(e)}"
