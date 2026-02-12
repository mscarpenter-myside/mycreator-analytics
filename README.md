# MyCreator Analytics ETL 🚀

**Pipeline de Extração e Análise de Dados de Redes Sociais**

Este projeto automatiza a extração de dados da plataforma **MyCreator (antiga ContentStudio)** para monitorar a performance de postagens e o crescimento de contas no Instagram, Facebook, e outras redes sociais.

---

## 🔥 Funcionalidades (Atualizado v2.0)

O sistema opera em uma arquitetura de **Dual-Tab**, gerando duas tabelas sincronizadas no Google Sheets:

### 1. Aba "Dados_Brutos" (Posts)
Tabela granular contendo cada postagem individual com suas métricas de desempenho.
*   **Métricas**: Likes, Comentários, Salvos, Compartilhamentos, Alcance, Impressões.
*   **Novidade**: Coluna **Seguidores** (snapshot no momento da extração) para cálculo de taxa de alcance.
*   **Segmentação**: Tipo de Mídia (Reels, Carrossel, Vídeo, Imagem).

### 2. Aba "Perfis" (Saúde da Conta)
Tabela consolidada com o snapshot diário de todas as contas monitoradas.
*   **Métricas**: Total de Seguidores, Total de Posts, Engajamento Médio (30 dias), Alcance Total (30 dias).
*   **Cobertura**: Monitora automaticamente todas as contas configuradas nos workspaces.

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
