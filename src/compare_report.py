"""
Comparação entre JSON bruto (backend real) e JSON otimizado (nosso).
Gera relatório em Markdown, HTML lado a lado e opcionalmente métricas em JSON.
"""
import html
import json
import re
from datetime import datetime
from pathlib import Path

from src.storage import get_cache_folder, _suffix_from_params

# Chaves em pt que o optimizer consolida para en (espelho do optimizer)
_DATA_COLLECT_PT_KEYS = {
    "nome completo", "data de nascimento", "cpf", "celular", "e-mail",
    "cep", "endereço", "número", "cidade", "estado",
}


def _safe_suffix(params: dict | None) -> str:
    """Sufixo seguro para nomes de arquivo (alinhado ao storage)."""
    suffix = _suffix_from_params(params)
    return re.sub(r"[^\w\-=.]", "_", suffix)


def get_raw_and_optimized_paths(endpoint_key: str, params: dict | None) -> tuple[Path | None, Path | None]:
    """
    Retorna (path_raw, path_optimized) para o endpoint e params.
    Se params for None, tenta usar o par mais recente no folder (por data de modificação).
    """
    folder = get_cache_folder(endpoint_key)
    if params is not None:
        safe = _safe_suffix(params)
        raw_path = folder / f"raw_{safe}.json"
        opt_path = folder / f"optimized_{safe}.json"
        return (raw_path if raw_path.exists() else None, opt_path if opt_path.exists() else None)
    # Par mais recente: procurar raw_*.json e paired optimized
    raw_files = sorted(folder.glob("raw_*.json"), key=lambda p: p.stat().st_mtime, reverse=True)
    for raw_path in raw_files:
        suffix = raw_path.stem.replace("raw_", "")
        opt_path = folder / f"optimized_{suffix}.json"
        if opt_path.exists():
            return (raw_path, opt_path)
    return (None, None)


def load_raw_and_optimized(endpoint_key: str, params: dict | None = None) -> tuple[dict | None, dict | None]:
    """
    Carrega os dois JSONs do cache. Retorna (raw_dict, optimized_dict) ou (None, None).
    """
    raw_path, opt_path = get_raw_and_optimized_paths(endpoint_key, params)
    if not raw_path or not opt_path:
        return (None, None)
    try:
        with open(raw_path, encoding="utf-8") as f:
            raw = json.load(f)
        with open(opt_path, encoding="utf-8") as f:
            optimized = json.load(f)
        return (raw, optimized)
    except (json.JSONDecodeError, OSError):
        return (None, None)


