# 📘 Documentação Técnica Visual: MyCreator Analytics ETL

Este documento detalha a arquitetura lógica e o fluxo de dados do pipeline de ETL, utilizando diagramas **Mermaid** para fácil visualização e manutenção.

---

## 🏗️ 1. Arquitetura do Pipeline (Data Flow)

O diagrama abaixo ilustra como os dados fluem da API MyCreator até o Google Sheets, destacando o processo de **Enriquecimento em Memória** (Memory Join) que permite adicionar métricas de seguidores aos posts.

```mermaid
graph TD
    %% Estilos (Cores Profissionais para Data Team)
    classDef api fill:#e3f2fd,stroke:#1565c0,stroke-width:2px,color:#0d47a1;
    classDef etl fill:#fff3e0,stroke:#e65100,stroke-width:2px,color:#e65100;
    classDef storage fill:#e8f5e9,stroke:#2e7d32,stroke-width:2px,color:#1b5e20;
    classDef join fill:#f3e5f5,stroke:#7b1fa2,stroke-width:2px,stroke-dasharray: 5 5,color:#4a148c;

    subgraph Sources ["📡 Fontes (API)"]
        A1["Endpoint: /getSummary"]:::api
        A2["Endpoint: /fetchPlans"]:::api
        A3["Endpoint: /postAnalytics"]:::api
    end

    subgraph Processing ["⚙️ Processamento (Python)"]
        B1("1. Extração de Perfis"):::etl
        B2("2. Extração de Posts"):::etl
        B3{{"⚡ ENRIQUECIMENTO"}}:::join
        B4["Dict: AccountID -> Seguidores"]:::etl
    end

    subgraph Destination ["📊 Google Sheets"]
        C1[("Aba: Perfis")]:::storage
        C2[("Aba: Dados_Brutos")]:::storage
    end

    %% Fluxo Perfis (Master Data)
    A1 -->|JSON: Followers, Engajamento| B1
    B1 -->|Cria Mapa em Memória| B4
    B1 -->|DataFrame Limpo| C1

    %% Fluxo Posts (Transactional Data)
    A2 -->|JSON: Lista de Posts| B2
    A3 -->|JSON: Likes, Reach, Type| B2
    
    B2 --> B3
    B3 -->|DataFrame Final| C2
    B3 -.->|Regex Extraction| B5("3. Extração de Hashtags"):::etl
    B5 -->|DataFrame Agregado| C3[("Aba: Hashtags_Analitico")]:::storage
    
    A2 -->|JSON: Stories (Type=Story)| B6("4. Extração de Stories"):::etl
    B6 -->|DataFrame Stories| C4[("Aba: Stories_Detalhado")]:::storage

    %% Novos Fluxos (Fase 3)
    B2 -->|Filtro: Video/Reel| B7("5. Filtro Reels"):::etl
    B7 --> C5[("Aba: Reels_Detalhado")]:::storage

    B2 -->|Filtro: Imagem (Feed)| B8("6. Filtro Imagens"):::etl
    B8 --> C6[("Aba: Imagens_Detalhado")]:::storage

    B2 -->|Filtro: Carrossel| B9("7. Filtro Carrossel"):::etl
    B9 --> C7[("Aba: Carrossel_Detalhado")]:::storage

    B2 -->|Agregação| B10("8. Monitoramento"):::etl
    B10 --> C8[("Aba: Redes_Monitoramento")]:::storage

    B2 -->|Padronização| B11("9. Base Unificada"):::etl
    B11 --> C9[("Aba: Base_Looker_Unificada")]:::storage

    linkStyle 4 stroke:#7b1fa2,stroke-width:3px;
```

---

## 🔄 2. Diagrama de Sequência (Execução Passo-a-Passo)

Este diagrama detalha a ordem exata das chamadas HTTP realizadas pelo script `run_etl.py`. Útil para depuração e entendimento de latência.

```mermaid
sequenceDiagram
    participant ETL as 🐍 run_etl.py
    participant API as ☁️ MyCreator API
    participant Sheet as 📊 Google Sheets

    Note over ETL, API: 🟢 FASE 1: Extração de Perfis (Master Data)
    ETL->>API: POST /backend/fetchSocialAccounts (Lista Contas)
    loop Para cada Conta
        ETL->>API: POST /backend/analytics/overview/getSummary
        API-->>ETL: JSON { followers, engagement_rate, ... }
        ETL->>ETL: Armazena em Memória (Dict)
    end

    Note over ETL, API: 🟢 FASE 2: Extração de Posts & Hashtags (Transaction Data)
    ETL->>API: POST /backend/plan/preview (Lista Posts)
    loop Para cada Post
        ETL->>ETL: Lookup Followers (usa Dict da Fase 1)
        ETL->>ETL: Regex Extract Hashtags (from Caption)
        ETL->>API: GET /backend/analytics/post/{id}
        API-->>ETL: JSON { likes, reach, media_type, ... }
    end

    Note over ETL, API: 🟢 FASE 3: Extração de Stories (New!)
    ETL->>API: POST /backend/fetchPlans (type=['story'])
    loop Para cada Story
        ETL->>API: POST /backend/plan/preview
        API-->>ETL: JSON { metadata, metrics (if available) }
    end

    Note over ETL, Sheet: 🟢 FASE 4: Carga (Load)
    ETL->>Sheet: load_to_sheets(df_perfis, tab="Perfis")
    ETL->>Sheet: load_to_sheets(df_posts, tab="Dados_Brutos")
    ETL->>Sheet: load_to_sheets(df_hashtags, tab="Hashtags_Analitico")
    ETL->>Sheet: load_to_sheets(df_stories, tab="Stories_Detalhado")
    Sheet-->>ETL: Success (200 OK)
```

