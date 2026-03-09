---
description: Como debugar erros 500 no SciAgent Backend
---

# Debugging 500 Errors

Sempre que houver um erro 500 no backend, siga estes passos para identificar a causa raiz:

1. **Verificar Logs do Terminal**:
   - Observe a saída do terminal onde o `uvicorn` está rodando.
   - Procure por `ValidationError` do Pydantic ou `traceback`.

2. **Verificar server.log**:
   - O arquivo `sci-agent-backend/server.log` contém os tracebacks completos.
   - Use o comando `tail -n 100 server.log` para ver as últimas mensagens.

3. **Logs Temporários nos Endpoints**:
   - Se o erro for silencioso, adicione um bloco `try-except` com `traceback.print_exc()` no endpoint afetado em `app/api/v1/endpoints/`.

4. **Payload de Erro do Pydantic**:
   - Erros do tipo `Input should be a valid list` ou `Input should be a valid string` indicam que o modelo de resposta (`response_model`) está recebendo dados em um formato inesperado do Agente de IA (ex: uma lista de blocos em vez de uma string).
