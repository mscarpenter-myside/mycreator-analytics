# MyCreator Analytics ETL

Pipeline automatizado para extração de métricas de performance de publicações do MyCreator, com carga direta no Google Sheets.

## 📁 Estrutura do Projeto

```
mycreator_analytics/
├── .github/workflows/
│   └── daily_etl.yml         # Automação GitHub Actions (08:00 BRT)
├── credentials/
│   └── service_account.json  # Credenciais GCP (não commitado)
├── src/
│   ├── __init__.py
│   ├── auth.py               # Autenticação automática (email/password)
│   ├── config.py             # Configurações e variáveis de ambiente
│   ├── extract.py            # Extração de dados da API MyCreator
│   └── load.py               # Carga de dados no Google Sheets
├── .env                      # Variáveis de ambiente (não commitado)
├── .env.example              # Template de configuração
├── requirements.txt          # Dependências Python
├── run_etl.py                # Script principal
└── README.md
```

## 🚀 Fluxo ETL

1. **Extract**: Busca dados de publicações da API MyCreator (4 workspaces fixos)
2. **Transform**: Converte dados para DataFrame com colunas padronizadas
3. **Load**: Atualiza planilha Google Sheets automaticamente

## 🔐 Autenticação

O sistema suporta dois modos de autenticação:

### Opção 1: Cookie + Token (Manual)
- Requer extração manual das credenciais do DevTools do navegador
- Expira periodicamente e precisa ser atualizado manualmente

### Opção 2: Email + Password (Automático) ✨ **Recomendado**
- Login automático via API usando email/password
- Re-autenticação automática em caso de sessão expirada (erro 401)
- Usa `curl_cffi` para personificação de navegador e evitar bloqueios WAF

```bash
# .env
MYCREATOR_EMAIL="seu_email@empresa.com"
MYCREATOR_PASSWORD="sua_senha_aqui"
```

## 🏙️ Workspaces Configurados

| Cidade | Workspace ID |
|--------|--------------|
| Florianópolis | `696e75c20f3354d37f074866` |
| Florianópolis Continente | `696689afcddd41ec6a024adb` |
| Goiânia | `696689f3c04f3fefdc0118cd` |
| MyCreator | `68fbfe91e94c0946d103643d` |

## 📊 Colunas do Relatório

O relatório gerado contém as seguintes colunas (na ordem):

| Categoria | Colunas |
|-----------|---------|
| **Identificação** | Cidade, Data de Publicação, Rede Social, Perfil, Tipo |
| **Conteúdo** | Título, Legenda |
| **Engajamento** | Likes, Comentários, Salvos, Compartilhamentos |
| **Performance** | Alcance, Impressões, Plays |
| **Técnico** | Link, ID Instagram, ID Interno, Status Dados, Timestamp de Atualização |

## ⚙️ Configuração

### 1. Variáveis de Ambiente

Copie `.env.example` para `.env` e configure:

```bash
# Autenticação MyCreator (escolha uma opção)

# Opção 1: Cookie + Token
MYCREATOR_COOKIE=your_cookie_here
MYCREATOR_TOKEN=your_token_here

# Opção 2: Email + Password (recomendado)
MYCREATOR_EMAIL=seu_email@empresa.com
MYCREATOR_PASSWORD=sua_senha_aqui

# Google Sheets
GOOGLE_SHEET_ID=your_sheet_id_here
SHEET_TAB_NAME=Dados_Brutos
WRITE_MODE=overwrite

# Configurações
POSTS_LIMIT=50
DEBUG_MODE=false
```

### 2. Credenciais Google Cloud

1. Acesse o [Google Cloud Console](https://console.cloud.google.com/)
2. Crie um projeto ou selecione um existente
3. Ative a API do Google Sheets
4. Crie uma Service Account
5. Gere uma chave JSON e salve em `credentials/service_account.json`
6. Compartilhe a planilha com o email da Service Account

### 3. Secrets do GitHub Actions

Configure os seguintes secrets no repositório:

| Secret | Descrição |
|--------|-----------|
| `MYCREATOR_EMAIL` | Email de login MyCreator |
| `MYCREATOR_PASSWORD` | Senha de login MyCreator |
| `GOOGLE_SHEET_ID` | ID da planilha do Google Sheets |
| `GCP_SA_KEY` | Conteúdo JSON da Service Account |

> **Nota**: Se preferir usar Cookie + Token em vez de Email + Password, configure `MYCREATOR_COOKIE` e `MYCREATOR_TOKEN` nos secrets.

## 🔧 Execução

### Local

```bash
# Ativar ambiente virtual
source venv/bin/activate

# Executar ETL
python run_etl.py
```

### Automática (GitHub Actions)

O ETL é executado automaticamente:
- **Horário**: Todo dia às 08:00 BRT (11:00 UTC)
- **Trigger manual**: Disponível via "Run workflow" no GitHub

## 📦 Dependências

```
requests>=2.31.0
pandas>=2.0.0
python-dotenv>=1.0.0
gspread>=5.0.0
google-auth>=2.0.0
google-auth-oauthlib>=1.0.0
curl_cffi>=0.5.0
```

## 📝 Licença

Projeto interno - MySide/MyCreator
