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

## ☁️ Sincronização Cloud (Supabase)

O pipeline agora inclui uma etapa de **Sincronização em Nuvem** que espelha os dados consolidados do Google Sheets em um banco de dados PostgreSQL no Supabase. Isso permite que os dados sejam acessados em tempo real via **Claude MCP** e **Looker Studio**.

### Como verificar a integridade:
Implementamos um script dedicado para validar se o Google Sheets e o Supabase estão em sincronia:
```bash
python3 verify_sync.py
```
Este script valida não apenas a contagem de linhas, mas também a integridade do primeiro e último registro de cada tabela.

### Requisitos Técnicos para Estabilidade (WSL):
Para evitar falhas de conexão comuns em ambientes WSL, o projeto utiliza:
- **IPv4 Forçado**: Conexão otimizada via IPv4.
- **Transaction Pooler (Porta 6543)**: Para maior estabilidade.
- **URI Sanitization**: Tratamento automático de aspas e drivers no `.env`.

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
    **Nota**: A URI do Supabase é essencial para a sincronização cloud.

5.  **Execute o ETL**
    ```bash
    python run_etl.py
    ```

---

## ⚙️ Configuração (GitHub Actions)

A infraestrutura na nuvem foi particionada em dois cronogramas (Workflows) independentes:

1. **`sync_data.yml`**: Roda às 07:15 BRT e 16:15 BRT. Robô *trigger* rápido.
2. **`daily_etl.yml`**: Roda às 08:00 BRT e 17:00 BRT. Extrator principal que consolida dados e sincroniza com o Supabase.

### Variáveis de Ambiente Necessárias (Secrets)
*   `MYCREATOR_EMAIL` / `MYCREATOR_PASSWORD`: Credenciais de acesso.
*   `GOOGLE_SHEET_ID`: ID da planilha de destino.
*   `GCP_SA_KEY`: JSON da Service Account do Google Cloud.
*   `URI`: String de conexão do Supabase (PostgreSQL).

---

## 📊 Estrutura de Dados

- Consulte [`database-guide.md`](Docs/database-guide.md) para a documentação detalhada das tabelas SQL.
- Consulte [`architecture.md`](Docs/architecture.md) para detalhes da arquitetura e fluxos.
- Consulte [`data-dictionary.md`](Docs/data-dictionary.md) para o dicionário de campos.

---

**Engenharia de Conteúdo & Automação**




