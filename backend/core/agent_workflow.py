from functools import lru_cache
from typing import Any, TypedDict

from settings.config import get_settings


MEDICAL_SAFETY_TEXT = "以下内容仅供参考，不能替代兽医诊断。"
HIGH_RISK_TEXT = "你描述的情况可能存在急症风险，请尽快联系线下兽医或宠物医院。"


class QaWorkflowState(TypedDict, total=False):
    question: str
    risk_level: str
    history: list[dict[str, str]]
    rag_context: str
    answer: str
    references: str | None


class GuideRecommendationState(TypedDict, total=False):
    product_id: int
    sku_id: int | None
    rank: int
    reason: str
    caution: str | None
    source: str


class GuideWorkflowState(TypedDict, total=False):
    question: str
    risk_level: str
    history: list[dict[str, str]]
    rag_context: str
    pet_summary: dict[str, Any] | None
    products: list[dict[str, Any]]
    answer: str
    recommendations: list[GuideRecommendationState]
    references: str | None


GUIDE_MEDICAL_SAFETY_TEXT = (
    "Medical, medication, prescription diet, or emergency content is for reference only "
    "and cannot replace a veterinarian diagnosis."
)
GUIDE_HIGH_RISK_TEXT = "For possible emergency symptoms, contact an offline veterinarian as soon as possible."


def build_rule_based_qa_answer(risk_level: str) -> str:
    base = "我会先根据你提供的信息给出日常养宠建议。"
    if risk_level == "high":
        return f"{base} {HIGH_RISK_TEXT}{MEDICAL_SAFETY_TEXT}"
    if risk_level == "medical":
        return (
            f"{base} 涉及医疗、用药、疫苗或驱虫时，{MEDICAL_SAFETY_TEXT}"
            "不要自行使用处方药或调整剂量。"
        )
    return f"{base} 当前问题暂未命中医疗高风险规则，后续可接入平台知识库和私人知识库后给出更具体回答。"


def _build_system_prompt(risk_level: str, has_rag_context: bool) -> str:
    rag_instruction = (
        "已提供 RAG 检索摘要时，可以基于摘要回答，但不能夸大为完整诊断；"
        if has_rag_context
        else "当前没有可用 RAG 检索摘要，不能声称引用了私人知识库、平台知识库或宠物档案。"
    )
    return (
        "你是宠物综合服务平台的养宠知识问答助手。"
        "请用中文回答，表达清晰、谨慎、可执行。"
        f"{rag_instruction}"
        "不知道时要说明信息不足，不要编造诊断、药品剂量、检查结果或平台不存在的数据。"
        f"当前风险等级：{risk_level}。"
        "如果涉及医疗、用药、疫苗、驱虫、急症或疑似疾病，必须提示仅供参考，不能替代兽医诊断。"
        "如果可能存在急症风险，必须建议尽快线下就医。"
    )


def _normalize_history(history: list[dict[str, str]] | None) -> str:
    if not history:
        return ""
    recent = history[-8:]
    lines = []
    for item in recent:
        role = item.get("role", "unknown")
        content = item.get("content", "")
        lines.append(f"{role}: {content}")
    return "\n".join(lines)


async def _call_deepseek(
    question: str,
    risk_level: str,
    history: list[dict[str, str]] | None,
    rag_context: str | None,
) -> str | None:
    settings = get_settings()
    if settings.llm_provider != "deepseek" or not settings.llm_api_key:
        return None
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_deepseek import ChatDeepSeek
    except ImportError:
        return None

    llm = ChatDeepSeek(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        temperature=settings.llm_temperature,
    )
    history_text = _normalize_history(history)
    user_prompt = f"用户问题：{question}"
    if rag_context:
        user_prompt = f"RAG 检索摘要：\n{rag_context}\n\n{user_prompt}"
    if history_text:
        user_prompt = f"最近对话：\n{history_text}\n\n{user_prompt}"
    response = await llm.ainvoke(
        [
            SystemMessage(content=_build_system_prompt(risk_level, bool(rag_context))),
            HumanMessage(content=user_prompt),
        ]
    )
    content = getattr(response, "content", None)
    if isinstance(content, str) and content.strip():
        return content.strip()
    return None


def _enforce_safety(answer: str, risk_level: str) -> str:
    result = answer.strip()
    if risk_level in {"medical", "high"} and "不能替代兽医诊断" not in result:
        result = f"{result}\n\n{MEDICAL_SAFETY_TEXT}"
    if risk_level == "high" and "宠物医院" not in result and "兽医" not in result:
        result = f"{result}\n\n{HIGH_RISK_TEXT}"
    return result


