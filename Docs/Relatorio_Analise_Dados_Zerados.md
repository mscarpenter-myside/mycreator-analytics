# Relatório de Análise: Dados Ausentes e Zerados

## 1. Aba `Historico_Diario_MyCreator` (Identificação de Posts)

**Pergunta:** *"Não deveria ter o ID ou nome de post pra identificação?"*

**Análise Técnica:**
*   Esta aba foi projetada para ser uma **Agregação Diária** (Comportamento de Publicação), e não uma lista de posts.
*   **Lógica Atual:** O robô agrupa todos os posts de um mesmo dia e soma seus resultados.
    *   *Exemplo:* Se você postar 3 Reels no dia 18/02, esta aba mostrará **uma única linha** com `Data=18/02`, `Posts=3` e a soma do alcance de todos eles.
*   **Conclusão:** O comportamento está correto para o objetivo de "Histórico de Performance da Conta". Para ver posts individualizados com ID e Nome, deve-se usar a aba **`Dados_Brutos`**.

---

## 2. Dados Zerados (Reels, Carrossel, Dados Brutos)

Identificamos que métricas específicas estão vindo zeradas da API. Abaixo detalho as causas prováveis para cada caso baseado na análise do código de extração (`extract.py`).

### 2.1. Reels Detalhado e Dados Brutos (Vídeo)
*   **Campos Zerados:** `Duração`, `Tempo Assistido`, `Tempo Médio`, `Plays`.
*   **Causa Técnica:**
    *   O robô tenta ler estes campos do endpoint de analytics (`/backend/analytics/post/{id}`).
    *   Se estes valores estão vindo zerados, significa que **a API do MyCreator não está retornando estas chaves** no JSON de resposta para os posts da sua conta, ou eles estão em uma estrutura diferente (ex: dentro de um sub-objeto `video_metrics` que não estamos varrendo).
    *   *Nota:* Métricas de "Tempo Assistido" muitas vezes só estão disponíveis para *Insights* proprietários (donos da conta) e podem ter limitações na API privada que o MyCreator usa.

### 2.2. Carrossel Detalhado
*   **Campos Zerados:** `Compartilhamentos`, `Impressões`.
*   **Causa Técnica:**
    *   Para Carrosséis, a API do Instagram (via MyCreator) frequentemente retorna métricas simplificadas.
    *   Se `Likes` e `Comentários` aparecem, mas `Impressões` e `Compartilhamentos` não, é um forte indício de **limitação da API para este formato específico** ou nível de permissão da conta.

---

## 3. Recomendações

1.  **Validar no MyCreator Web:** Verificar se esses números (Tempo assistido, Shares de Carrossel) aparecem no painel web do MyCreator para os *mesmos posts*.
    *   *Se não aparecerem lá:* O dado não existe na fonte.
    *   *Se aparecerem lá:* Precisamos investigar o JSON bruto ("Raw Data") da API para encontrar onde eles estão escondidos.

2.  **Manter `Dados_Brutos` como Referência:** A aba de dados brutos é a fonte da verdade. Se o dado não está lá, ele não aparecerá nas abas detalhadas.
