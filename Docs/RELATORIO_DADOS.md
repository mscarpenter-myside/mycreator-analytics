# 📊 Relatório Técnico de Dados: MyCreator Analytics ETL

**Data:** 13/02/2026  
**Responsável:** Equipe de Engenharia de Conteúdo
**Versão:** 3.3 (Unified Architecture)

---

## 1. Visão Geral da Arquitetura

O pipeline de dados (ETL) foi evoluído para fornecer uma visão **nônupla** da performance nas redes sociais, cobrindo Feed (Geral), Perfis, Stories, Hashtags, Reels, Imagens, Carrosseis, Destaques e Base Unificada.

O objetivo é permitir análises completas 360º:
*   **Feed:** Performance de longo prazo e cauda longa.
*   **Perfis:** Saúde da marca e crescimento de base.
*   **Stories:** Engajamento efêmero e frequência de publicação.
*   **Hashtags:** Alcance viral e descoberta de novos públicos.

### Fluxo de Dados Expandido
1.  **Extração**: Conexão multi-endpoint (Feed, Stories, Contas).
2.  **Transformação**:
    *   Enriquecimento de Posts com dados de Perfis.
    *   Mineração de texto (Regex) para extrair Hashtags.
    *   Filtragem especializada para separar Stories de Reels.
3.  **Carga (Load)**: Exportação síncrona para 4 abas no Google Sheets:
    *   `Dados_Brutos` (Posts Geral)
    *   `Perfis` (Snapshot da Conta)
    *   `Stories_Detalhado` (Stories 24h)
    *   `Reels_Detalhado` (Vídeos Curtos)
    *   `Imagens_Detalhado` (Fotos Feed)
    *   `Carrossel_Detalhado` (Álbuns)
    *   `Redes_Monitoramento` (Monitoramento Agregado)
    *   `Hashtags_Analitico` (Temas Virais)

---

## 2. Estrutura de Métricas

Para o detalhamento completo de cada coluna, consulte o documento **[DICIONARIO_DADOS.md](DICIONARIO_DADOS.md)**.

### Resumo das Fontes de Dados

| Aba Google Sheets | Fonte Principal (API Endpoint) | Tipo de Dado | Frequência |
| :--- | :--- | :--- | :--- |
| **Perfis** | `/backend/analytics/overview/getSummary` | Agregado (Conta) | Diária (Snapshot) |
| **Dados_Brutos** | `/backend/plan/preview` + `/post/{id}` | Transacional (Post) | Histórica Completa |
| **Stories_Detalhado** | `/backend/fetchPlans` (type=['story']) | Efêmero (Story) | Histórica (Metadados) |
| **Reels_Detalhado** | Filtro `media_type` IN ['REEL', 'VIDEO'] | Vídeo (Reel) | Histórica Completa |
| **Imagens_Detalhado** | Filtro `media_type`='IMAGE' | Imagem (Feed) | Histórica Completa |
| **Carrossel_Detalhado** | Filtro `media_type`='CAROUSEL' | Carrossel (Feed) | Histórica Completa |
| **Redes_Monitoramento** | Agrupamento por Cidade/Plataforma | **Monitoramento (KPIs)** | Recalculado a cada execução |
| **Hashtags_Analitico** | Regex sobre `Dados_Brutos` | Agregado (Tag) | Recalculado a cada execução |
| **Base_Looker_Unificada** | União Padronizada (Feed + Reels) | Tabela Mestra | **Fonte Principal Looker Studio** |

---

## 3. Lógica de Cruzamento e Processamento

A inteligência do ETL reside na capacidade de cruzar informações que a API entrega separadas.

### O Cruzamento de Hashtags (Feature Nova)
Diferente das outras métricas que vêm prontas, as hashtags são **mineradas**.
1.  O robô lê a legenda de *cada post*.
2.  Identifica padrões `#exemplo`.
3.  Cria uma tabela derivada onde **uma hashtag** soma a performance de **vários posts**.
    *   *Exemplo:* Se a hashtag `#floripa` foi usada em 10 posts que somaram 1000 likes, a linha `#floripa` na aba Hashtags terá 1000 de "Engajamento Total".

### O Tratamento de Stories (Feature Nova)
A API mistura Reels e Stories. O ETL aplica um filtro rigoroso (`published_post_type == 'STORY'`) para garantir que a aba `Stories_Detalhado` contenha apenas conteúdo nativo de 24h.

### O Tratamento de Reels (Feature Nova)
Para isolar a performance de vídeos curtos, o ETL cria a aba `Reels_Detalhado`, filtrando posts onde o tipo de mídia é `REEL` ou `VIDEO`. Isso permite analisar métricas específicas como **Tempo Assistido** e **Duração Média**, que não fazem sentido para imagens estáticas.

### Análise de Formatos (Feature Nova - Fase 3)
Além de Reels, agora separamos **Imagens** e **Carrosseis** em abas próprias. Isso facilita a comparação direta de ROI entre formatos.
*   *Exemplo:* Um gestor pode abrir a aba `Carrossel_Detalhado` e ver rapidamente se os álbuns estão gerando mais salvamentos que os Reels.

### Dashboard de Monitoramento (Feature Nova - Fase 3)
A aba `Redes_Monitoramento` foi evoluída para um **Painel de Monitoramento**. Em vez de listar posts individuais, ela agora apresenta os **Totais Consolidados** por cidade:
*   Total de Posts
*   Alcance Acumulado
*   Impressões Acumuladas
*   Engajamento Médio Global

2.  **Etapa de Posts (Transaction Data)**:
    *   Itera sobre todos os Posts publicados.
    *   Identifica o `account_id` do autor do post.
    *   **Enriquece** o post com o valor de seguidores do Dicionário (Lookup em O(1)).
    *   Busca métricas granulares de analytics do post.

3.  **Saída (Output)**:
    *   Gera dois DataFrames pandas independentes.
    *   Realiza o upload em paralelo para as abas respectivas no Google Sheets.

---

**Engenharia de Conteúdo & Automação**