def compare_responses(raw: dict, optimized: dict) -> dict:
    """
    Compara os dois JSONs e retorna um dict de métricas e resumos.
    """
    raw_str = json.dumps(raw, ensure_ascii=False, indent=2)
    opt_str = json.dumps(optimized, ensure_ascii=False, indent=2)
    size_raw = len(raw_str.encode("utf-8"))
    size_opt = len(opt_str.encode("utf-8"))
    saved = size_raw - size_opt
    saved_pct = (saved / size_raw * 100) if size_raw else 0

    data_raw = raw.get("data") if isinstance(raw.get("data"), list) else []
    data_opt = optimized.get("data") if isinstance(optimized.get("data"), list) else []
    data_count_raw = len(data_raw)
    data_count_opt = len(data_opt)

    def count_full_conversation_entries(items: list) -> int:
        total = 0
        for it in items:
            if isinstance(it, dict) and isinstance(it.get("Full Conversation"), list):
                total += len(it["Full Conversation"])
        return total

    fc_raw = count_full_conversation_entries(data_raw)
    fc_opt = count_full_conversation_entries(data_opt)

    # Otimizações aplicadas
    items_with_ai_agent_raw = sum(1 for it in data_raw if isinstance(it, dict) and "aiAgent" in it and it.get("aiAgent"))
    items_with_ai_agent_opt = sum(1 for it in data_opt if isinstance(it, dict) and "aiAgent" in it and it.get("aiAgent"))
    has_meta_agent = bool(optimized.get("meta") and optimized["meta"].get("agent"))

    empty_agent_id_raw = sum(1 for it in data_raw if isinstance(it, dict) and it.get("agentId") == [])
    empty_agent_id_opt = sum(1 for it in data_opt if isinstance(it, dict) and it.get("agentId") == [])

    sender_normalized = 0
    data_collect_pt_consolidated = 0
    for i, (r, o) in enumerate(zip(data_raw, data_opt)):
        if not isinstance(r, dict) or not isinstance(o, dict):
            continue
        r_fc = r.get("Full Conversation") if isinstance(r.get("Full Conversation"), list) else []
        o_fc = o.get("Full Conversation") if isinstance(o.get("Full Conversation"), list) else []
        for rent, oent in zip(r_fc, o_fc):
            if isinstance(rent, dict) and isinstance(oent, dict) and "sender" in rent and "sender" in oent:
                rs = rent["sender"]
                os_val = oent["sender"]
                if isinstance(os_val, str) and (isinstance(rs, (list, dict)) or rs != os_val):
                    sender_normalized += 1
        r_dc = r.get("dataCollectFromUser") if isinstance(r.get("dataCollectFromUser"), dict) else {}
        o_dc = o.get("dataCollectFromUser") if isinstance(o.get("dataCollectFromUser"), dict) else {}
        pt_keys_here = sum(1 for k in r_dc if k in _DATA_COLLECT_PT_KEYS)
        if pt_keys_here or len(r_dc) != len(o_dc):
            data_collect_pt_consolidated += pt_keys_here

    return {
        "size_raw_bytes": size_raw,
        "size_optimized_bytes": size_opt,
        "size_saved_bytes": saved,
        "size_saved_percent": round(saved_pct, 2),
        "data_count_raw": data_count_raw,
        "data_count_optimized": data_count_opt,
        "full_conversation_entries_raw": fc_raw,
        "full_conversation_entries_optimized": fc_opt,
        "items_with_ai_agent_removed": items_with_ai_agent_raw - items_with_ai_agent_opt,
        "meta_agent_at_root": has_meta_agent,
        "empty_agent_id_removed": empty_agent_id_raw - empty_agent_id_opt,
        "sender_entries_normalized": sender_normalized,
        "data_collect_pt_keys_consolidated": data_collect_pt_consolidated,
        "summary_removed": [
            "aiAgent removido de cada item e extraído para meta.agent" if items_with_ai_agent_raw > items_with_ai_agent_opt else None,
            "agentId vazio removido dos itens" if empty_agent_id_raw > empty_agent_id_opt else None,
        ],
        "summary_added": [
            "meta.agent no topo (agente único)" if has_meta_agent else None,
        ],
        "summary_normalized": [
            "sender em Full Conversation: objeto/array → 'agent' ou 'user'" if sender_normalized else None,
            "dataCollectFromUser: chaves em pt consolidadas para en" if data_collect_pt_consolidated else None,
        ],
    }


