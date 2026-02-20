Este documento descreve como configurar o Lovable para consumir o wrapper de relatório (report_lia) e, se necessário, como mapear/tratar o JSON otimizado para os campos dos dashboards do Lovable.

---

## 1. Configuração da API no Lovable

### 1.1 Base URL da API

Use a URL pública do ngrok (troque quando o túnel mudar):

| Campo no Lovable | Valor |
|------------------|--------|
| **Base URL** | `https://vulnerably-bilabiate-andreas.ngrok-free.dev` |

### 1.2 Endpoint do relatório

| Campo no Lovable | Valor |
|------------------|--------|
| **Path do relatório** | `/wrapper/report_lia` |

### 1.3 Chamada completa (GET)

**Resposta padrão do wrapper:** JSON tratado para dashboards (chave `visao_geral` com total_conversas, mensagens_lia, etc.). O Lovable chama uma vez e aninha `response.visao_geral` nos cards e gráficos da Visão Geral.

```
GET https://vulnerably-bilabiate-andreas.ngrok-free.dev/wrapper/report_lia?from=YYYY-MM-DD&to=YYYY-MM-DD
```

Não é necessário enviar `view=dashboard`: o wrapper já devolve o tratado por padrão. Use `view=full` só se precisar do relatório otimizado completo.

O mesmo JSON da resposta é salvo em `cache/report_lia/dashboard_liareport.json` a cada chamada, para conferência local (ex.: após testar com `https://...ngrok-free.dev/wrapper/report_lia?from=2026-01-01&to=2026-02-19`).

### 1.4 Parâmetros de query

| Parâmetro | Obrigatório | Formato | Exemplo | Descrição |
|-----------|-------------|---------|---------|-----------|
| `from` | Sim | YYYY-MM-DD | `2026-01-01` | Data inicial do período |
| `to`   | Sim | YYYY-MM-DD | `2026-01-14` | Data final do período |
| `view` | Não | string | `full` | Omitido = resposta tratada (dashboard). `view=full` = JSON otimizado completo (relatório). |

O wrapper adiciona internamente `agentId`, `by`, `messageHistory`; o Lovable envia apenas `from` e `to`.

### 1.5 Headers

- **Não** é necessário enviar `X-API-Key` (o wrapper envia para a API real).
- O Lovable pode enviar apenas `Accept: application/json` se quiser.

### 1.6 Resumo para preencher no Lovable

- **URL base da API de relatório:** `https://vulnerably-bilabiate-andreas.ngrok-free.dev`
- **Rota/caminho do relatório:** `/wrapper/report_lia`
- **Método:** GET
- **Parâmetros que o Lovable controla:** somente `from` e `to` (datas do date picker).

---

## 2. Resposta padrão (tratada para dashboards)

A resposta **padrão** do wrapper é um objeto com uma chave por página, por exemplo:

```json
{
  "visao_geral": {
    "total_conversas": 2632,
    "mensagens_lia": 18424,
    "distribuicao_por_estado": { "SP": 1380, "MG": 290, "RJ": 245, ... },
    "faixa_etaria": { "0-17": 87, "18-24": 420, "25-34": 890, ... },
    "menores_de_18": 87,
    "percentual_menores_18": 3.3,
    "fora_do_horario_count": 1000,
    "fora_do_horario_percent": 38,
    "atendimentos_por_hora": { "08:00": 120, "09:00": 180, ... },
    "volume_conversas_por_dia": { "2026-01-01": 150, "2026-01-02": 162, ... },
    "cohort_por_dia": { ... },
    "compras_confirmadas": null,
    "ticket_medio": null,
    "leads_qualificados": null,
    "agendamentos": null,
    "taxa_conversao": null,
    "efetividade_lia": null
  }
}
```

O front usa `response.visao_geral` para preencher os cards e gráficos da página Visão Geral. Campos `null` dependem de CSV ou regras de negócio (ver seção 3).

---

## 2b. Estrutura do JSON otimizado (quando usar view=full)

O que o wrapper devolve ao chamar com **`view=full`** (relatório completo):

### 2.1 Nível raiz

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `statusCode` | number | Ex.: 200 |
| `msg` | string | Ex.: "Report download successfully." |
| `status` | boolean | Ex.: true |
| `type` | string | Ex.: "Default" |
| `meta` | object | (opcional) Metadados |
| `meta.agent` | object | Dados do agente (ex.: firstName "Lia") — único no topo |
| `data` | array | Lista de conversas/relatórios (um item por conversa) |

