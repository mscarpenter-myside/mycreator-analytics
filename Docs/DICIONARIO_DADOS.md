
# 📖 Dicionário de Dados: MyCreator Analytics ETL

Este documento detalha **cada coluna** gerada pelo robô de ETL nas 4 abas do Google Sheets. Utilize este guia para criar dashboards no Looker Studio ou Power BI.

---

## 🧩 Diagrama de Funcionamento

```mermaid
graph TD
    API[MyCreator API] -->|JSON| ETL[Robô ETL Python]
    
    subgraph Processamento
        ETL -->|Limpeza & Tipagem| P1[Posts]
        ETL -->|Regex & Agregação| H1[Hashtags]
    ETL -->|Filtro Type='story'| S1[Stories]
        ETL -->|Filtro Type='reel'| R1[Reels]
        ETL -->|Filtro Type='image'| I1[Imagens]
        ETL -->|Filtro Type='carousel'| C1[Carrossel]
        ETL -->|Monitoramento| D1[Monitoramento]
        ETL -->|Snapshot| PR1[Perfis]
    end
    
    P1 -->|Upload| GS1[📄 Aba: Dados_Brutos]
    PR1 -->|Upload| GS2[📄 Aba: Perfis]
    H1 -->|Upload| GS3[📄 Aba: Hashtags_Analitico]
    S1 -->|Upload| GS4[📄 Aba: Stories_Detalhado]
    R1 -->|Upload| GS5[📄 Aba: Reels_Detalhado]
    I1 -->|Upload| GS6[📄 Aba: Imagens_Detalhado]
    C1 -->|Upload| GS7[📄 Aba: Carrossel_Detalhado]
    D1 -->|Upload| GS8[📄 Aba: Redes_Monitoramento]
```

---

## 📑 1. Aba: `Perfis` (MyCreator + Seguidores)
**Granularidade:** Uma linha por Perfil.
*Combina o total de seguidores (dado geral) com a performance acumulada apenas dos posts feitos via MyCreator.*

| Coluna | Descrição | Exemplo |
| :--- | :--- | :--- |
| **Cidade** | Nome do Workspace. | `Florianópolis` |
| **Perfil** | Nome da conta. | `myside.imoveis` |
| **Seguidores (Total)** | Total de seguidores da conta (API Geral). | `15400` |
| **Posts MyCreator** | Qtd. posts publicados pela ferramenta. | `12` |
| **Engajamento Médio MyCreator (%)** | `(Interações MyCreator / Alcance MyCreator)`. | `4.5` |
| **Taxa de Alcance MyCreator (%)** | `((Alcance Médio / Seguidores) * 100)`. | `15.2` |
| **Alcance Acumulado MyCreator** | Soma do alcance dos posts da ferramenta. | `45000` |
| **Interações Totais MyCreator** | Soma de likes, comments, shares, saves. | `2300` |
| **Atualizado em** | Data da extração. | `13/02/2026 02:00:00` |

---

## 📑 2. Aba: `Dados_Brutos` (Posts de Feed/Reels)
**Granularidade:** Uma linha por Post publicado.

