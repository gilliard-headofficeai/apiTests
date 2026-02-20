# Guia de configuração — API de relatório para dashboards

Este documento descreve como configurar a aplicação de front/dashboard para consumir o wrapper de relatório (`report_lia`), quais campos da resposta usar e como trocar a URL de desenvolvimento (ngrok) pela URL de produção depois.

**Condições atuais:**
- A resposta padrão do wrapper é um JSON tratado por página. **De momento apenas a página "Visão Geral" está coberta** por esse formato; outras páginas terão chaves adicionais no futuro.
- A **URL base da API** (ngrok em desenvolvimento) deve ser tratada como **placeholder**: use uma variável de ambiente ou constante (ex.: `REPORT_API_BASE_URL`) para poder trocar por uma URL de produção sem alterar código.

**Requisito de código:** Remover de **todo o projeto** menções e tags ao nome "Lovable" (ou qualquer ferramenta específica). O repositório deve ser agnóstico de ferramenta: referir-se a "front", "aplicação", "dashboard" ou "cliente" em comentários e documentação.

---

## 1. Configuração da API

### 1.1 Base URL da API

| Uso | URL |
|-----|-----|
| **Desenvolvimento (ngrok atual)** | `https://vulnerably-bilabiate-andreas.ngrok-free.dev` |
| **Produção** | Substituir pela URL definitiva da API ao fazer deploy (use variável de ambiente, ex.: `REPORT_API_BASE_URL`) |

Em produção, use um placeholder (variável de ambiente) para a base; em desenvolvimento use a URL do ngrok acima. Quando o túnel mudar, atualize só a variável.

### 1.2 Endpoint do relatório

| Campo | Valor |
|-------|--------|
| **Path do relatório** | `/wrapper/report_lia` |

**URL completa de exemplo (desenvolvimento):**

```
GET https://vulnerably-bilabiate-andreas.ngrok-free.dev/wrapper/report_lia?from=2026-02-18&to=2026-02-19
```

O **período (`from` e `to`)** é controlado pelo **date picker da página**: o front envia na query as datas que o usuário escolheu no seletor de período (formato YYYY-MM-DD). Não é necessário enviar mais nada além desses dois parâmetros.

### 1.3 Resposta padrão

A resposta **padrão** do wrapper (sem `view=full`) é o JSON tratado para dashboards. O front chama uma vez e usa `response.visao_geral` para preencher a página **Visão Geral**. Não é necessário enviar `view=dashboard`; use `view=full` só se precisar do relatório otimizado completo.

O mesmo JSON é salvo em `cache/report_lia/dashboard_liareport.json` a cada chamada, para conferência local.

### 1.4 Parâmetros de query

| Parâmetro | Obrigatório | Formato | Exemplo | Descrição |
|-----------|-------------|---------|---------|-----------|
| `from` | Sim | YYYY-MM-DD | `2026-02-18` | Data inicial do período — **vem do date picker da página** |
| `to`   | Sim | YYYY-MM-DD | `2026-02-19` | Data final do período — **vem do date picker da página** |
| `view` | Não | string | `full` | Omitido = resposta tratada (dashboard). `view=full` = JSON otimizado completo. |
| `compare` | Não | string | `previous_month` | Quando enviar: ver regras em §1.5 (primeira carga e troca de mês). |

O front envia `from` e `to` em toda requisição (valores do date picker). O wrapper adiciona internamente `agentId`, `by`, `messageHistory`.

### 1.5 Comparativo com mês anterior — quando chamar

Para exibir **"vs mês ant.: +X%"** nos cards, o backend devolve `comparativo_mes_anterior` quando a requisição inclui `compare=previous_month`. Isso gera uma **segunda chamada** à API (mês anterior). Regra de uso:

1. **No primeiro momento (carregamento inicial da página)**  
   Chamar **com** `compare=previous_month`. Ex.: `?from=2026-02-01&to=2026-02-19&compare=previous_month`.  
   O usuário já vê os dados do período e o comparativo com o mês anterior (ex.: fev vs jan).

2. **Ao apenas atualizar o período dentro do mesmo mês**  
   Chamar **somente** `from` e `to` (sem `compare`). Ex.: usuário muda de 1–15 fev para 1–20 fev → `?from=2026-02-01&to=2026-02-20`.  
   Atualizam só os dados do período; o comparativo já exibido pode ser mantido no front (ou escondido, conforme o design).

3. **Ao trocar de mês no date picker**  
   Chamar de novo **com** `compare=previous_month`. Ex.: usuário escolhe março → `?from=2026-03-01&to=2026-03-19&compare=previous_month` (março vs fev). Se voltar para fevereiro → `?from=2026-02-01&to=2026-02-28&compare=previous_month` (fev vs jan).  
   Assim o comparativo é sempre do mês selecionado em relação ao mês anterior.

**Resumo:** usar `compare=previous_month` no **carregamento inicial** e sempre que o **mês selecionado mudar**. Não usar quando só mudar os dias dentro do mesmo mês.

