# Relatório Técnico: Coleta de Dados e Diferenças (MyCreator vs Geral)

Este documento detalha como o robô (ETL) extrai os dados atualmente e por que existe uma diferença entre os dados "MyCreator" e os dados "Gerais".

## 1. Coleta de Publicações MyCreator (Foco Interno)

A extração das postagens gerenciadas pelo time MySide ocorre através do endpoint de **Planejamento** (`/backend/fetchPlans`).

*   **Fonte**: O robô acessa a lista de "Plans" (Posts) que foram criados e agendados dentro da ferramenta MyCreator.
*   **Filtro Principal**: `status = "published"` (Apenas posts já publicados).
*   **Limitação Técnica**: O endpoint entrega uma lista dos **últimos X posts** (definido por limite, ex: 300).
*   **O que ele vê**: Apenas o que foi postado *via ferramenta*. Se alguém pegar o celular e postar um Story direto no Instagram, **esse post não aparece aqui**.
*   **Para que serve**: Para medir a eficiência e performance do *trabalho do time*.
    *   Gera as abas: `Dados_Brutos`, `Historico_Diario_MyCreator`, `Top_Posts_MyCreator`.

## 2. Coleta de Dados Gerais (Visão Macro)

A extração dos dados gerais do perfil ocorre através do endpoint de **Analytics Overview** (`/backend/analytics/overview/getSummary`).

*   **Fonte**: API oficial do Instagram/Facebook (via MyCreator).
*   **O que ele vê**: **TUDO**. Posts do MyCreator, posts feitos pelo celular, reposts, collabs, etc.
*   **Limitação**: Ele entrega números **agregados** (Soma Total) para um período (ex: Últimos 30 dias). Ele *não* entrega lista de posts individualizados postados fora da ferramenta.
*   **Para que serve**: Para Benchmarking e visão de crescimento real da conta.
    *   Gera a aba: `Visao_Geral_Perfil`.

## 3. O Desafio do Comparativo

Queremos responder: *"Qual % do resultado do perfil veio do trabalho da MySide?"*

*   **Problema**:
    *   O **Geral** nos dá a soma do período (ex: Jan 1 - Jan 30).
    *   O **MyCreator** nos dá uma lista de posts.
*   **Solução Proposta**:
    1.  Definir uma janela exata (ex: **Últimos 30 dias**).
    2.  No ETL, somar manualmente o alcance de todos os posts da lista **MyCreator** que foram publicados nestes 30 dias.
    3.  Extrair o **Geral** especificamente para estes mesmos 30 dias.
    4.  Dividir um pelo outro: `(Alcance MyCreator / Alcance Geral) * 100` = **Share of Voice**.

## 4. Próximo Passo Sugerido

Para viabilizar essa comparação justa, precisamos padronizar a extração dos dados "Gerais".

**Recomendação**:
Criar uma nova aba **`Comparativo_Mensal`** que:
1.  Busca o **Total Geral dos Últimos 30 Dias** (dado API).
2.  Calcula o **Total MyCreator dos Últimos 30 Dias** (soma dos posts extraídos).
3.  Mostra o percentual de contribuição.