| Coluna | Descrição | Exemplo |
| :--- | :--- | :--- |
| **Cidade** | Nome do Workspace de origem. | `Florianópolis`, `Curitiba` |
| **Data de Publicação** | Data e hora exata da publicação. | `12/02/2026 14:30:00` |
| **Rede Social** | Plataforma onde foi postado. | `Instagram`, `Facebook` |
| **Perfil** | Nome da conta (@arroba ou Nome). | `@myside.imoveis` |
| **Seguidores** | *Snapshot* de seguidores no dia da extração. | `15400` |
| **Tipo** | Formato geral do conteúdo. | `image`, `video`, `carousel` |
| **Tipo de Mídia** | Formato específico técnico. | `REELS`, `FEED_IMAGE` |
| **Título** | Primeira linha ou título do post. | `Confira as novidades...` |
| **Legenda** | Texto completo do post. | `Confira as novidades... #imoveis` |
| **Likes** | Quantidade de curtidas. | `120` |
| **Comentários** | Quantidade de comentários. | `5` |
| **Salvos** | Quantidade de salvamentos. | `12` |
| **Compartilhamentos** | Quantidade de envios. | `8` |
| **Alcance** | Contas únicas alcançadas. | `2500` |
| **Impressões** | Total de visualizações. | `3000` |
| **Plays** | Visualizações de vídeo (Reels). | `5000` |
| **Taxa de Alcance (%)** | `(Alcance / Seguidores) * 100`. | `12.5` |
| **Engajamento (%)** | `(Likes + Coments + Saves) / Alcance`. | `4.5` |
| **ID Post** | Identificador único do post (excl. ID). | `1784...` |
| **Link Permanente** | URL direta para o post. | `https://instagram.com/p/...` |
| **Atualizado em** | Data da última leitura pelo robô. | `13/02/2026 02:00:00` |

---

## 📑 2. Aba: `Stories_Detalhado` (Stories 24h)
**Granularidade:** Uma linha por Story publicado.
*Nota: Métricas de engajamento podem estar zeradas devido a limitações da API para histórico.*

| Coluna | Descrição | Exemplo |
| :--- | :--- | :--- |
| **Cidade** | Nome do Workspace. | `Florianópolis` |
| **Data** | Data e hora da publicação. | `12/02/2026 09:00:00` |
| **Perfil** | Conta que publicou. | `@myside.imoveis` |
| **Link** | Link para o story (se válido). | `https://instagram.com/stories/...` |
| **Preview** | URL da imagem do story (Capa). | `https://cdn.instagram...jpg` |
| **ID Story** | Identificador único. | `1798...` |
| **Alcance** | Contas alcançadas (Se disponível). | `0` (API Limitada) |
| **Impressões** | Visualizações totais (Se disponível). | `0` (API Limitada) |
| **Saídas** | Toques para sair (Exit). | `0` |
| **Respostas** | Directs enviados pelo story. | `0` |
| **Avançar** | Taps para pular (Forward). | `0` |
| **Voltar** | Taps para voltar (Back). | `0` |
| **Atualizado em** | Data da extração. | `13/02/2026 02:00:00` |

---

## 📑 3. Aba: `Hashtags_Analitico`
**Granularidade:** Uma linha por Hashtag encontrada (Agregado).
*Analisa quais temas geram mais resultado.*

