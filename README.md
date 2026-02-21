# MyCreator Analytics ETL 🚀

**Pipeline de Extração e Análise de Dados de Redes Sociais**

Este projeto automatiza a extração de dados da plataforma **MyCreator (antiga ContentStudio)** para monitorar a performance de postagens e o crescimento de contas no Instagram, Facebook, e outras redes sociais.

---

## 🔥 Funcionalidades (Pipeline Enxuto)

O sistema opera de maneira otimizada exportando dados fundamentais de performance nas redes sociais para o Google Sheets através de 4 abas principais:

### 1. `dados_brutos` (Posts)
Tabela granular contendo postagens unitárias com métricas de desempenho.
*   **Métricas**: Likes, Comentários, Salvos, Compartilhamentos, Alcance, Impressões.
*   **Segmentação**: Tipo de Mídia (Reels, Carrossel, Vídeo, Imagem).

### 2. `analise_hashtag` (Temas Virais)
Agregação em volume do engajamento e alcance através da mineração das palavras-chave postadas.

### 3. `top_posts_mycreator` (Destaques)
Ranqueamento unificado dos melhores conteúdos da marca baseando-se no alcance global, engajamento consolidado e total de impressões.

### 4. `crescimento_seguidores` (Audience Growth)
Monitoramento histórico contínuo da flutuação da audiência agregada por dia para análises de aquisição.

---

## 🛠️ Como Executar Localmente

1.  **Clone o repositório**
    ```bash
    git clone https://github.com/mscarpenter-myside/mycreator-analytics.git
    cd mycreator-analytics
    ```

2.  **Crie o ambiente virtual**
    ```bash
    python -m venv venv
    source venv/bin/activate  # Linux/Mac
    # ou
    .\venv\Scripts\activate   # Windows
    ```

3.  **Instale as dependências**
    ```bash
    pip install -r requirements.txt
    ```

4.  **Configure o ambiente (.env)**
    Crie um arquivo `.env` na raiz com as credenciais (veja `.env.example`).

5.  **Execute o ETL**
    ```bash
    python run_etl.py
    ```

---

## ⚙️ Configuração (GitHub Actions)

O workflow `daily_etl.yml` roda diariamente às 08:00 BRT.

### Variáveis de Ambiente Necessárias (Secrets)
*   `MYCREATOR_EMAIL` / `MYCREATOR_PASSWORD`: Credenciais de acesso.
*   `GOOGLE_SHEET_ID`: ID da planilha de destino.
*   `GCP_SA_KEY`: JSON da Service Account do Google Cloud (base64 ou raw).

---

## 📊 Estrutura de Dados

Consulte o arquivo [`RELATORIO_DADOS.md`](./RELATORIO_DADOS.md) para a documentação técnica completa de cada métrica e endpoint utilizado.

---

**Engenharia de Conteúdo & Automação**