def generate_comparison_report(
    raw: dict, optimized: dict, endpoint_key: str, params: dict | None, metrics: dict
) -> str:
    """Gera o conteúdo Markdown do relatório de comparação."""
    lines = [
        f"# Comparação: Original vs Otimizado — `{endpoint_key}`",
        "",
        f"**Data da geração:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC",
        "",
    ]
    if params:
        lines.append("**Parâmetros:** " + ", ".join(f"`{k}={v}`" for k, v in sorted(params.items()) if v))
        lines.append("")

    lines.extend([
        "## Tamanho",
        "",
        f"- **Original (backend real):** {metrics['size_raw_bytes']:,} bytes ({metrics['size_raw_bytes'] / 1024:.2f} KB)",
        f"- **Otimizado (nosso):** {metrics['size_optimized_bytes']:,} bytes ({metrics['size_optimized_bytes'] / 1024:.2f} KB)",
        f"- **Economia:** {metrics['size_saved_bytes']:,} bytes ({metrics['size_saved_percent']}% menor)",
        "",
        "## Estrutura",
        "",
        f"- Itens em `data`: {metrics['data_count_raw']} (original) → {metrics['data_count_optimized']} (otimizado)",
        f"- Total de entradas em \"Full Conversation\": {metrics['full_conversation_entries_raw']} → {metrics['full_conversation_entries_optimized']}",
        "",
        "## Alterações aplicadas",
        "",
    ])

    if metrics.get("items_with_ai_agent_removed", 0):
        lines.append(f"- **aiAgent:** removido de {metrics['items_with_ai_agent_removed']} itens; primeiro agente extraído para `meta.agent`.")
    if metrics.get("empty_agent_id_removed", 0):
        lines.append(f"- **agentId vazio:** removido de {metrics['empty_agent_id_removed']} itens.")
    if metrics.get("sender_entries_normalized", 0):
        lines.append(f"- **sender:** {metrics['sender_entries_normalized']} entradas normalizadas para \"agent\" ou \"user\".")
    if metrics.get("data_collect_pt_keys_consolidated", 0):
        lines.append(f"- **dataCollectFromUser:** {metrics['data_collect_pt_keys_consolidated']} chaves em português consolidadas para inglês.")

    lines.extend(["", "## Conclusão: Valeu a pena?", ""])
    saved_pct = metrics.get("size_saved_percent", 0)
    if saved_pct > 0:
        lines.append(f"Sim. O payload ficou **{saved_pct}% menor**, com menos redundância (agente único em `meta.agent`, sem `aiAgent` repetido em cada item). O front pode usar um único `meta.agent` e um formato de `sender` mais simples.")
    else:
        lines.append("A otimização reduz redundância e padroniza o formato (sender, dataCollectFromUser, meta.agent), mesmo quando a economia de bytes é pequena. O front se beneficia de uma estrutura mais limpa e previsível.")
    lines.append("")
    return "\n".join(lines)


def generate_comparison_html(
    raw: dict, optimized: dict, endpoint_key: str, params: dict | None, metrics: dict
) -> str:
    """Gera HTML com duas colunas: Original | Otimizado (JSON formatado, rolável)."""
    raw_json = json.dumps(raw, ensure_ascii=False, indent=2)
    opt_json = json.dumps(optimized, ensure_ascii=False, indent=2)
    raw_escaped = html.escape(raw_json)
    opt_escaped = html.escape(opt_json)

    params_str = ", ".join(f"{k}={v}" for k, v in sorted((params or {}).items()) if v)
    saved_kb = metrics.get("size_saved_bytes", 0) / 1024
    saved_pct = metrics.get("size_saved_percent", 0)
    summary_line = f"Economia: {saved_kb:.2f} KB ({saved_pct}% menor)" if metrics.get("size_saved_bytes", 0) > 0 else "Estrutura simplificada (veja o relatório .md)."

    return f"""<!DOCTYPE html>
<html lang="pt-BR">
<head>
  <meta charset="utf-8">
  <title>Comparação: {html.escape(endpoint_key)}</title>
  <style>
    * {{ box-sizing: border-box; }}
    body {{ font-family: system-ui, sans-serif; margin: 0; padding: 1rem; background: #f5f5f5; }}
    h1 {{ font-size: 1.25rem; margin: 0 0 0.5rem 0; }}
    .meta {{ font-size: 0.875rem; color: #555; margin-bottom: 1rem; }}
    .summary {{ font-size: 0.9rem; margin-bottom: 1rem; padding: 0.5rem; background: #e8f5e9; border-radius: 4px; }}
    .columns {{ display: flex; gap: 0; min-height: 80vh; }}
    .col {{ flex: 1; display: flex; flex-direction: column; border: 1px solid #ccc; background: #fff; }}
    .col:first-child {{ border-right: none; }}
    .col h2 {{ margin: 0; padding: 0.5rem 1rem; font-size: 1rem; background: #eee; border-bottom: 1px solid #ccc; }}
    .col pre {{ flex: 1; margin: 0; padding: 1rem; overflow: auto; font-family: ui-monospace, monospace; font-size: 12px; line-height: 1.4; white-space: pre-wrap; word-break: break-all; background: #fafafa; }}
  </style>
</head>
<body>
  <h1>Comparação: Original (backend real) | Otimizado (nosso)</h1>
  <div class="meta">Endpoint: {html.escape(endpoint_key)} | Parâmetros: {html.escape(params_str or "—")} | Gerado em {datetime.utcnow().strftime("%Y-%m-%d %H:%M")} UTC</div>
  <div class="summary">{html.escape(summary_line)}</div>
  <div class="columns">
    <div class="col">
      <h2>Original (backend real)</h2>
      <pre>{raw_escaped}</pre>
    </div>
    <div class="col">
      <h2>Otimizado (nosso)</h2>
      <pre>{opt_escaped}</pre>
    </div>
  </div>
</body>
</html>"""


