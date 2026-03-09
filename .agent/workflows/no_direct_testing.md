---
description: Regra de Ouro: Nunca testar chamando modelos diretamente
---

# Regra de Ouro: Testes e Limites de Taxa

Para respeitar os limites de taxa (rate limits) e custos do usuário, siga estas diretrizes:

1. **NUNCA execute chamadas de teste aos modelos de IA**:
   - Não use scripts ou ferramentas para invocar endpoints que chamam o LLM (como `/chat/invoke`) apenas para verificar se "está funcionando".
   - Limite seus testes a verificações de sintaxe, linting, tipos e lógica de código que não envolva chamadas de rede para modelos.

2. **Notifique o Usuário para Testar**:
   - Após realizar uma alteração em um endpoint de IA ou agente, descreva as mudanças e peça ao usuário para realizar o teste manual.
   - O usuário prefere gerenciar os testes para monitorar os limites de taxa.

3. **Use Logs para Depurar**:
   - Em vez de testar chamando o modelo, adicione logs detalhados e tracebacks para capturar informações durante os testes realizados pelo usuário.
