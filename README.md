# 📊 MyCreator Analytics ETL

Pipeline ETL para extrair dados de performance de posts da plataforma **MyCreator/ContentStudio** e salvar em **Google Sheets**.

## 🏗️ Arquitetura

```
mycreator_analytics/
├── .github/workflows/
│   └── daily_etl.yml      # Cron do GitHub Actions (08:00 UTC)
├── src/
│   ├── __init__.py
│   ├── config.py          # Configurações e credenciais
│   ├── extract.py         # Extração via curl_cffi
│   ├── transform.py       # Limpeza e cálculos com Pandas
│   ├── load.py            # Envio para Google Sheets
│   └── main.py            # Orquestrador do ETL
├── credentials/           # ⚠️ NÃO COMITAR
│   └── service_account.json
├── .env                   # ⚠️ NÃO COMITAR
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

## 🚀 Setup Local

### 1. Clone e instale dependências

```bash
cd ~/mycreator_analytics
python -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure variáveis de ambiente

```bash
cp .env.example .env
# Edite o arquivo .env com suas credenciais
```

### 3. Obtenha as credenciais

#### Cookie e Token MyCreator:
1. Acesse `app.mycreator.io` e faça login
2. Abra DevTools (F12) > Network
3. Faça qualquer ação na página
4. Clique em uma requisição para `/api/`
5. Em **Headers**, copie:
   - `Cookie` → `MYCREATOR_COOKIE`
   - `Authorization` → `MYCREATOR_TOKEN`

#### Service Account Google Cloud:
1. Acesse [Google Cloud Console](https://console.cloud.google.com)
2. Crie um projeto ou selecione existente
3. Ative a **Google Sheets API**
4. Vá em **IAM & Admin > Service Accounts**
5. Crie uma Service Account
6. Crie uma chave JSON e salve em `credentials/service_account.json`
7. Compartilhe sua Google Sheet com o email da Service Account

### 4. Execute

```bash
python -m src.main
```

## ⚙️ GitHub Actions

### Configurar Secrets

No repositório GitHub, vá em **Settings > Secrets and Variables > Actions** e adicione:

| Secret | Descrição |
|--------|-----------|
| `MYCREATOR_COOKIE` | Cookie de sessão |
| `MYCREATOR_TOKEN` | Token de autorização |
| `GOOGLE_SHEET_ID` | ID da planilha (da URL) |
| `GCP_SA_KEY` | JSON completo da Service Account |

### Execução

- **Automática**: Todo dia às 08:00 UTC
- **Manual**: Actions > Daily ETL > Run workflow

## 📈 Métricas Coletadas

| Métrica | Descrição |
|---------|-----------|
| Likes | Curtidas |
| Comentários | Comentários |
| Salvos | Salvamentos |
| Alcance | Reach |
| Impressões | Impressions |
| Plays | Visualizações (vídeo) |
| Taxa Engajamento | (Likes+Saves+Comments)/Reach × 100 |

## 🔧 Configurações

| Variável | Padrão | Descrição |
|----------|--------|-----------|
| `POSTS_LIMIT` | 50 | Número de posts a extrair |
| `WRITE_MODE` | overwrite | `overwrite` ou `append` |
| `DEBUG_MODE` | false | Logs detalhados |

## 📝 Licença

MIT