---

## 🧩 3. Modelo de Dados (Relacionamento entre Abas)

Embora o Google Sheets não seja um banco de dados relacional, estruturamos as abas como tal para facilitar a análise no Looker Studio ou Power BI.

```mermaid
erDiagram
    PERFIS ||--o{ POSTS : "publica"
    PERFIS ||--o{ STORIES : "publica"
    POSTS ||--o{ HASHTAGS : "contem"
    
    PERFIS {
        string Cidade
        string Perfil PK "Chave Primária Lógica"
        int Seguidores "Snapshot Atual"
        float Engajamento_Medio
        int Total_Posts
        date Atualizado_em
    }

    POSTS {
        string Cidade
        string Perfil FK "Chave Estrangeira p/ Perfis"
        date Data_Publicacao
        string Tipo_Midia "Reels, Video, Imagem"
        int Seguidores "Snapshot no Momento da Extração"
        int Alcance
        int Impressoes
        int Likes
    }

    STORIES {
        string ID_Story PK
        string Perfil FK
        date Data_Publicacao
        string Link
        string Preview_URL
        int Alcance "N/A (API limitation)"
        int Impressoes "N/A (API limitation)"
    }

    HASHTAGS {
        string Hashtag PK
        int Qtd_Usos
        int Alcance_Acumulado
        int Engajamento_Total
    }

    REELS {
        string ID Link
        string Titulo
        int Duração
        int Tempo_Assistido
        int Plays
        int Alcance
        int Likes
    }

    IMAGENS {
        string ID Link
        string Legenda
        int Likes
        int Comentarios
        int Alcance
    }

    CARROSSEL {
        string ID Link
        string Legenda
        int Likes
        int Comentarios
        int Alcance
    }

    MONITORAMENTO {
        string Cidade_Plataforma PK
        int Contagem_Posts
        float Engajamento_Medio
        int Alcance_Total
    }

    BASE_UNIFICADA {
        string ID_Post PK
        string Tipo_Midia "Reels, Video, Imagem, Carrousel"
        int Seguidores
        int Alcance
        int Impressoes
        float Engajamento_Pct
    }
```

### Explicação do Modelo
*   **Aba Perfis (Dimensão)**: Contém atributos únicos da conta. Se o nome do perfil mudar, reflete aqui.
*   **Aba Posts (Fato)**: Contém eventos históricos.
*   **Aba Stories (Fato)**: Novo! Contém eventos efêmeros (Stories) rastreados.
    *   *Nota*: Métricas de engajamento (taps, saídas) dependem da API liberar acesso histórico.
*   **Aba Hashtags (Agregada)**: Tabela contendo a performance consolidada por hashtag.
*   **Abas Detalhadas (Reels, Imagens, Carrossel)**: Segmentações específicas por formato de mídia para análises focadas.
*   **Aba Redes_Monitoramento**: Visão executiva agregada por cidade e plataforma.
*   **Aba Base_Looker_Unificada**: Tabela mestra padronizada (normalizada) pronta para consumo direto pelo Looker Studio, contendo todos os tipos de mídia com colunas compatíveis.

### Detalhamento das Colunas (Atualizado)

#### Aba: Perfis
| Coluna | Descrição |
| :--- | :--- |
| **Cidade** | Nome do workspace (Ex: Florianópolis) |
| **Perfil** | Nome da conta (Ex: myside.florianopolis) |
| **Seguidores (Total)** | Total de seguidores da conta |
| **Posts MyCreator** | Quantidade de posts processados/extraídos |
| **Engajamento Médio MyCreator (%)** | (Interações / Alcance) * 100 |
| **Alcance Acumulado MyCreator** | Soma do alcance dos posts extraídos |
| **Interações Totais MyCreator** | Soma de Likes + Comentários + Salvos + Shares |
| **Atualizado em** | Data da extração |

#### Aba: Base_Looker_Unificada (Fonte Mestra)
Esta é a principal tabela para dashboards. Normaliza diferentes tipos de métricas.

| Coluna | Descrição |
| :--- | :--- |
| **ID Post** | Identificador único |
| **Data** | Data de publicação (DD/MM/YYYY) |
| **Cidade** | Workspace |
| **Perfil** | Conta emissora |
| **Rede Social** | Instagram, Facebook, etc |
| **Seguidores** | No momento da publicação |
| **Tipo de Mídia** | Padronizado: `Reels`, `Imagem`, `Carrousel` |
| **Link** | URL do post |
| **Legenda/Título** | Texto descritivo |
| **Alcance** | Pessoas alcançadas |
| **Impressões** | Total de visualizações |
| **Engajamento (%)** | Taxa de engajamento |
| **Likes/Comentários/Salvos/Shares** | Métricas de interação |

#### Abas Específicas (Imagens, Carrossel, Reels)
Contêm métricas exclusivas de cada formato (ex: `Duração` e `Plays` para Reels). Estão separadas para facilitar auditoria.

#### Aba: Redes_Monitoramento
Resumo executivo atualizado a cada execução.
- **Contagem de Posts**: Volume publicado.
- **Engajamento Médio (%)**: Performance média da marca na cidade.
- **Alcance/Impressões Totais**: Visibilidade total da marca na cidade.

---

**Engenharia de Conteúdo & Automação**