def _build_references(rag_context: str | None) -> str | None:
    if not rag_context:
        return None
    return rag_context[:4000]


async def _generate_answer_node(state: QaWorkflowState) -> QaWorkflowState:
    risk_level = state.get("risk_level", "normal")
    answer = await _call_deepseek(
        state.get("question", ""),
        risk_level,
        state.get("history"),
        state.get("rag_context"),
    )
    if answer is None:
        answer = build_rule_based_qa_answer(risk_level)
    return {
        **state,
        "answer": _enforce_safety(answer, risk_level),
        "references": _build_references(state.get("rag_context")),
    }


@lru_cache(maxsize=1)
def _compile_qa_graph_without_checkpointer():
    return _build_qa_graph().compile()


def _build_qa_graph():
    from langgraph.graph import END, StateGraph

    graph = StateGraph(QaWorkflowState)
    graph.add_node("generate_answer", _generate_answer_node)
    graph.set_entry_point("generate_answer")
    graph.add_edge("generate_answer", END)
    return graph


def _build_thread_config(session_id: int | None) -> dict[str, Any] | None:
    if session_id is None:
        return None
    return {
        "configurable": {
            "thread_id": f"qa_session:{session_id}",
        }
    }


async def _run_graph_without_checkpointer(
    state: QaWorkflowState,
    session_id: int | None,
) -> QaWorkflowState:
    graph = _compile_qa_graph_without_checkpointer()
    config = _build_thread_config(session_id)
    if config is None:
        return await graph.ainvoke(state)
    return await graph.ainvoke(state, config=config)


async def _run_graph_with_postgres_checkpointer(
    state: QaWorkflowState,
    session_id: int,
) -> QaWorkflowState | None:
    settings = get_settings()
    if not settings.agent_memory_postgres_dsn:
        return None
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver
    except ImportError:
        return None

    try:
        async with AsyncPostgresSaver.from_conn_string(settings.agent_memory_postgres_dsn) as checkpointer:
            if settings.agent_memory_setup_on_start:
                await checkpointer.setup()
            graph = _build_qa_graph().compile(checkpointer=checkpointer)
            return await graph.ainvoke(state, config=_build_thread_config(session_id))
    except Exception:
        return None


async def run_qa_agent_workflow(
    *,
    question: str,
    risk_level: str,
    history: list[dict[str, str]] | None = None,
    rag_context: str | None = None,
    session_id: int | None = None,
) -> QaWorkflowState:
    state: QaWorkflowState = {
        "question": question,
        "risk_level": risk_level,
        "history": history or [],
        "rag_context": rag_context or "",
    }
    try:
        if session_id is not None:
            checkpointed_result = await _run_graph_with_postgres_checkpointer(state, session_id)
            if checkpointed_result is not None:
                return checkpointed_result
        return await _run_graph_without_checkpointer(state, session_id)
    except Exception:
        return {
            "question": question,
            "risk_level": risk_level,
            "history": history or [],
            "answer": build_rule_based_qa_answer(risk_level),
            "references": None,
        }


def _first_in_stock_sku(product: dict[str, Any]) -> dict[str, Any] | None:
    for sku in product.get("skus") or []:
        if sku.get("is_enabled", True) and int(sku.get("stock") or 0) > 0:
            return sku
    return None


def _build_guide_recommendations(
    products: list[dict[str, Any]],
    limit: int,
    rag_context: str | None,
) -> list[GuideRecommendationState]:
    recommendations: list[GuideRecommendationState] = []
    for product in products[:limit]:
        sku = _first_in_stock_sku(product)
        if sku is None:
            continue
        recommendations.append(
            {
                "product_id": int(product["id"]),
                "sku_id": int(sku["id"]),
                "rank": len(recommendations) + 1,
                "reason": "Matched the current pet profile and the user's shopping request.",
                "caution": "Check ingredients, size, and transition gradually when changing food.",
                "source": "rag_enhanced" if rag_context else "product_search",
            }
        )
    return recommendations


def _build_pet_summary_text(pet_summary: dict[str, Any] | None) -> str:
    if not pet_summary:
        return "No pet profile was selected."
    fields = [
        f"name={pet_summary.get('name')}",
        f"type={pet_summary.get('pet_type')}",
        f"breed={pet_summary.get('breed')}",
        f"weight={pet_summary.get('weight')}",
        f"allergy={pet_summary.get('allergy_notes')}",
        f"diet={pet_summary.get('diet_preference')}",
        f"product={pet_summary.get('product_preference')}",
    ]
    return "; ".join(item for item in fields if not item.endswith("=None"))