| Parâmetro | Valor | Descrição |
|-----------|--------|-----------|
| `compare` | `previous_month` | Incluir na primeira chamada e ao trocar de mês. O backend faz segunda chamada para o mês anterior e devolve `comparativo_mes_anterior`. |

**Exemplos:**

- Primeira carga (fev): `GET .../wrapper/report_lia?from=2026-02-01&to=2026-02-19&compare=previous_month`
- Só atualizar período (mesmo mês): `GET .../wrapper/report_lia?from=2026-02-01&to=2026-02-28`
- Troca para março: `GET .../wrapper/report_lia?from=2026-03-01&to=2026-03-31&compare=previous_month`
- Volta para fev: `GET .../wrapper/report_lia?from=2026-02-01&to=2026-02-28&compare=previous_month`

**Comportamento do backend:**

- Sem `compare`: uma chamada; resposta só com `visao_geral`.
- Com `compare=previous_month`: usa `from` para calcular o mês anterior (ex.: 2026-02-01 → jan: 2026-01-01 a 2026-01-31), faz a segunda chamada e preenche `comparativo_mes_anterior`.

**Formato de `comparativo_mes_anterior`:**

Objeto com uma entrada por métrica de card que tem comparativo. Cada entrada tem `atual`, `anterior` e `variacao_percent` (número, ex.: `15.28` para +15,28%). O front só precisa exibir o texto "vs mês ant.: +15,3%" (ou "-10,2%") usando `variacao_percent`.

Métricas incluídas: `total_conversas`, `mensagens_lia`, `menores_de_18`, `fora_do_horario_count`, `percentual_menores_18`, `fora_do_horario_percent`.

Exemplo de trecho da resposta:

```json
{
  "visao_geral": { ... },
  "comparativo_mes_anterior": {
    "total_conversas": { "atual": 513, "anterior": 445, "variacao_percent": 15.28 },
    "mensagens_lia": { "atual": 2470, "anterior": 2100, "variacao_percent": 17.62 },
    "menores_de_18": { "atual": 36, "anterior": 30, "variacao_percent": 20.0 },
    "fora_do_horario_count": { "atual": 233, "anterior": 200, "variacao_percent": 16.5 },
    "percentual_menores_18": { "atual": 7.02, "anterior": 6.5, "variacao_percent": 8.0 },
    "fora_do_horario_percent": { "atual": 45.42, "anterior": 42.0, "variacao_percent": 8.14 }
  }
}
```

Se `compare=previous_month` não for enviado, a resposta **não** terá a chave `comparativo_mes_anterior`. Se houver erro ao calcular ou buscar o mês anterior, a chave virá como `null`. O front pode manter o card sem trend ou mostrar "—" quando não houver comparativo.

### 1.6 Headers

- Não é necessário enviar `X-API-Key` (o wrapper envia para a API real).
- O cliente pode enviar `Accept: application/json` se quiser.

### 1.7 Resumo de configuração

- **URL base (dev):** `https://vulnerably-bilabiate-andreas.ngrok-free.dev` — em produção, use variável de ambiente.
- **Rota do relatório:** `/wrapper/report_lia`
- **Método:** GET
- **Período:** `from` e `to` em toda requisição (date picker).
- **Comparativo:** enviar `compare=previous_month` (1) no **carregamento inicial** e (2) sempre que o usuário **trocar de mês**. Ao mudar só os dias dentro do mesmo mês, chamar só `from` e `to` (atualizar só os dados do período).

---

## 2. Resposta tratada — Visão Geral (exemplo real)

A resposta padrão é um objeto com uma chave por página. **Atualmente está implementada apenas a chave `visao_geral`**, que alimenta a página **Visão Geral**. Os campos abaixo devem ser atualizados no front com os valores recebidos.

### 2.0 Conferir e chamar no front

- **URL correta (ngrok atual):**  
  `GET https://vulnerably-bilabiate-andreas.ngrok-free.dev/wrapper/report_lia?from=2026-02-18&to=2026-02-19`  
  A parte **`from=...&to=...`** é montada pelo **date picker da página**: o usuário escolhe o período e o front adiciona essas query params na chamada.
- **Método:** GET, sem `X-API-Key`.
- **Resposta:** objeto com `visao_geral`; use `response.visao_geral` para preencher cards e gráficos.
- **Conferência:** para o mesmo período, a resposta deve bater com o JSON abaixo (ou com `cache/report_lia/dashboard_liareport.json` após uma chamada local).

Exemplo real (período 2026-02-18 a 2026-02-19 — mesmo retorno da URL acima; também salvo em `dashboard_liareport.json`):

