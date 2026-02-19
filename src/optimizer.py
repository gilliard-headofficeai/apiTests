"""
Otimização do JSON da API: remove duplicatas e reduz estrutura repetida,
mantendo ordem das mensagens e consistência dos dados.
"""
from copy import deepcopy

# Mapeamento pt -> en para dataCollectFromUser (manter um conjunto canônico em inglês)
_DATA_COLLECT_PT_TO_EN = {
    "nome completo": "name",
    "data de nascimento": "birthDate",
    "cpf": "cpf",
    "celular": "phone",
    "e-mail": "email",
    "cep": "zipCode",
    "endereço": "address",
    "número": "number",
    "cidade": "city",
    "estado": "state",
}


def _consolidate_data_collect_from_user(obj: dict) -> dict:
    """
    Remove duplicatas pt/en em dataCollectFromUser.
    Mantém um único conjunto: preferir chaves em inglês quando existir par pt/en.
    """
    if not obj or not isinstance(obj, dict):
        return obj
    out = {}
    seen_en = set()
    for key, value in obj.items():
        en_key = _DATA_COLLECT_PT_TO_EN.get(key)
        if en_key is not None:
            if en_key not in seen_en:
                out[en_key] = value
                seen_en.add(en_key)
        else:
            out[key] = value
    return out


def _normalize_sender(sender_value: list | dict) -> str:
    """Normaliza sender para 'agent' (tinha firstName) ou 'user' (array vazio)."""
    if isinstance(sender_value, list):
        if not sender_value:
            return "user"
        first = sender_value[0] if sender_value else {}
        if isinstance(first, dict) and first.get("firstName"):
            return "agent"
        return "user"
    return "user"


def _optimize_conversation_item(item: dict, agent_at_root: dict | None) -> dict:
    """
    Otimiza um item do array data: consolida dataCollectFromUser,
    substitui sender em Full Conversation, remove aiAgent e agentId vazio.
    agent_at_root: dict que será preenchido com o primeiro aiAgent encontrado.
    """
    item = deepcopy(item)
    if "dataCollectFromUser" in item and item["dataCollectFromUser"]:
        item["dataCollectFromUser"] = _consolidate_data_collect_from_user(
            item["dataCollectFromUser"]
        )
    if "Full Conversation" in item and isinstance(item["Full Conversation"], list):
        for entry in item["Full Conversation"]:
            if isinstance(entry, dict) and "sender" in entry:
                entry["sender"] = _normalize_sender(entry["sender"])
    if agent_at_root is not None and "aiAgent" in item and not agent_at_root:
        agent_at_root.update(item.get("aiAgent") or {})
    item.pop("aiAgent", None)
    if item.get("agentId") == []:
        item.pop("agentId", None)
    return item


def optimize_report_response(data: dict) -> dict:
    """
    Recebe o JSON da resposta da API de report (statusCode, msg, data, ...).
    Retorna um novo dict otimizado com meta.agent no topo e data processado.
    """
    if not data or not isinstance(data, dict):
        return data
    result = deepcopy(data)
    result.pop("data", None)
    # meta.agent: único no topo
    meta_agent = {}
    if "data" in data and isinstance(data["data"], list):
        optimized_data = []
        for item in data["data"]:
            optimized_data.append(
                _optimize_conversation_item(item, meta_agent)
            )
        result["data"] = optimized_data
    if meta_agent:
        if "meta" not in result:
            result["meta"] = {}
        result["meta"]["agent"] = meta_agent
    return result
