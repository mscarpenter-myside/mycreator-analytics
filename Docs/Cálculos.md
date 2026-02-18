# 🧮 Fórmulas e Cálculos Detalhados do ETL MyCreator

Este documento serve como a **"Bíblia de Métricas"** do projeto. Ele explica não só a matemática, mas o **porquê** de cada cálculo e como interpretá-lo no dia a dia.

---

## 1. Aba: `Perfis` (Métricas Agregadas)

Esta aba é um **Resumo Executivo** de cada influenciador/conta. Ela mistura dados que vêm prontos do Instagram (Snapshot) com dados calculados pela nossa ferramenta (Performance).

### A. Métricas de Snapshot (O que a conta É hoje)
*Dados lidos diretamente do Instagram no momento que o robô roda.*

#### **1. Seguidores (Total)**
*   **Definição:** O número exato de seguidores que a conta tem agora.
*   **Fonte:** API MyCreator (`getSummary`).
*   **Para que serve:** Mede o **tamanho da base** (potencial máximo de alcance orgânico direto).

### B. Métricas de Performance MyCreator (O que a conta FEZ)
*Calculadas somando apenas os posts que estão cadastrados na ferramenta.*

#### **2. Posts MyCreator**
*   **Definição:** Quantidade de publicações que foram processadas neste relatório.
*   **Importância:** Mostra a **produtividade** da equipe. Se o número for muito baixo, as outras métricas (como Alcance Acumulado) também serão baixas, não por performance ruim, mas por falta de volume.

#### **3. Alcance Acumulado MyCreator**
*   **Fórmula:** $\sum (\text{Alcance de cada Post})$
*   **Exemplo Prático:**
    *   Post 1: Alcançou 1.000 pessoas.
    *   Post 2: Alcançou 1.500 pessoas.
    *   **Alcance Acumulado = 2.500**.
*   **⚠️ Ponto de Atenção (Soma Simples vs. Únicos):**
    *   Este número **NÃO** significa que 2.500 pessoas diferentes viram o conteúdo.
    *   Se a *Maria* viu o Post 1 e também viu o Post 2, ela foi contada duas vezes.
    *   **Interpretação Correta:** Representa o "volume de impacto" ou "tonelagem" de distribuição de conteúdo gerado pela ferramenta.

#### **4. Interações Totais MyCreator**
*   **Fórmula:** $\text{Likes} + \text{Comentários} + \text{Salvos} + \text{Compartilhamentos}$
*   **Definição:** A soma de qualquer clique relevante que o usuário deu no conteúdo.
*   **Para que serve:** Mede o volume bruto de reação da audiência. O "barulho" que a marca fez.

#### **5. Engajamento Médio MyCreator (%)**
*   **Fórmula Atual (Por Alcance):** 
    $$ \left( \frac{\text{Interações Totais}}{\text{Alcance Acumulado}} \right) \times 100 $$
*   **Exemplo:**
    *   Alcance Acumulado: 10.000
    *   Interações Totais: 500
    *   **Resultado:** $5,00\%$.
*   **Interpretação:** De cada 100 vezes que o conteúdo apareceu na tela de alguém, em 5 vezes a pessoa interagiu.
*   **Dúvida Comum:** *"Por que não dividir por seguidores?"*
    *   Dividir por seguidores mostra o engajamento da **Base** (bom para ver se os fãs estão ativos).
    *   Dividir por alcance mostra a **Qualidade do Conteúdo** (bom para ver se o post é interessante, independente de quantas pessoas viram).
    *   *Nossa escolha atual:* Focamos na qualidade do conteúdo (Por Alcance).

---

## 2. Aba: `Redes_Monitoramento` (Visão por Cidade)

Aqui agrupamos tudo por Cidade para comparar performances regionais (ex: Florianópolis vs Curitiba).

#### **1. Engajamento Médio (%) das Cidades**
*   **Fórmula:** Média simples das taxas de cada post.
*   **Comportamento Matemático:**
    *   Post Viral (100k alcance, 2% engajamento)
    *   Post Nichado (100 alcance, 20% engajamento)
    *   **Média na Tabela:** $(2\% + 20\%) / 2 = 11\%$.
*   **Por que assim?** Para evitar que um único post viral "esmague" a média e esconda que os outros posts tiveram bom desempenho qualitativo com a base fiel. Valoriza a consistência.

---

## 3. Glossário de Métricas Nativas (Instagram/Facebook)

Termos que vêm direto da API para as abas detalhadas (Reels, Imagens, etc).

| Métrica | O que significa? |
| :--- | :--- |
| **Impressões** | Quantas vezes o post apareceu na tela. Se eu ver o mesmo post 5 vezes, conta 5 impressões. |
| **Alcance** | Quantas **contas únicas** viram. Se eu ver 5 vezes, conta 1 alcance. |
| **Plays** | Quantas vezes o vídeo começou a rodar (mesmo que por 1 segundo). |
| **Tempo Médio (Reels)** | Quanto tempo, em média, as pessoas ficaram assistindo. Se o vídeo tem 30s e a média é 3s, o conteúdo não está prendendo atenção (Retenção baixa). |
| **Salvos** | O "Super Like". Indica intenção de compra ou utilidade alta. É o KPI mais valioso para topo de funil. |