```json
{
    "visao_geral": {
        "total_conversas": 513,
        "mensagens_lia": 2470,
        "distribuicao_por_estado": {
            "Goiás": 2,
            "Minas Gerais": 132,
            "Paraíba": 1,
            "Rio de Janeiro": 102,
            "Santa Catarina": 4,
            "Sergipe": 1,
            "São Paulo": 262
        },
        "faixa_etaria": {
            "0-17": 36,
            "18-24": 82,
            "25-34": 199,
            "35-44": 128,
            "45-54": 35,
            "55+": 9
        },
        "menores_de_18": 36,
        "percentual_menores_18": 7.02,
        "fora_do_horario_count": 233,
        "fora_do_horario_percent": 45.42,
        "atendimentos_por_hora": {
            "00:00": 31,
            "01:00": 23,
            "02:00": 22,
            "03:00": 3,
            "04:00": 6,
            "06:00": 2,
            "09:00": 3,
            "10:00": 4,
            "11:00": 10,
            "12:00": 30,
            "13:00": 35,
            "14:00": 31,
            "15:00": 49,
            "16:00": 43,
            "17:00": 45,
            "18:00": 30,
            "19:00": 32,
            "20:00": 29,
            "21:00": 35,
            "22:00": 24,
            "23:00": 26
        },
        "volume_conversas_por_dia": {
            "2026-02-17": 232,
            "2026-02-18": 246,
            "2026-02-19": 35
        },
        "cohort_por_dia": {
            "2026-02-17": 232,
            "2026-02-18": 246,
            "2026-02-19": 35
        },
        "compras_confirmadas": null,
        "ticket_medio": null,
        "leads_qualificados": null,
        "agendamentos": null,
        "taxa_conversao": null,
        "efetividade_lia": null
    }
}
```

### 2.1 Mapeamento para a página Visão Geral

| Campo na resposta | Tipo | Uso na Visão Geral |
|-------------------|------|---------------------|
| `total_conversas` | number | Card/indicador total de conversas |
| `mensagens_lia` | number | Card total de mensagens do agente |
| `distribuicao_por_estado` | object (nome do estado → count) | Gráfico de distribuição por estado. Chaves são **nomes completos** (ex.: "São Paulo", "Santa Catarina") para evitar siglas corrompidas ou inválidas. |
| `faixa_etaria` | object (faixa → count) | Gráfico de faixa etária |
| `menores_de_18` | number | Card menores de 18 anos |
| `percentual_menores_18` | number | Percentual sobre total de conversas |
| `fora_do_horario_count` | number | Card conversas fora do horário |
| `fora_do_horario_percent` | number | Percentual fora do horário |
| `atendimentos_por_hora` | object ("HH:00" → count) | Gráfico de atendimentos por hora do dia |
| `volume_conversas_por_dia` | object (data → count) | Gráfico volume ao longo do tempo |
| `cohort_por_dia` | object (data → count) | Cohort de conversas por dia |
| `compras_confirmadas`, `ticket_medio`, `leads_qualificados`, `agendamentos`, `taxa_conversao`, `efetividade_lia` | null (por enquanto) | Dependem de CSV ou regras de negócio; manter como null até integração futura |

Outras páginas do dashboard (além da Visão Geral) serão cobertas por chaves adicionais no mesmo objeto de resposta em versões futuras.

---

## 3. Estrutura do JSON otimizado (view=full)

Quando for necessário o relatório completo, use `?view=full`. A estrutura resumida:

### 3.1 Nível raiz

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `statusCode` | number | Ex.: 200 |
| `msg` | string | Ex.: "Report download successfully." |
| `data` | array | Lista de conversas (um item por conversa) |

### 3.2 Cada item de `data[]`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `_id` | string | ID da conversa |
| `createdAt` | string | Data/hora ISO (início da conversa) |
| `dataCollectFromUser` | object | Dados do usuário (ex.: state, birthDate) |
| `userName` | string | Nome do usuário |
| `botMessageCount` | number | Quantidade de mensagens do bot |
| `Full Conversation` | array | Histórico de mensagens; cada entrada: `message`, `sender` ("agent" ou "user") |

---

## 4. Checklist de configuração

- [ ] Base URL da API: em dev use `https://vulnerably-bilabiate-andreas.ngrok-free.dev`; em produção use variável de ambiente.
- [ ] Path do relatório: `/wrapper/report_lia`
- [ ] **Date picker da página** envia `from` e `to` (YYYY-MM-DD) na query; o front monta a URL com o período escolhido pelo usuário.
- [ ] Chamada GET sem header X-API-Key
- [ ] Tratamento da resposta: usar `response.visao_geral` para a página Visão Geral e atualizar os campos conforme a tabela 2.1
- [ ] Remoção no projeto: nenhuma menção ou tag ao nome "Lovable" (ou outra ferramenta específica) no código ou comentários; usar termos neutros (front, aplicação, dashboard, cliente).

---

## 5. URL de desenvolvimento vs produção

- **Desenvolvimento:** URL atual do ngrok: `https://vulnerably-bilabiate-andreas.ngrok-free.dev`. O período na URL (`from` e `to`) é preenchido pelo **date picker da página**.
- **Produção:** substitua a base URL pela URL definitiva da API (variável de ambiente); a lógica de montar a query com as datas do date picker permanece a mesma.
