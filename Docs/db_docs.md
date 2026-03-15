# Documentação do Banco de Dados Supabase (PostgreSQL - MyCreator Analytics)

Este documento detalha o funcionamento, estrutura e integração do banco de dados em nuvem no **Supabase**, projetado para permitir que os responsáveis do marketing tenham acesso compartilhado aos dados via Claude MCP e Looker Studio.

---

## 1. Origem dos Dados
Os dados são extraídos da API MyCreator, consolidados no Google Sheets e sincronizados automaticamente com o **PostgreSQL no Supabase** ao final de cada execução do pipeline.

### Fluxo de Captura (Dual-Write / Sync)
1. **ETL MyCreator**: Extrai e transforma dados.
2. **Google Sheets**: Recebe os dados brutos e via GAS consolida na aba `base_looker_studio_posts`.
3. **Sincronização Cloud**: O script `run_etl.py` baixa a versão final consolidada e a espelha nas tabelas do Supabase.

---

## 2. Estrutura da Tabela (`posts_final`)

Esta é a tabela principal de performance de posts.

| Coluna | Tipo PostgreSQL | Descrição |
| :--- | :--- | :--- |
| `id_interno` | TEXT (PK) | ID único gerado pelo MyCreator |
| `data_publicacao` | TEXT | Data formatada (DD/MM/YYYY) |
| `cidade` | TEXT | Nome da workspace (Ex: Florianópolis) |
| `perfil` | TEXT | @usuario do perfil |
| `rede_social` | TEXT | Instagram, TikTok, etc. |
| `curtidas` | INTEGER | Total de likes |
| `comentarios` | INTEGER | Total de comentários |
| `salvos` | INTEGER | Total de salvamentos |
| `compartilhamentos` | INTEGER | Total de shares |
| `taxa_engajamento` | NUMERIC | Engagement Rate (Ex: 0.052 para 5.2%) |
| `alcance` | INTEGER | Reach total |
| `taxa_alcance` | NUMERIC | Reach Rate (Alcance / Seguidores) |
| `titulo_referencia` | TEXT | Título consolidado pelo time |
| `formato` | TEXT | Reels, Carrossel, Foto, etc. |

---

## 3. Tabela de Seguidores (`seguidores_history`)

Histórico diário de crescimento dos perfis.

| Coluna | Tipo PostgreSQL | Descrição |
| :--- | :--- | :--- |
| `data` | TEXT | Data da coleta |
| `cidade` | TEXT | Workspace |
| `perfil` | TEXT | @usuario |
| `seguidores` | INTEGER | Total de seguidores |
| `variacao_diaria`| INTEGER | Diferença em relação ao dia anterior |

---

## 4. Acesso Compartilhado (Claude MCP)

O **Supabase** permite que qualquer membro da equipe acesse os dados configurando a URI de conexão em sua ferramenta de preferência (como o Claude).

**Configuração no Claude Desktop (Exemplo):**
No arquivo de configuração do MCP, utilize a URI fornecida no `.env` do projeto.

### Exemplos de Perguntas para IA:
- *"Claude, qual perfil teve o melhor crescimento de seguidores na última semana?"*
- *"Gere um resumo de performance para a cidade de Florianópolis comparando Reels vs Carrossel."*
- *"Quais posts tiveram taxa de engajamento acima da média?"*

Como os dados estão em **PostgreSQL**, o Claude tem total precisão para rodar cálculos sumários e estatísticos complexos.
