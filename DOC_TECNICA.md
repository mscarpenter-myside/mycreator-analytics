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

    subgraph Sources [📡 Fontes (API)]
        A1[Endpoint: /getSummary]:::api
        A2[Endpoint: /fetchPlans]:::api
        A3[Endpoint: /postAnalytics]:::api
    end

    subgraph Processing [⚙️ Processamento (Python)]
        B1(1. Extração de Perfis):::etl
        B2(2. Extração de Posts):::etl
        B3{{⚡ ENRIQUECIMENTO}}:::join
        B4[Dict: AccountID -> Seguidores]:::etl
    end

    subgraph Destination [📊 Google Sheets]
        C1[(Aba: Perfis)]:::storage
        C2[(Aba: Dados_Brutos)]:::storage
    end

    %% Fluxo Perfis (Master Data)
    A1 -->|JSON: Followers, Engajamento| B1
    B1 -->|Cria Mapa em Memória| B4
    B1 -->|DataFrame Limpo| C1

    %% Fluxo Posts (Transactional Data)
    A2 -->|JSON: Lista de Posts| B2
    A3 -->|JSON: Likes, Reach, Type| B2
    
    %% O Pulo do Gato (Join)
    B4 -.->|Lookup O(1)| B3
    B2 --> B3
    B3 -->|DataFrame Final| C2

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

    Note over ETL, API: 🟢 FASE 2: Extração de Posts (Transaction Data)
    ETL->>API: POST /backend/plan/preview (Lista Posts)
    loop Para cada Post
        ETL->>ETL: Lookup Followers (usa Dict da Fase 1)
        ETL->>API: GET /backend/analytics/post/{id}
        API-->>ETL: JSON { likes, reach, media_type, ... }
    end

    Note over ETL, Sheet: 🟢 FASE 3: Carga (Load)
    ETL->>Sheet: load_to_sheets(df_perfis, tab="Perfis")
    Sheet-->>ETL: Success (200 OK)
    ETL->>Sheet: load_to_sheets(df_posts, tab="Dados_Brutos")
    Sheet-->>ETL: Success (200 OK)
```

---

## 🧩 3. Modelo de Dados (Relacionamento entre Abas)

Embora o Google Sheets não seja um banco de dados relacional, estruturamos as abas como tal para facilitar a análise no Looker Studio ou Power BI.

```mermaid
erDiagram
    PERFIS ||--o{ POSTS : "publica"
    
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
```

### Explicação do Modelo
*   **Aba Perfis (Dimensão)**: Contém atributos únicos da conta. Se o nome do perfil mudar, reflete aqui.
*   **Aba Posts (Fato)**: Contém eventos históricos.
*   **Redundância Intencional**: A coluna `Seguidores` existe em **ambas** as tabelas.
    *   Em **Perfis**: Representa o *estado atual* da conta.
    *   Em **Posts**: Representa o *estado no momento da extração*, permitindo calcular a eficiência do post isoladamente.

---

**Engenharia de Conteúdo & Automação**
