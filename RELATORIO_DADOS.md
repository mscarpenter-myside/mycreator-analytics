# 📊 Relatório Técnico de Dados: MyCreator Analytics ETL

**Data:** 12/02/2026  
**Responsável:** Equipe de Engenharia de Dados  
**Versão:** 2.0 (Dual-Tab Architecture)

---

## 1. Visão Geral da Arquitetura

O pipeline de dados (ETL) foi rearquitetado para fornecer uma visão **dupla** da performance nas redes sociais, separando dados granulares (Posts) de dados consolidados de conta (Perfis).

O objetivo é permitir análises cruzadas como **"Alcance por Tamanho de Base de Seguidores"** e monitoramento da saúde das contas ao longo do tempo.

### Fluxo de Dados
1.  **Extração**: O script conecta-se à API do MyCreator simulando sessões de usuário autenticado.
2.  **Transformação**: Os dados brutos JSON são limpos, tipados e enriquecidos com cálculos de engajamento.
3.  **Carga (Load)**: Os dados são exportados para o Google Sheets em duas abas sincronizadas: **"Dados_Brutos"** (Posts) e **"Perfis"**.

---

## 2. Estrutura de Métricas e Fonte de Dados

### 📑 Aba 1: Perfis (Visão Agregada)
**Objetivo**: Monitoramento macro da saúde da conta e crescimento de base.  
**Janela de Dados**: Snapshot do momento da extração (Métricas de totais consideram últimos 30 dias).

| Campo (Coluna) | Descrição Técnica | Fonte Original (Endpoint) | Regra de Cálculo/Negócio |
| :--- | :--- | :--- | :--- |
| **Cidade** | Nome do Workspace | `Config` | Definido manualmente no ETL (ex: Florianópolis) |
| **Perfil** | Nome da Conta Instagram | `fetchSocialAccounts` | Campo `name` da conta vinculada |
| **Seguidores** | Total de Seguidores | `getSummary` | **Snapshot** do total de seguidores no momento da execução |
| **Total Posts** | Posts totais na conta | `getSummary` | Contagem total retornada pela API |
| **Engajamento Médio (%)** | Taxa de Engajamento Global | `getSummary` | Retornado pela API (Média dos últimos 30 dias) |
| **Total Engajamento (30d)** | Soma de interações | `getSummary` | Soma (Likes + Comentários + Salvos) nos últimos 30 dias |
| **Alcance Total (30d)** | Alcance acumulado | `getSummary` | Contas únicas alcançadas nos últimos 30 dias |
| **Impressões Totais (30d)** | Impressões acumuladas | `getSummary` | Total de exibições nos últimos 30 dias |
| **Atualizado em** | Data de Extração | `System` | Timestamp (UTC-3) da execução do robô |

**Endpoint Principal**:  
`POST /backend/analytics/overview/getSummary`  
*Payload customizado para extrair dados conta a conta, e não o agregado do workspace.*

---

### 📑 Aba 2: Posts (Dados_Brutos)
**Objetivo**: Análise granular de performance de conteúdo.  
**Janela de Dados**: Histórico completo disponível no setup do workspace.

| Campo (Coluna) | Descrição Técnica | Fonte Original (Endpoint) |
| :--- | :--- | :--- |
| **Cidade** | Workspace | `Config` |
| **Data de Publicação** | Data de veiculação | `/backend/plan/preview` |
| **Rede Social** | Plataforma (Instagram) | `/backend/plan/preview` |
| **Perfil** | Nome da Conta | `/backend/plan/preview` |
| **Seguidores** | **Snapshot por Post** | Cruzamento com `Data Perfis` |
| **Tipo** | Formato de Publicação | `/backend/plan/preview` |
| **Tipo de Mídia** | Formato de Mídia (Reels/Video) | `/backend/analytics/post/{id}` |
| **Título/Legenda** | Conteúdo textual | `/backend/plan/preview` |
| **Likes/Comentários/Salvos** | Métricas de Interação | `/backend/analytics/post/{id}` |
| **Alcance/Impressões** | Métricas de Visibilidade | `/backend/analytics/post/{id}` |
| **Plays** | Visualizações de Vídeo | `/backend/analytics/post/{id}` |

**Lógica de Cruzamento (Feature Nova)**:  
Para cada post extraído, o ETL consulta o mapa de seguidores gerado na extração de Perfis e injeta o número de seguidores daquele perfil na linha do post. Isso permite calcular o **"Alcance Relativo"** (Alcance / Seguidores) diretamente no post, sem PROCV.

---

## 3. Estrutura Lógica do Cruzamento

Para garantir a consistência dos dados, o ETL segue estritamente a ordem:

1.  **Etapa de Perfis (Master Data)**:
    *   Itera sobre todos os Workspaces.
    *   Busca todas as contas sociais (`fetchSocialAccounts`).
    *   Extrai métricas de saúde e **Seguidores** para cada conta.
    *   Armazena em memória um Dicionário: `{ "account_id": 12345_seguidores }`.

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