### 2.2 Cada item de `data[]`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `_id` | string | ID da conversa |
| `createdAt` | string | Data/hora ISO (ex.: "2026-01-14T02:39:52.447Z") |
| `dataCollectFromUser` | object | Dados coletados do usuário (chaves em inglês quando há equivalente) |
| `userName` | string | Nome do usuário |
| `botMessageCount` | number | Quantidade de mensagens do bot |
| `aiId` | string | ID do agente |
| `humanEscalation` | boolean | Se houve escalação humana |
| `Full Conversation` | array | Histórico de mensagens em ordem |

### 2.3 `dataCollectFromUser` (campos comuns)

Chaves em **inglês** (padronizadas pelo wrapper):  
`name`, `birthDate`, `cpf`, `phone`, `email`, `zipCode`, `address`, `number`, `city`, `state`.  
Podem existir outras chaves (perguntas customizadas) em português.

### 2.4 Cada entrada de `Full Conversation[]`

| Campo | Tipo | Descrição |
|-------|------|-----------|
| `message` | string | Texto da mensagem (pode ter quebras `<br>`) |
| `sender` | string | `"agent"` (bot) ou `"user"` (usuário) — sempre um desses dois valores |

---

## 3. Modelagem dos dados — Visão Geral (widget a widget)

Cada gráfico/KPI abaixo indica: **fonte no JSON otimizado**, **tratamento** aplicado e se depende de **heurística** ou **CSV externo**. O JSON otimizado é suficiente para a maioria dos widgets; exceções estão marcadas.

### 3.1 Conclusão: usar JSON otimizado

O otimizador só remove duplicatas pt/en em `dataCollectFromUser`, normaliza `sender` para `"agent"`/`"user"`, coloca o agente em `meta.agent` e remove `aiAgent`/`agentId` vazio. Não remove `customer`, `distributionCenter` nem outros campos. **Usar o JSON otimizado** é suficiente e preferível (payload menor, chaves estáveis como `state`, `birthDate`).

### 3.2 Dados disponíveis por conversa (`data[]`)

| Campo | Uso nos dashboards |
|-------|--------------------|
| `_id` | Identificador único da conversa |
| `createdAt` | ISO 8601 — **único timestamp por conversa** (não por mensagem) |
| `dataCollectFromUser.state` | Distribuição por Estado |
| `dataCollectFromUser.birthDate` | Faixa etária (calcular idade: hoje - birthDate) |
| `dataCollectFromUser.customer` | Pode ser objeto ou **array**; quando array, pode ter `distributionCenter[]` com `name` (loja/CD) |
| `userName`, `botMessageCount`, `humanEscalation` | Métricas e filtros |
| `Full Conversation[]` | Cada entrada: `message` (texto), `sender` ("agent" ou "user") — **sem timestamp por mensagem** |

Kits e lojas **não** vêm em campos dedicados: aparecem no **texto das mensagens** ou em `dataCollectFromUser.customer[].distributionCenter[].name`.

---

### 3.3 Cards do topo (KPIs)

| Métrica | Fonte no JSON | Tratamento | Observação |
|---------|----------------|------------|------------|
| **Total de Conversas** | `data.length` | Nenhum | Direto. "vs Jan" exige dados de janeiro (outra chamada ou período). |
| **Mensagens da LIA** | Soma de `item.botMessageCount` em `data` | Nenhum | Direto. Se ausente, fallback: contar entradas com `sender == "agent"` em Full Conversation. |
| **Leads Qualificados** | Não existe flag | **Heurística** | Definir regra (ex.: conversa com dataCollectFromUser preenchido + N mensagens do agente). Sem regra, não dá para derivar só do JSON. |
| **Taxa de Conversão** | Calculada | (Leads Qualificados / Total de Conversas) × 100 | Depende da definição de lead qualificado. |
| **Ticket Médio** | Não está no JSON | **CSV externo** | Cruzar com CSV de vendas (ex.: por `_id` ou CPF/e-mail). |
| **Fora do Horário (19h–8h)** | `createdAt` de cada item em `data` | Para cada conversa, extrair hora de `createdAt`; contar quantas caem em 19h–08h; % = (count / total) × 100 | Limitação: só temos hora da **conversa** (início), não de cada mensagem. |
| **Menores de 18** | `dataCollectFromUser.birthDate` | Calcular idade: (hoje - birthDate); contar conversas com idade &lt; 18 | Direto. "% do total" = (menores 18 / Total de Conversas) × 100. |

---

### 3.4 Segunda linha de cards

| Métrica | Fonte no JSON | Tratamento | Observação |
|---------|----------------|------------|------------|
| **Agendamentos (visitas agendadas)** | Não existe flag | **Heurística** | Ex.: mensagem do agente com "agendar"/"visita"/"terça-feira às 14h" ou `distributionCenter` preenchido. Ou cruzar com CSV. |
| **Compras Confirmadas** | Não está no JSON | **CSV externo** | Cruzar com CSV do cliente (ex.: por CPF ou `_id` da conversa). |
| **Efetividade da LIA (agendados → compradores)** | Calculada | (Compras Confirmadas / Agendamentos) × 100 | Depende de agendamentos (heurística ou CSV) e compras (CSV). |

