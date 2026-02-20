# Guia de configuração — API de relatório para dashboards

Este documento descreve como configurar a aplicação de front/dashboard para consumir o wrapper de relatório (`report_lia`), quais campos da resposta usar e como trocar a URL de desenvolvimento (ngrok) pela URL de produção depois.

**Condições atuais:**
- A resposta padrão do wrapper é um JSON tratado por página. **De momento apenas a página "Visão Geral" está coberta** por esse formato; outras páginas terão chaves adicionais no futuro.
- A **URL base da API** (ngrok em desenvolvimento) deve ser tratada como **placeholder**: use uma variável de ambiente ou constante (ex.: `REPORT_API_BASE_URL`) para poder trocar por uma URL de produção sem alterar código.

**Requisito de código:** Remover de **todo o projeto** menções e tags ao nome "Lovable" (ou qualquer ferramenta específica). O repositório deve ser agnóstico de ferramenta: referir-se a "front", "aplicação", "dashboard" ou "cliente" em comentários e documentação.

---

## 1. Configuração da API

### 1.1 Base URL da API (placeholder)

Use um **placeholder** configurável (variável de ambiente ou constante) para a URL base, a ser trocada por produção depois:

| Uso | Valor sugerido |
|-----|----------------|
| **Desenvolvimento** | URL do ngrok enquanto o túnel estiver ativo (ex.: `https://xxxx.ngrok-free.dev`) |
| **Produção** | URL definitiva da API de relatórios (substituir o placeholder ao fazer deploy) |

Exemplo de placeholder no código: `REPORT_API_BASE_URL` ou `VITE_REPORT_API_BASE_URL` (ou equivalente no seu stack). **Não** hardcodar a URL do ngrok; ao mudar o túnel ou ir para produção, apenas altere a variável.

### 1.2 Endpoint do relatório

| Campo | Valor |
|-------|--------|
| **Path do relatório** | `/wrapper/report_lia` |

Chamada completa: `GET {BASE_URL}/wrapper/report_lia?from=YYYY-MM-DD&to=YYYY-MM-DD`

### 1.3 Resposta padrão

A resposta **padrão** do wrapper (sem `view=full`) é o JSON tratado para dashboards. O front chama uma vez e usa `response.visao_geral` para preencher a página **Visão Geral**. Não é necessário enviar `view=dashboard`; use `view=full` só se precisar do relatório otimizado completo.

O mesmo JSON é salvo em `cache/report_lia/dashboard_liareport.json` a cada chamada, para conferência local.

### 1.4 Parâmetros de query

| Parâmetro | Obrigatório | Formato | Exemplo | Descrição |
|-----------|-------------|---------|---------|-----------|
| `from` | Sim | YYYY-MM-DD | `2026-02-17` | Data inicial do período |
| `to`   | Sim | YYYY-MM-DD | `2026-02-19` | Data final do período |
| `view` | Não | string | `full` | Omitido = resposta tratada (dashboard). `view=full` = JSON otimizado completo. |

O wrapper adiciona internamente `agentId`, `by`, `messageHistory`; o cliente envia apenas `from` e `to`.

### 1.5 Headers

- Não é necessário enviar `X-API-Key` (o wrapper envia para a API real).
- O cliente pode enviar `Accept: application/json` se quiser.

### 1.6 Resumo de configuração

- **URL base:** usar placeholder (ex.: variável de ambiente), substituível por ngrok em dev ou URL de produção.
- **Rota do relatório:** `/wrapper/report_lia`
- **Método:** GET
- **Parâmetros controlados pelo front:** somente `from` e `to` (datas do seletor de período).

---

## 2. Resposta tratada — Visão Geral (exemplo real)

A resposta padrão é um objeto com uma chave por página. **Atualmente está implementada apenas a chave `visao_geral`**, que alimenta a página **Visão Geral**. Os campos abaixo devem ser atualizados no front com os valores recebidos.

### 2.0 Conferir e chamar no front

- **URL de exemplo (troque pela sua base URL / ngrok):**  
  `GET {BASE_URL}/wrapper/report_lia?from=2026-02-17&to=2026-02-19`
- **Método:** GET, sem `X-API-Key`.
- **Resposta:** objeto com `visao_geral`; use `response.visao_geral` para preencher cards e gráficos.
- **Conferência:** para o mesmo período, a resposta deve bater com o JSON abaixo (ou com o arquivo `cache/report_lia/dashboard_liareport.json` após uma chamada local). Se a base URL estiver correta e o wrapper estiver no ar, o front deve receber exatamente essa estrutura.

Exemplo real (período 2026-02-17 a 2026-02-19 — mesmo retorno que o wrapper devolve e que fica em `dashboard_liareport.json`):

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

- [ ] Base URL da API em placeholder (variável de ambiente ou constante), sem URL do ngrok hardcoded.
- [ ] Path do relatório: `/wrapper/report_lia`
- [ ] Seletor de período envia `from` e `to` em YYYY-MM-DD
- [ ] Chamada GET sem header X-API-Key
- [ ] Tratamento da resposta: usar `response.visao_geral` para a página Visão Geral e atualizar os campos conforme a tabela 2.1
- [ ] Remoção no projeto: nenhuma menção ou tag ao nome "Lovable" (ou outra ferramenta específica) no código ou comentários; usar termos neutros (front, aplicação, dashboard, cliente).

---

## 5. URL de desenvolvimento vs produção

- **Durante o desenvolvimento:** use a URL do ngrok no placeholder (ex.: variável de ambiente). Quando o túnel mudar, atualize apenas essa variável.
- **Em produção:** substitua o placeholder pela URL definitiva da API de relatórios; não deve ser necessário alterar lógica de código, apenas a configuração da base URL.
