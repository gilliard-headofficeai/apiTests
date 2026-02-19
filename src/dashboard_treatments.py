"""
Tratamento do JSON otimizado para o dashboard (Visão Geral e outras páginas).
A partir do payload otimizado da API de report, calcula métricas agregadas que o front
pode consumir em uma única chamada, sem expor o JSON bruto.
Responsabilidade: derivar total_conversas, mensagens_lia, distribuição por estado, faixa etária, atendimentos por hora, etc.; pode ser chamado por uma rota de dashboard ou via CLI (python -m src.dashboard_treatments).
"""
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any


def _parse_date(value: Any) -> datetime | None:
    """Tenta extrair um datetime de string ou número (timestamp ms). Retorna None se inválido."""
    if value is None:
        return None
    if isinstance(value, (int, float)):
        try:
            if value > 1e12:
                value = value / 1000.0
            return datetime.utcfromtimestamp(value)
        except (OSError, ValueError):
            return None
    if isinstance(value, str):
        for fmt in ("%Y-%m-%dT%H:%M:%S.%fZ", "%Y-%m-%dT%H:%M:%SZ", "%Y-%m-%d %H:%M:%S", "%Y-%m-%d"):
            try:
                return datetime.strptime(value.replace("Z", "").split(".")[0], fmt.replace(".%f", "").replace("Z", ""))
            except ValueError:
                continue
        try:
            return datetime.fromisoformat(value.replace("Z", "+00:00"))
        except ValueError:
            pass
    return None


def _idade_em_anos(data_nascimento: Any) -> int | None:
    """Calcula idade em anos a partir de data de nascimento (string ou timestamp). Retorna None se inválido."""
    dt = _parse_date(data_nascimento)
    if dt is None:
        return None
    hoje = datetime.now(timezone.utc)
    anos = hoje.year - dt.year
    if (hoje.month, hoje.day) < (dt.month, dt.day):
        anos -= 1
    return anos if anos >= 0 else None


def _extrair_estado(item: dict) -> str | None:
    """Extrai estado do item (dataCollectFromUser.state). Retorna string normalizada ou None."""
    dcu = item.get("dataCollectFromUser") if isinstance(item.get("dataCollectFromUser"), dict) else {}
    state = dcu.get("state")
    if state is None or not isinstance(state, str):
        return None
    return state.strip().upper()[:2] if state.strip() else None


def _extrair_data_atendimento(item: dict) -> datetime | None:
    """Extrai data/hora do atendimento (createdAt no item ou primeiro uso). Retorna None se ausente."""
    created = item.get("createdAt")
    if created is not None:
        return _parse_date(created)
    # Fallback: não temos createdAt em todos os relatórios
    return None


def _contar_mensagens_agente(item: dict) -> int:
    """Conta mensagens da LIA (sender == 'agent') em Full Conversation. Fallback quando botMessageCount ausente."""
    fc = item.get("Full Conversation")
    if not isinstance(fc, list):
        return 0
    return sum(1 for e in fc if isinstance(e, dict) and e.get("sender") == "agent")


def _mensagens_lia_item(item: dict) -> int:
    """Mensagens da LIA: usa botMessageCount quando presente e numérico, senão conta em Full Conversation."""
    count = item.get("botMessageCount")
    if isinstance(count, (int, float)) and count >= 0:
        return int(count)
    return _contar_mensagens_agente(item)


def _esta_fora_do_horario(dt: datetime) -> bool:
    """Retorna True se a hora está no intervalo 19h–08h (inclusive 19h, exclusive 09h). Usa UTC."""
    hour = dt.hour
    return hour >= 19 or hour < 8


