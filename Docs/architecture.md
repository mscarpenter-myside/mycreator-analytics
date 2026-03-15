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
        A1["Endpoint: /analytics/triggerJob"]:::api
        A2["Endpoint: /fetchPlans"]:::api
        A3["Endpoint: /postAnalytics"]:::api
        A4["Endpoint: /audienceGrowth"]:::api
    end

    subgraph Processing ["⚙️ Processamento (Python)"]
        B0("Sincronização / Bypass (sync_data)"):::etl
        B2("Extração de Posts"):::etl
        B5("Extração de Hashtags"):::etl
        B10("Agregação Monitoramento (Apenas Logs)"):::etl
        B13("Top Posts (Rank)"):::etl
    end

    subgraph Destination ["📊 Destinos (Sheets & Cloud)"]
        C2[("Aba: dados_brutos")]:::storage
        C3[("Aba: analise_hashtag")]:::storage
        C11[("Aba: top_posts_mycreator")]:::storage
        C12[("Aba: crescimento_seguidores")]:::storage
        C20[("Aba [CONSOLIDADA]: base_looker_studio_posts")]:::storage
        D1[("☁️ Supabase: posts_final")]:::storage
        D2[("☁️ Supabase: seguidores_history")]:::storage
    end

    A4 -->|Crescimento| C12
    A2 -->|JSON: Lista de Posts| B2
    A3 -->|JSON: Likes, Reach, Type| B2
    
    B2 -->|DataFrame Final| C2
    B2 -.->|Regex Extraction| B5:::etl
    B5 -->|DataFrame Agregado| C3:::storage
    
    B2 -->|Agregação Interna| B10:::etl
    
    B2 -->|Rank Top 20| B13:::etl
    B13 --> C11:::storage

    C20 -->|Sync Script| D1
    C12 -->|Sync Script| D2
```

---

## 🔄 2. Diagrama de Sequência (Execução Passo-a-Passo)

Este diagrama detalha a ordem exata das chamadas HTTP realizadas pelo script `run_etl.py` enxuto.

```mermaid
sequenceDiagram
    participant SYNC as 🤖 sync_data.py
    participant ETL as 🐍 run_etl.py
    participant API as ☁️ MyCreator API
    participant Sheet as 📊 Google Sheets

    Note over SYNC, API: 🟢 FASE 1: Sincronização Prévia (-45 min)
    SYNC->>API: POST /backend/api/analytics/triggerJob (Bypass c/ ID Interno)
    API-->>SYNC: Status 200 (Sync Iniciado)

    Note over ETL, API: 🟢 FASE 2: Extração de Posts & Crescimento
    ETL->>API: POST /backend/audienceGrowth
    ETL->>API: POST /backend/plan/preview (Lista Posts)
    loop Para cada Post
        ETL->>ETL: Regex Extract Hashtags (from Caption)
        ETL->>API: GET /backend/analytics/post/{id}
        API-->>ETL: JSON { metrics }
    end

    Note over ETL, Sheet: 🟢 FASE 3: Carga Sheets
    ETL->>Sheet: load_to_sheets(df_posts, tab="dados_brutos")
    ETL->>Sheet: load_to_sheets(df_hashtags, tab="analise_hashtag")
    ETL->>Sheet: load_to_sheets(df_top_posts, tab="top_posts_mycreator")
    ETL->>Sheet: load_to_sheets(df_audience_growth, tab="crescimento_seguidores")
    Sheet-->>ETL: Success (200 OK)

    Note over SYNC, Sheet: 🟢 FASE 4: Consolidação (GAS)
    ETL->>API: GET (GAS_URL)
    Note right of API: Google Apps Script roda consolidando dados...

    Note over ETL, API: 🟢 FASE 5: Cloud Sync (Supabase)
    ETL->>Sheet: Fetch base_looker_studio_posts
    ETL->>API: SQLAlchemy UPSERT (Supabase)
    ETL->>API: SQLAlchemy UPSERT (seguidores_history)
```

---

## 🧩 3. Modelo de Dados (Relacionamento entre Abas)

Estrutura das abas simplificadas para facilitar a análise no Looker Studio ou Power BI.

```mermaid
erDiagram
    POSTS ||--o{ HASHTAGS : "contem"
    
    POSTS {
        string Cidade
        string Perfil
        date Data_Publicacao
        string Tipo_Midia "Reels, Video, Imagem, Carousel"
        int Seguidores "Snapshot no Momento da Extração"
        int Alcance
        int Impressoes
        int Likes
    }

    HASHTAGS {
        string Hashtag PK
        int Qtd_Usos
        int Alcance_Acumulado
        int Engajamento_Total
    }

    TOP_POSTS {
        string Rank_Tipo
        int Valor_Metrica
        string Perfil
        string Link
    }

    CRESCIMENTO_SEGUIDORES {
        date Data PK
        string Perfil PK
        int Seguidores
    }
```

### Explicação do Modelo
*   **Aba dados_brutos (Fato Principal)**: Contém eventos históricos de feed, reels, e carrossel. Fornece a base de cálculo para o Looker Studio.
*   **Aba analise_hashtag (Agregada)**: Tabela contendo a performance consolidada por hashtag, construída minerando a legenda dos posts.
*   **Aba top_posts_mycreator**: Um ranqueamento atualizado com os melhores posts que geraram alcance, engajamento e visualizações em toda a rede.
*   **Aba crescimento_seguidores**: Monitoramento da flutuação da audiência global.

---

## 🛠️ 4. Ferramentas de Verificação e Integridade

Para garantir a confiabilidade do pipeline entre as diferentes plataformas, o projeto conta com:

- **`test_connection_v2.py`**: Valida a conectividade SSH/Cloud e força protocolos IPv4 para ambientes WSL/Docker.
- **`verify_sync.py`**: Realiza a paridade de dados, comparando contagens e a existência do primeiro/último registro entre Google Sheets e Supabase.

**Engenharia de Conteúdo & Automação**