---

### 3.5 Gráficos — Atendimentos e volume

| Gráfico | Fonte no JSON | Tratamento | Observação |
|---------|----------------|------------|------------|
| **Atendimentos por Hora do Dia** | `createdAt` de cada item em `data` | Agrupar por hora do dia (0–23) e contar conversas | Um ponto por conversa (hora de início). |
| **Volume de Conversas ao Longo do Tempo** | `createdAt` | Agrupar por dia; contar conversas por dia. Série "Qualificados" exige definição de lead e mesmo agrupamento | Duas linhas: total conversas/dia e leads qualificados/dia (se a regra existir). |

---

### 3.6 Gráficos — Distribuição e funil

| Gráfico | Fonte no JSON | Tratamento | Observação |
|---------|----------------|------------|------------|
| **Distribuição por Estado** | `dataCollectFromUser.state` | Contar conversas por `state`; converter contagens em % do total | Chave em inglês no otimizado (`state`). Valores: siglas (SP, MG, RJ, etc.). |
| **Faixa Etária** | `dataCollectFromUser.birthDate` | Calcular idade; classificar em: Menor de 18, 18–24, 25–34, 35–44, 45–54, 55+; contar por faixa | "Menor de 18" em destaque (ex.: barra vermelha) conforme mock. |
| **Kits Mais Sugeridos** | Apenas no **texto** de `Full Conversation[].message` (sender "agent") | **Parsing**: buscar em mensagens do agente padrões como "**(Nome do Kit)**" ou "kit ... **Nome do Kit**"; normalizar nomes; contar por kit | Lista canônica de kits e mapear variações. |
| **Funil de Conversão** | Conversas: `data.length`. Demais: heurística ou CSV | Conversas = total. Leads/Agendamentos = conforme regras ou CSV. Percentuais em relação ao total | Sem definição de "qualificado" e "agendamento", usar heurísticas documentadas ou CSV. |
| **Cohort de Mensagens (conversas/dia)** | `createdAt` | Agrupar por semana (ex.: Sem 1 Jan, Sem 2 Jan) e por dia da semana (Seg–Dom); contar conversas por célula | Matriz: linhas = semanas, colunas = dias da semana. |

---

### 3.7 Top Lojas Mais Escolhidas

| Fonte no JSON | Tratamento | Observação |
|---------------|------------|------------|
| (1) `dataCollectFromUser.customer` (quando array) → `customer[].distributionCenter[].name` | Quando existir, extrair `name`; normalizar para nome de loja (ex.: "Mega Park") | Pode haver duplicata de nome em cidades diferentes; considerar chave composta (nome + cidade/UF). |
| (2) Texto em `Full Conversation[].message` | Parsing: mensagens do agente que citam loja (ex.: "Cacau Show - Mega Park") | Unificar com (1) via lista canônica de nomes. |

---

### 3.8 Resumo: o que temos vs o que falta

- **Só com o JSON otimizado:** Total de Conversas, Mensagens da LIA, Fora do Horário (por início da conversa), Menores de 18, Atendimentos por Hora, Volume de Conversas ao Longo do Tempo, Distribuição por Estado, Faixa Etária, Cohort conversas/dia. Taxa de Conversão e Efetividade dependem de definições.
- **Com heurísticas (sem CSV):** Leads Qualificados, Agendamentos, Kits Mais Sugeridos, Top Lojas (parcial), Funil (parcial). Precisam de regras de negócio documentadas.
- **Com CSV externo (obrigatório para):** Compras Confirmadas, Ticket Médio; e opcionalmente cruzamento para validar Agendamentos e Leads. Definir chave de junção (ex.: CPF, e-mail, `_id`).

---

## 4. Checklist de configuração no Lovable

- [ ] Base URL definida: `https://vulnerably-bilabiate-andreas.ngrok-free.dev`
- [ ] Path do relatório: `/wrapper/report_lia`
- [ ] Date picker envia `from` e `to` em YYYY-MM-DD
- [ ] Chamada GET sem header X-API-Key
- [ ] Tratamento da resposta: usar `response.data` como lista de conversas
- [ ] Para cada conversa: `item["Full Conversation"]` na ordem; `item.dataCollectFromUser` para dados do usuário; `sender` sempre `"agent"` ou `"user"`

---

## 5. Atualizar quando o ngrok mudar

Se a URL do ngrok for alterada (ex.: novo túnel), atualize:

1. Este arquivo: seção 1.1 e 1.6 (Base URL).
2. A configuração no Lovable (campo onde está a base URL da API de relatório).
