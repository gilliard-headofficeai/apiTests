# Plano: Comparação raw vs otimizado (atualizado)

## Objetivo

- Pasta única por endpoint com: JSON bruto (backend real), JSON tratado (nosso), relatório de comparação.
- **Relatório Markdown**: métricas (tamanho, estrutura, alterações) e conclusão "Valeu a pena?".
- **Relatório HTML**: comparação visual lado a lado.

---

## Relatório HTML (comparação visual)

Gerar um arquivo **HTML** na mesma pasta do cache, por exemplo:

`cache/report_lia/comparison_from=2026-01-01_to=2026-01-14.html`

### Conteúdo do HTML

- **Duas colunas lado a lado** (layout responsivo):
  - **Coluna esquerda**: "Original (backend real)" — JSON bruto em bloco de código (`<pre>` ou `<code>`).
  - **Coluna direita**: "Otimizado (nosso)" — JSON tratado em bloco de código.
- **Snippet**: o JSON deve aparecer formatado (indentado), com quebras de linha, em fonte monoespaçada, dentro de um bloco rolável (overflow: auto) para não estourar a página.
- **Cabeçalho** opcional: endpoint, parâmetros (from, to), data da geração; e um resumo em uma linha (ex.: "Economia: X KB, Y% menor").
- **Estilo mínimo**: CSS inline ou `<style>` no próprio HTML para:
  - duas colunas (grid ou flex: 50% | 50%);
  - fundo diferenciado para o bloco de código (ex.: fundo cinza claro);
  - fonte monoespaçada e tamanho legível;
  - borda ou separador entre as colunas.

### Implementação sugerida

- Função `generate_comparison_html(raw: dict, optimized: dict, endpoint_key: str, params: dict, metrics: dict) -> str` que retorna o HTML como string.
- O JSON deve ser serializado com `json.dumps(..., ensure_ascii=False, indent=2)` e escapado para HTML (ex.: `html.escape`) antes de colocar dentro do `<pre>`.
- Salvar com o mesmo sufixo dos outros arquivos: `comparison_<suffix>.html`.
- Chamar essa função junto com a geração do relatório em Markdown (no servidor após save_optimized, e no CLI de comparação).

### Resumo dos arquivos na pasta do endpoint

| Arquivo | Descrição |
|--------|-----------|
| `raw_<params>.json` | JSON da API real |
| `optimized_<params>.json` | JSON nosso tratado |
| `comparison_<params>.md` | Relatório em Markdown (métricas e análise) |
| `comparison_<params>.html` | Comparação visual lado a lado (original \| otimizado) |
| `comparison_<params>.json` | (Opcional) Métricas em JSON |

Assim você pode abrir o `.html` no navegador e analisar visualmente as diferenças entre original e otimizado.