def build_visao_geral(optimized: dict) -> dict:
    """
    A partir do JSON otimizado do report, monta o payload da página Visão Geral.
    Inclui totais, distribuição por estado, faixa etária, menores de 18, atendimentos por hora, etc.
    Campos que dependem de CSV ou heurísticas complexas ficam null/zero com indicação.
    """
    data = optimized.get("data") if isinstance(optimized.get("data"), list) else []
    total_conversas = len(data)

    mensagens_lia = 0
    distribuicao_por_estado = defaultdict(int)
    idades = []
    menores_de_18 = 0
    fora_do_horario_count = 0
    atendimentos_por_hora = defaultdict(int)
    volume_por_dia = defaultdict(int)
    cohort_por_dia = defaultdict(int)

    for item in data:
        if not isinstance(item, dict):
            continue
        mensagens_lia += _mensagens_lia_item(item)
        estado = _extrair_estado(item)
        if estado:
            distribuicao_por_estado[estado] += 1
        dcu = item.get("dataCollectFromUser") if isinstance(item.get("dataCollectFromUser"), dict) else {}
        birth = dcu.get("birthDate")
        idade = _idade_em_anos(birth)
        if idade is not None:
            idades.append(idade)
            if idade < 18:
                menores_de_18 += 1
        dt = _extrair_data_atendimento(item)
        if dt:
            if _esta_fora_do_horario(dt):
                fora_do_horario_count += 1
            atendimentos_por_hora[dt.strftime("%H:00")] += 1
            volume_por_dia[dt.strftime("%Y-%m-%d")] += 1
            cohort_por_dia[dt.strftime("%Y-%m-%d")] += 1

    # Faixa etária: buckets
    faixa_etaria = {"0-17": 0, "18-24": 0, "25-34": 0, "35-44": 0, "45-54": 0, "55+": 0}
    for i in idades:
        if i < 18:
            faixa_etaria["0-17"] += 1
        elif i <= 24:
            faixa_etaria["18-24"] += 1
        elif i <= 34:
            faixa_etaria["25-34"] += 1
        elif i <= 44:
            faixa_etaria["35-44"] += 1
        elif i <= 54:
            faixa_etaria["45-54"] += 1
        else:
            faixa_etaria["55+"] += 1

    # Percentuais (quando total > 0)
    percentual_menores_18 = round((menores_de_18 / total_conversas * 100), 2) if total_conversas else 0
    fora_do_horario_percent = round((fora_do_horario_count / total_conversas * 100), 2) if total_conversas else 0

    return {
        "total_conversas": total_conversas,
        "mensagens_lia": mensagens_lia,
        "distribuicao_por_estado": dict(distribuicao_por_estado),
        "faixa_etaria": faixa_etaria,
        "menores_de_18": menores_de_18,
        "percentual_menores_18": percentual_menores_18,
        "fora_do_horario_count": fora_do_horario_count,
        "fora_do_horario_percent": fora_do_horario_percent,
        "atendimentos_por_hora": dict(sorted(atendimentos_por_hora.items())),
        "volume_conversas_por_dia": dict(sorted(volume_por_dia.items())),
        "cohort_por_dia": dict(sorted(cohort_por_dia.items())),
        # Campos que exigem CSV ou heurísticas; deixar indicado para o front
        "compras_confirmadas": None,
        "ticket_medio": None,
        "leads_qualificados": None,
        "agendamentos": None,
        "taxa_conversao": None,
        "efetividade_lia": None,
    }


def build_dashboard_payload(optimized: dict) -> dict:
    """
    Retorna o payload completo do dashboard: uma chave por "página".
    O front (ex.: Lovable) chama uma única API e aninha por tela.
    """
    return {
        "visao_geral": build_visao_geral(optimized),
    }


if __name__ == "__main__":
    """
    Teste: carrega o JSON otimizado mais recente do cache (report_lia) ou de um arquivo,
    aplica o tratamento da visão geral e imprime o JSON resultante.
    Uso:
      python -m src.dashboard_treatments
      python -m src.dashboard_treatments --file path/to/optimized.json
    """
    import argparse
    import json
    import sys
    from pathlib import Path

    sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

    parser = argparse.ArgumentParser(description="Calcula métricas do dashboard a partir do JSON otimizado.")
    parser.add_argument("--file", type=str, default=None, help="Caminho para um arquivo optimized_*.json (opcional).")
    parser.add_argument("--endpoint", type=str, default="report_lia", help="Chave do endpoint quando não usa --file.")
    args = parser.parse_args()

    if args.file:
        path = Path(args.file)
        if not path.exists():
            print(f"Arquivo não encontrado: {path}", file=sys.stderr)
            sys.exit(1)
        with open(path, encoding="utf-8") as f:
            optimized = json.load(f)
        print(f"# Carregado: {path}", file=sys.stderr)
    else:
        from src.compare_report import load_raw_and_optimized

        raw, optimized = load_raw_and_optimized(args.endpoint, params=None)
        if optimized is None:
            print("Nenhum JSON otimizado encontrado no cache. Use --file <path> ou rode o wrapper antes.", file=sys.stderr)
            sys.exit(1)
        print(f"# Cache: par mais recente do endpoint {args.endpoint}", file=sys.stderr)

    payload = build_dashboard_payload(optimized)
    print(json.dumps(payload, ensure_ascii=False, indent=2))