| Coluna | Descrição | Exemplo |
| :--- | :--- | :--- |
| **Hashtag** | A tag em si (sem o #). | `imoveis` |
| **Qtd Usos** | Quantos posts usaram esta tag. | `15` |
| **Engajamento Total** | Soma do engajamento desses posts. | `850` |
| **Alcance Acumulado** | Soma do alcance desses posts. | `15000` |
| **Impressões Acumuladas** | Soma das impressões. | `20000` |
| **Total Likes** | Soma de likes. | `800` |
| **Total Comentários** | Soma de comentários. | `50` |

---

## 📑 4. Aba: `Perfis` (Snapshot da Conta)
**Granularidade:** Uma linha por Perfil/Conta conectada.

| Coluna | Descrição | Exemplo |
| :--- | :--- | :--- |
| **Cidade** | Workspace. | `Florianópolis` |
| **Perfil** | Nome da Conta. | `Lilian Jácomo` |
| **Seguidores (Total)** | Total atual de seguidores. | `1250` |
| **Posts MyCreator** | Posts processados pela ferramenta. | `45` |
| **Engajamento Médio MyCreator (%)** | `(Interações / Alcance) * 100`. | `5.2` |
| **Alcance Acumulado MyCreator** | Soma do alcance (Posts ferramenta). | `15000` |
| **Interações Totais MyCreator** | Soma de interações (Posts ferramenta). | `1200` |
| **Atualizado em** | Data da extração. | `13/02/2026 02:00:00` |

---

## 📑 5. Aba: `Reels_Detalhado` (Vídeos Curtos)
**Granularidade:** Uma linha por Reel publicado.
*Foco na performance de vídeos.*

| Coluna | Descrição | Exemplo |
| :--- | :--- | :--- |
| **Cidade** | Workspace. | `Florianópolis` |
| **Data** | Data da publicação. | `12/02/2026` |
| **Perfil** | Nome da conta. | `@myside.imoveis` |
| **Título** | Título ou início da legenda. | `Tour pelo ap...` |
| **Duração (s)** | Duração do vídeo em segundos. | `45.5` |
| **Tempo Assistido (s)** | Tempo total assistido por todos os usuários. | `15000` |
| **Tempo Médio (s)** | Média de tempo assistido por view. | `12.5` |
| **Plays** | Número de visualizações. | `2300` |
| **Alcance** | Contas alcançadas. | `1800` |
| **Engajamento (%)** | Taxa de engajamento do vídeo. | `5.5` |
| **Likes** | Total de curtidas. | `150` |
| **Comentários** | Total de comentários. | `20` |
| **Salvos** | Total de salvamentos. | `45` |
| **Compartilhamentos** | Total de envios. | `30` |
| **Link** | URL do vídeo. | `https://instagram...` |
| **Atualizado em** | Data da extração. | `13/02/2026 02:00:00` |

---

| **Link** | URL do vídeo. | `https://instagram...` |
| **Atualizado em** | Data da extração. | `13/02/2026 02:00:00` |

---

## 📑 6. Aba: `Imagens_Detalhado` (Feed Estático)
**Granularidade:** Uma linha por Post de Imagem única.

*Colunas idênticas à aba Dados_Brutos, mas filtrado apenas para Imagens.*

---

## 📑 7. Aba: `Carrossel_Detalhado` (Álbuns)
**Granularidade:** Uma linha por Post do tipo Carrossel.

*Colunas idênticas à aba Dados_Brutos, mas filtrado apenas para Carrosseis.*

---

## 📑 8. Aba: `Redes_Monitoramento` (Monitoramento Agregado)
**Granularidade:** Uma linha por Cidade e Plataforma.
**Antigo:** *Destaques_Performance*
*Dashboard executivo de performance geral.*

| Coluna | Descrição | Exemplo |
| :--- | :--- | :--- |
| **Cidade** | Workspace. | `Florianópolis` |
| **Rede Social** | Plataforma. | `Instagram` |
| **Contagem de Posts** | Total de publicações extraídas. | `45` |
| **Engajamento Médio (%)** | Média da taxa de engajamento do período. | `4.5` |
| **Alcance Total** | Soma do alcance de todos os posts. | `150400` |
| **Impressões Totais** | Soma das impressões de todos os posts. | `200000` |
| **Atualizado em** | Data da última atualização. | `13/02/2026 14:30:00` |

---

## 📑 9. Aba: `Base_Looker_Unificada` (Fonte Mestra)
**Granularidade:** Uma linha por Post (Feed ou Reels).
*Tabela otimizada para "Single Data Source" no Looker Studio.*

| Coluna | Descrição | Exemplo |
| :--- | :--- | :--- |
| **ID Post** | Identificador único. | `33772895...` |
| **Data** | Data de publicação. | `13/02/2026` |
| **Cidade** | Workspace de origem. | `Florianópolis` |
| **Perfil** | Nome do perfil. | `@myside.imoveis` |
| **Rede Social** | Plataforma. | `Instagram` |
| **Seguidores** | Total de seguidores do perfil. | `15200` |
| **Tipo de Mídia** | `Imagem`, `Carrossel` ou `Reels`. | `Reels` |
| **Link** | Permalink. | `https://...` |
| **Legenda/Título** | Texto do post. | `Confira este imóvel...` |
| **Alcance** | Alcance total. | `1500` |
| **Taxa de Alcance (%)** | `(Alcance / Seguidores) * 100`. | `10.5` |
| **Impressões** | Impressões totais. | `2000` |
| **Engajamento (%)** | Taxa de engajamento oficial. | `5.2` |
| **Likes** | Total de curtidas. | `120` |
| **Comentários** | Total de comentários. | `5` |
| **Salvos** | Total de salvamentos. | `10` |
| **Compartilhamentos** | Total de compartilhamentos. | `22` |
| **Atualizado em** | Data da extração. | `13/02/2026 15:00:00` |

---


---

## 📑 10. Aba: `Visao_Geral_Perfil` (Benchmarks)
**Granularidade:** Uma linha por Workspace (Agregado 365 dias).
*Comparativo de performance geral (todos os posts, inclusive fora da plataforma).*

| Coluna | Descrição | Exemplo |
| :--- | :--- | :--- |
| **Cidade** | Workspace. | `Florianópolis` |
| **Perfis Conectados** | Nomes das contas. | `myside.imoveis` |
| **Seguidores (Total)** | Total de seguidores. | `8100` |
| **Total Posts (365d)** | Posts publicados no ano. | `370` |
| **Alcance Total (365d)** | Alcance acumulado no ano. | `680000` |
| **Interações Totais (365d)** | Engajamento total no ano. | `3500` |
| **Período Analisado** | Intervalo de datas (últimos 365 dias). | `2025-02-18 - 2026-02-18` |

---

## 📅 11. Aba: `Historico_Diario_MyCreator` (Publishing Behavior)
**Granularidade:** Uma linha por Dia por Perfil.
*Dados agregados para gráficos de comportamento de publicação e desempenho ao longo do tempo.*

| Coluna | Descrição | Exemplo |
| :--- | :--- | :--- |
| **Data** | Data da publicação. | `2025-02-15` |
| **Cidade** | Workspace. | `Florianópolis` |
| **Perfil** | Nome do perfil. | `myside.imoveis` |
| **Rede** | Rede Social (Instagram/Facebook). | `Instagram` |
| **Posts Publicados** | Quantidade de posts no dia. | `3` |
| **Alcance (Soma)** | Soma do alcance de todos os posts do dia. | `15000` |
| **Impressões (Soma)** | Soma das impressões. | `18000` |
| **Engajamento (Soma)** | Soma de todas interações. | `500` |
| **Plays (Soma)** | Total de visualizações de vídeo/Reels. | `20000` |
| **Tempo Assistido Total (Seg)** | Soma do tempo assistido (Reels). | `150000` |

---

## 🏆 12. Aba: `Top_Posts_MyCreator` (Rankings)
**Granularidade:** Top 20 posts por categoria.
*Lista dos melhores posts baseada em métricas específicas.*

| Coluna | Descrição | Exemplo |
| :--- | :--- | :--- |
| **Rank_Tipo** | Categoria do Ranking (Alcance, Engajamento, Impressões). | `Alcance` |
| **Valor_Metrica** | Valor da métrica correspondente. | `50000` |
| **Perfil** | Perfil dono do post. | `myside.imoveis` |
| **Data** | Data de publicação. | `2025-02-10` |
| **Tipo** | Tipo de mídia (IMAGE, VIDEO, CAROUSEL, REELS). | `REELS` |
| **Legenda/Titulo** | Título ou início da legenda do post. | `Confira este imóvel...` |
| **Link** | Link para o post. | `https://instagram...` |

---

## 📸 13. Aba: `Snapshot_Seguidores` (Histórico BigQuery)
**Granularidade:** Snapshot Diário (Append).
*Histórico acumulado de seguidores para análise futura de "Seguidores na época do post".*

| Coluna | Descrição | Exemplo |
| :--- | :--- | :--- |
| **Data_Snapshot** | Data da coleta do dado. | `2026-02-18` |
| **Cidade** | Workspace. | `Goiânia` |
| **Perfil** | Nome do perfil. | `myside.goiania` |
| **Seguidores** | Contagem total de seguidores no dia. | `12500` |