def _build_products_text(products: list[dict[str, Any]]) -> str:
    lines = []
    for product in products[:10]:
        sku = _first_in_stock_sku(product)
        sku_text = f", sku_id={sku.get('id')}" if sku else ""
        lines.append(
            f"product_id={product.get('id')}, title={product.get('title')}, "
            f"price={product.get('price')}, stock={product.get('stock')}{sku_text}"
        )
    return "\n".join(lines)


async def _call_deepseek_guide(
    question: str,
    risk_level: str,
    pet_summary: dict[str, Any] | None,
    products: list[dict[str, Any]],
    history: list[dict[str, str]] | None,
    rag_context: str | None,
) -> str | None:
    settings = get_settings()
    if settings.llm_provider != "deepseek" or not settings.llm_api_key or not products:
        return None
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_deepseek import ChatDeepSeek
    except ImportError:
        return None

    system_prompt = (
        "You are a pet mall shopping guide. Answer in concise Chinese. "
        "Only recommend products from the provided candidate list. "
        "Do not invent product IDs, SKUs, prices, stock, promotions, brands, or medical conclusions. "
        "Prices and stock are database facts. "
        "For medical, medication, prescription diet, or emergency questions, add a veterinarian safety warning."
    )
    user_prompt = (
        f"Risk level: {risk_level}\n"
        f"Pet profile: {_build_pet_summary_text(pet_summary)}\n"
        f"Candidate products:\n{_build_products_text(products)}\n"
        f"RAG context:\n{rag_context or ''}\n"
        f"Recent history:\n{_normalize_history(history)}\n"
        f"User question: {question}"
    )
    llm = ChatDeepSeek(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        temperature=settings.llm_temperature,
    )
    response = await llm.ainvoke(
        [
            SystemMessage(content=system_prompt),
            HumanMessage(content=user_prompt),
        ]
    )
    content = getattr(response, "content", None)
    if isinstance(content, str) and content.strip():
        return content.strip()
    return None


def build_rule_based_guide_answer(
    risk_level: str,
    products: list[dict[str, Any]],
    pet_summary: dict[str, Any] | None,
) -> str:
    if not products:
        answer = "No matching on-sale products are available right now. Please refine the need or try another category."
    else:
        pet_part = ""
        if pet_summary:
            pet_name = pet_summary.get("name")
            pet_type = pet_summary.get("pet_type")
            pet_part = f" for {pet_name or 'the selected pet'} ({pet_type or 'pet'})"
        titles = ", ".join(str(product.get("title")) for product in products[:3] if product.get("title"))
        answer = f"Based on the current pet profile{pet_part}, the available product candidates are: {titles}."
    if risk_level == "high":
        return f"{answer}\n\n{GUIDE_HIGH_RISK_TEXT} {GUIDE_MEDICAL_SAFETY_TEXT}"
    if risk_level == "medical":
        return f"{answer}\n\n{GUIDE_MEDICAL_SAFETY_TEXT}"
    return answer


def _enforce_guide_safety(answer: str, risk_level: str) -> str:
    result = answer.strip()
    if risk_level in {"medical", "high"} and "cannot replace a veterinarian diagnosis" not in result:
        result = f"{result}\n\n{GUIDE_MEDICAL_SAFETY_TEXT}"
    if risk_level == "high" and "offline veterinarian" not in result:
        result = f"{result}\n\n{GUIDE_HIGH_RISK_TEXT}"
    return result


async def run_guide_agent_workflow(
    *,
    question: str,
    risk_level: str,
    pet_summary: dict[str, Any] | None = None,
    products: list[dict[str, Any]] | None = None,
    rag_context: str | None = None,
    history: list[dict[str, str]] | None = None,
    session_id: int | None = None,
) -> GuideWorkflowState:
    product_candidates = products or []
    try:
        answer = await _call_deepseek_guide(
            question,
            risk_level,
            pet_summary,
            product_candidates,
            history,
            rag_context,
        )
    except Exception:
        answer = None
    if answer is None:
        answer = build_rule_based_guide_answer(risk_level, product_candidates, pet_summary)
    return {
        "question": question,
        "risk_level": risk_level,
        "history": history or [],
        "rag_context": rag_context or "",
        "pet_summary": pet_summary,
        "products": product_candidates,
        "answer": _enforce_guide_safety(answer, risk_level),
        "recommendations": _build_guide_recommendations(
            product_candidates,
            len(product_candidates),
            rag_context,
        ),
        "references": _build_references(rag_context),
    }