def save_comparison_report(
    endpoint_key: str,
    params: dict | None,
    report_md: str,
    report_html: str,
    metrics: dict,
) -> tuple[Path, Path, Path]:
    """
    Salva relatório .md, .html e opcionalmente .json de métricas na pasta do endpoint.
    Retorna (path_md, path_html, path_json).
    """
    folder = get_cache_folder(endpoint_key)
    safe = _safe_suffix(params)
    path_md = folder / f"comparison_{safe}.md"
    path_html = folder / f"comparison_{safe}.html"
    path_json = folder / f"comparison_{safe}.json"

    path_md.write_text(report_md, encoding="utf-8")
    path_html.write_text(report_html, encoding="utf-8")

    # Métricas em JSON (sem dados brutos, só números e listas de resumo)
    metrics_serializable = {}
    for k, v in metrics.items():
        if isinstance(v, (int, float, str, bool, type(None))):
            metrics_serializable[k] = v
        elif isinstance(v, list):
            metrics_serializable[k] = [x for x in v if x is not None]
    path_json.write_text(json.dumps(metrics_serializable, ensure_ascii=False, indent=2), encoding="utf-8")

    return (path_md, path_html, path_json)


def run_comparison(
    endpoint_key: str,
    params: dict | None,
    raw: dict | None = None,
    optimized: dict | None = None,
) -> tuple[Path, Path, Path] | None:
    """
    Carrega (ou usa os dicts passados), compara, gera e salva relatório .md, .html e .json.
    Retorna (path_md, path_html, path_json) ou None se não houver par para comparar.
    """
    if raw is None or optimized is None:
        raw, optimized = load_raw_and_optimized(endpoint_key, params)
    if raw is None or optimized is None:
        return None
    metrics = compare_responses(raw, optimized)
    report_md = generate_comparison_report(raw, optimized, endpoint_key, params, metrics)
    report_html = generate_comparison_html(raw, optimized, endpoint_key, params, metrics)
    return save_comparison_report(endpoint_key, params, report_md, report_html, metrics)


if __name__ == "__main__":
    import argparse
    import sys
    from pathlib import Path
    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    parser = argparse.ArgumentParser(description="Gera relatório de comparação (raw vs otimizado) a partir do cache.")
    parser.add_argument("endpoint", help="Chave do endpoint (ex: report_lia)")
    parser.add_argument("--from", dest="from_", default=None, help="Parâmetro from (data início)")
    parser.add_argument("--to", default=None, help="Parâmetro to (data fim)")
    parser.add_argument("--agentId", default=None, help="Parâmetro agentId (opcional)")
    args = parser.parse_args()

    params = {}
    if args.from_:
        params["from"] = args.from_
    if args.to:
        params["to"] = args.to
    if args.agentId:
        params["agentId"] = args.agentId
    params = params or None

    result = run_comparison(args.endpoint, params)
    if result is None:
        print("Nenhum par raw/optimized encontrado no cache para este endpoint e parâmetros.", file=sys.stderr)
        sys.exit(1)
    path_md, path_html, path_json = result
    print(f"Relatório gerado:")
    print(f"  MD:   {path_md}")
    print(f"  HTML: {path_html}")
    print(f"  JSON: {path_json}")
