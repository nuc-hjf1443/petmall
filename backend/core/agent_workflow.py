import logging
from functools import lru_cache
import logging
from typing import Any, TypedDict

from settings.config import get_settings


logger = logging.getLogger(__name__)

MEDICAL_SAFETY_TEXT = "小提醒：以下内容只适合做日常参考，不能替代兽医诊断。"
HIGH_RISK_TEXT = "你描述的情况可能有急症风险，请尽快联系线下兽医或宠物医院。"


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
    source_detail: str | None
    score: float | None
    matched_pet_fields: list[str]


class GuideWorkflowState(TypedDict, total=False):
    question: str
    session_id: int | None
    risk_level: str
    history: list[dict[str, str]]
    history_summary: str
    rag_context: str
    pet_summary: dict[str, Any] | None
    products: list[dict[str, Any]]
    guide_state: dict[str, Any]
    next_questions: list[dict[str, Any]]
    requires_user_confirmation: bool
    answer: str
    recommendations: list[GuideRecommendationState]
    references: str | None


GUIDE_MEDICAL_SAFETY_TEXT = "涉及医疗、用药、处方粮或急症内容时，以下建议仅供参考，不能替代兽医诊断。"
GUIDE_HIGH_RISK_TEXT = "你描述的情况可能存在急症风险，请尽快联系线下兽医或宠物医院。"


def build_rule_based_qa_answer(risk_level: str) -> str:
    base = "我先按你提供的信息，给一份温和版的日常养宠建议。"
    if risk_level == "high":
        return f"{base}\n\n{HIGH_RISK_TEXT}\n\n{MEDICAL_SAFETY_TEXT}"
    if risk_level == "medical":
        return (
            f"{base}\n\n{MEDICAL_SAFETY_TEXT}\n\n"
            "建议：不要自行使用处方药或调整剂量，先记录症状、饮食和精神状态，再给兽医判断。"
        )
    return (
        f"{base}\n\n"
        "建议：\n"
        "1. 先观察宝贝的精神、食欲、排便和饮水变化。\n"
        "2. 如果症状持续或加重，及时联系兽医会更安心。\n"
        "3. 你也可以补充年龄、品种、体重和最近变化，我再帮你细化。"
    )


def _build_system_prompt(risk_level: str, has_rag_context: bool) -> str:
    rag_instruction = (
        "已提供 RAG 检索摘要时，可以基于摘要回答，但不能夸大成完整诊断。"
        if has_rag_context
        else "当前没有可用 RAG 检索摘要，不能声称引用了私人知识库、平台知识库或宠物档案。"
    )
    return (
        "你是宠物综合服务平台的养宠知识问答助手。"
        "请用中文回答，语气要温柔、生动、可亲近，像耐心陪用户一起照顾宠物的小助手。"
        "可以轻微可爱，但不要过度卖萌；医疗、支付、订单等严肃场景要稳重。"
        "输出格式只使用普通段落和 1. 2. 3. 编号，不使用 Markdown 标题、表格、分割线、粗体、代码块或大量 emoji。"
        "优先先给结论，再给简短建议。每次回答尽量控制在 4 段以内。"
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


def get_agent_memory_status() -> dict[str, Any]:
    settings = get_settings()
    configured = bool(settings.agent_memory_postgres_dsn)
    try:
        from langgraph.checkpoint.postgres.aio import AsyncPostgresSaver  # noqa: F401

        dependency_available = True
    except ImportError:
        dependency_available = False
    return {
        "provider": "postgres",
        "configured": configured,
        "enabled": configured and dependency_available,
        "dependency_available": dependency_available,
        "setup_on_start": settings.agent_memory_setup_on_start,
        "thread_id_pattern": "qa_session:{session_id}",
    }


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
        logger.warning("LangGraph postgres checkpointer dependency is not installed")
        return None

    try:
        async with AsyncPostgresSaver.from_conn_string(settings.agent_memory_postgres_dsn) as checkpointer:
            if settings.agent_memory_setup_on_start:
                await checkpointer.setup()
            graph = _build_qa_graph().compile(checkpointer=checkpointer)
            return await graph.ainvoke(state, config=_build_thread_config(session_id))
    except Exception as exc:
        logger.warning("LangGraph postgres checkpoint failed for qa session %s: %s", session_id, exc)
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


def _guide_slots(guide_state: dict[str, Any] | None) -> dict[str, Any]:
    if not isinstance(guide_state, dict):
        return {}
    slots = guide_state.get("slots")
    return slots if isinstance(slots, dict) else {}


def _guide_missing_slots(slots: dict[str, Any]) -> list[str]:
    missing: list[str] = []
    if not slots.get("pet_id") and not slots.get("pet_type"):
        missing.append("pet")
    if not slots.get("category"):
        missing.append("category")
    if (
        not slots.get("budget")
        and not slots.get("preferences")
        and not (slots.get("category") and (slots.get("pet_id") or slots.get("pet_type")))
    ):
        missing.append("budget_or_preference")
    return missing


def _build_guide_next_questions(missing_slots: list[str]) -> list[dict[str, Any]]:
    question_map = {
        "pet": {
            "key": "pet",
            "question": "\u8bf7\u5148\u544a\u8bc9\u6211\u8981\u7ed9\u54ea\u4e2a\u5ba0\u7269\u4e70\uff1f",
            "options": [
                {"label": "\u72d7\u72d7", "value": "\u7ed9\u72d7\u72d7\u4e70"},
                {"label": "\u732b\u54aa", "value": "\u7ed9\u732b\u54aa\u4e70"},
            ],
        },
        "category": {
            "key": "category",
            "question": "\u8fd9\u6b21\u4e3b\u8981\u60f3\u4e70\u54ea\u7c7b\u5546\u54c1\uff1f",
            "options": [
                {"label": "\u4e3b\u7cae", "value": "\u4e3b\u7cae"},
                {"label": "\u96f6\u98df\u51bb\u5e72", "value": "\u96f6\u98df\u51bb\u5e72"},
                {"label": "\u73a9\u5177", "value": "\u73a9\u5177"},
                {"label": "\u6d17\u62a4\u7528\u54c1", "value": "\u6d17\u62a4\u7528\u54c1"},
            ],
        },
        "budget_or_preference": {
            "key": "budget_or_preference",
            "question": "\u6709\u9884\u7b97\u6216\u504f\u597d\u5417\uff1f",
            "options": [
                {"label": "100 \u5143\u4ee5\u5185", "value": "\u9884\u7b97 100 \u5143\u4ee5\u5185"},
                {"label": "300 \u5143\u4ee5\u5185", "value": "\u9884\u7b97 300 \u5143\u4ee5\u5185"},
                {"label": "\u4f4e\u654f", "value": "\u504f\u597d\u4f4e\u654f"},
                {"label": "\u8010\u54ac", "value": "\u504f\u597d\u8010\u54ac"},
            ],
        },
    }
    return [question_map[key] for key in missing_slots if key in question_map][:2]


def _build_guide_clarification_answer(next_questions: list[dict[str, Any]]) -> str:
    if not next_questions:
        return "\u6211\u9700\u8981\u518d\u786e\u8ba4\u4e00\u70b9\u9700\u6c42\uff0c\u7136\u540e\u518d\u4ece\u771f\u5b9e\u5728\u552e\u5546\u54c1\u91cc\u7b5b\u9009\u3002"
    lines = ["\u4e3a\u4e86\u907f\u514d\u4e71\u63a8\u8350\uff0c\u6211\u9700\u8981\u5148\u786e\u8ba4\u4e00\u4e0b\u5173\u952e\u9700\u6c42\uff1a"]
    for index, item in enumerate(next_questions, start=1):
        lines.append(f"{index}. {item.get('question')}")
    return "\n".join(lines)


async def _parse_guide_request_node(state: GuideWorkflowState) -> GuideWorkflowState:
    guide_state = dict(state.get("guide_state") or {})
    slots = dict(_guide_slots(guide_state))
    if state.get("pet_summary"):
        pet_summary = state["pet_summary"] or {}
        if pet_summary.get("id"):
            slots["pet_id"] = pet_summary.get("id")
        if pet_summary.get("name"):
            slots["pet_name"] = pet_summary.get("name")
        if pet_summary.get("pet_type"):
            slots["pet_type"] = pet_summary.get("pet_type")

    missing_slots = _guide_missing_slots(slots)
    guide_state["slots"] = slots
    guide_state["missing_slots"] = missing_slots
    guide_state["stage"] = "clarifying" if missing_slots else "recommending"
    return {**state, "guide_state": guide_state}


def _route_guide_request(state: GuideWorkflowState) -> str:
    return "ask_clarification" if state.get("guide_state", {}).get("missing_slots") else "generate_answer"


async def _ask_guide_clarification_node(state: GuideWorkflowState) -> GuideWorkflowState:
    guide_state = dict(state.get("guide_state") or {})
    missing_slots = list(guide_state.get("missing_slots") or [])
    next_questions = _build_guide_next_questions(missing_slots)
    risk_level = state.get("risk_level", "normal")
    answer = _build_guide_clarification_answer(next_questions)
    return {
        **state,
        "answer": _enforce_guide_safety(answer, risk_level),
        "recommendations": [],
        "references": None,
        "next_questions": next_questions,
        "requires_user_confirmation": True,
    }


async def _generate_guide_answer_node(state: GuideWorkflowState) -> GuideWorkflowState:
    product_candidates = state.get("products") or []
    risk_level = state.get("risk_level", "normal")
    try:
        answer = await _call_deepseek_guide(
            state.get("question", ""),
            risk_level,
            state.get("pet_summary"),
            product_candidates,
            state.get("history"),
            state.get("history_summary"),
            state.get("rag_context"),
        )
    except Exception as exc:
        logger.exception(
            "guide_agent_llm_failed",
            extra={
                "stage": "llm",
                "session_id": state.get("session_id"),
                "exception_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        answer = None
    if answer is None:
        answer = build_rule_based_guide_answer(risk_level, product_candidates, state.get("pet_summary"))
    return {
        **state,
        "answer": _enforce_guide_safety(answer, risk_level),
        "recommendations": _build_guide_recommendations(
            product_candidates,
            len(product_candidates),
            state.get("rag_context"),
            state.get("pet_summary"),
        ),
        "references": _build_references(state.get("rag_context")),
        "next_questions": [],
        "requires_user_confirmation": False,
    }


def _build_guide_graph():
    from langgraph.graph import END, StateGraph

    graph = StateGraph(GuideWorkflowState)
    graph.add_node("parse_request", _parse_guide_request_node)
    graph.add_node("ask_clarification", _ask_guide_clarification_node)
    graph.add_node("generate_answer", _generate_guide_answer_node)
    graph.set_entry_point("parse_request")
    graph.add_conditional_edges(
        "parse_request",
        _route_guide_request,
        {
            "ask_clarification": "ask_clarification",
            "generate_answer": "generate_answer",
        },
    )
    graph.add_edge("ask_clarification", END)
    graph.add_edge("generate_answer", END)
    return graph


@lru_cache(maxsize=1)
def _compile_guide_graph_without_checkpointer():
    return _build_guide_graph().compile()


def _first_in_stock_sku(product: dict[str, Any]) -> dict[str, Any] | None:
    for sku in product.get("skus") or []:
        if sku.get("is_enabled", True) and int(sku.get("stock") or 0) > 0:
            return sku
    return None


def _build_guide_recommendations(
    products: list[dict[str, Any]],
    limit: int,
    rag_context: str | None,
    pet_summary: dict[str, Any] | None = None,
) -> list[GuideRecommendationState]:
    recommendations: list[GuideRecommendationState] = []
    for product in products[:limit]:
        sku = _first_in_stock_sku(product)
        if sku is None:
            continue
        matched_pet_fields = _matched_pet_fields(product, pet_summary)
        source = "rag_enhanced" if rag_context else "product_search"
        recommendations.append(
            {
                "product_id": int(product["id"]),
                "sku_id": int(sku["id"]),
                "rank": len(recommendations) + 1,
                "reason": _build_guide_recommendation_reason(product, matched_pet_fields),
                "caution": "下单前请确认规格、成分和适用对象；换粮时建议逐步过渡。",
                "source": source,
                "source_detail": "rag_enhanced" if rag_context else "rule_based_ranked",
                "score": 0.75 if matched_pet_fields else 0.6,
                "matched_pet_fields": matched_pet_fields,
            }
        )
    return recommendations


def _build_guide_recommendation_reason(product: dict[str, Any], matched_pet_fields: list[str]) -> str:
    points = []
    if "pet_type" in matched_pet_fields:
        points.append("适配当前宠物类型")
    elif product.get("applicable_pet_type"):
        points.append("适用对象明确")
    else:
        points.append("匹配本次导购关键词")
    if any(field in matched_pet_fields for field in ("allergy_notes", "diet_preference", "product_preference")):
        points.append("和宠物档案里的偏好或注意事项有关")
    else:
        points.append("可作为本次需求的候选款")
    points.append("卡片中可直接核对价格、库存和规格")
    return "；".join(points[:3]) + "。"


def _matched_pet_fields(product: dict[str, Any], pet_summary: dict[str, Any] | None) -> list[str]:
    if not pet_summary:
        return []
    matched: list[str] = []
    product_pet_type = product.get("applicable_pet_type")
    if pet_summary.get("pet_type") and product_pet_type == pet_summary.get("pet_type"):
        matched.append("pet_type")
    searchable_text = f"{product.get('title') or ''} {product.get('description') or ''}".lower()
    field_keywords = {
        "allergy_notes": ["低敏", "敏感", "allergy", "sensitive"],
        "diet_preference": ["粮", "food", "diet", "鸡肉", "牛肉", "鱼"],
        "product_preference": ["玩具", "牵引", "猫砂", "用品"],
    }
    for field, keywords in field_keywords.items():
        value = str(pet_summary.get(field) or "").strip()
        if value and any(keyword.lower() in searchable_text or keyword.lower() in value.lower() for keyword in keywords):
            matched.append(field)
    return matched


def _build_pet_summary_text(pet_summary: dict[str, Any] | None) -> str:
    if not pet_summary:
        return "未选择宠物档案。"
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


def build_rule_based_guide_history_summary(
    existing_summary: str | None,
    history: list[dict[str, str]],
    *,
    max_chars: int = 1200,
) -> str:
    parts = []
    if existing_summary:
        parts.append(f"既有摘要：{existing_summary.strip()}")
    if history:
        lines = []
        for item in history[-12:]:
            role = item.get("role", "unknown")
            content = str(item.get("content", "")).strip().replace("\n", " ")
            if content:
                lines.append(f"{role}: {content[:180]}")
        if lines:
            parts.append("历史要点：" + "；".join(lines))
    summary = "\n".join(parts).strip()
    return summary[:max_chars]


async def summarize_guide_history(
    *,
    existing_summary: str | None,
    history: list[dict[str, str]],
    max_chars: int = 1200,
) -> str:
    settings = get_settings()
    if settings.llm_provider != "deepseek" or not settings.llm_api_key:
        return build_rule_based_guide_history_summary(existing_summary, history, max_chars=max_chars)
    try:
        from langchain_core.messages import HumanMessage, SystemMessage
        from langchain_deepseek import ChatDeepSeek
    except ImportError:
        return build_rule_based_guide_history_summary(existing_summary, history, max_chars=max_chars)

    llm = ChatDeepSeek(
        model=settings.llm_model,
        api_key=settings.llm_api_key,
        temperature=0,
    )
    history_text = _normalize_history(history)
    response = await llm.ainvoke(
        [
            SystemMessage(content="你是宠物导购会话摘要器。请保留用户需求、宠物信息、预算、偏好和已推荐方向，输出简短中文摘要，不要编造。"),
            HumanMessage(content=f"既有摘要：{existing_summary or ''}\n\n需要合并的历史：\n{history_text}"),
        ]
    )
    content = getattr(response, "content", None)
    if isinstance(content, str) and content.strip():
        return content.strip()[:max_chars]
    return build_rule_based_guide_history_summary(existing_summary, history, max_chars=max_chars)


async def _call_deepseek_guide(
    question: str,
    risk_level: str,
    pet_summary: dict[str, Any] | None,
    products: list[dict[str, Any]],
    history: list[dict[str, str]] | None,
    history_summary: str | None,
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
        "You are a warm but concise pet mall shopping guide. Answer in Chinese with 2-4 short sentences. "
        "Only recommend products from the provided candidate list. "
        "Do not invent product IDs, SKUs, prices, stock, promotions, brands, or medical conclusions. "
        "Do not show raw product_id, sku_id, price, or stock values in the chat answer; product facts are rendered by cards. "
        "First summarize why these products fit, then tell the user to check the product cards for price, stock, and specs. "
        "For medical, medication, prescription diet, or emergency questions, add a veterinarian safety warning."
    )
    user_prompt = (
        f"Risk level: {risk_level}\n"
        f"Pet profile: {_build_pet_summary_text(pet_summary)}\n"
        f"Candidate products:\n{_build_products_text(products)}\n"
        f"RAG context:\n{rag_context or ''}\n"
        f"Conversation summary:\n{history_summary or ''}\n"
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
        answer = "我暂时没有找到完全匹配的在售商品。你可以换一个品类，或者补充宠物类型、预算、口味/材质偏好后再试。"
    else:
        pet_part = ""
        if pet_summary:
            pet_name = pet_summary.get("name")
            pet_type = pet_summary.get("pet_type")
            pet_part = f"，也参考了{pet_name or '所选宠物'}（{pet_type or '宠物'}）的档案"
        titles = ", ".join(str(product.get("title")) for product in products[:3] if product.get("title"))
        answer = (
            f"我先从当前真实在售商品里{pet_part}筛了一轮，下面这些更贴近本次需求：{titles}。"
            "你可以重点看商品卡片里的价格、库存和规格；如果有过敏或肠胃敏感，下单前再核对一下配方。"
        )
    if risk_level == "high":
        return f"{answer}\n\n{GUIDE_HIGH_RISK_TEXT} {GUIDE_MEDICAL_SAFETY_TEXT}"
    if risk_level == "medical":
        return f"{answer}\n\n{GUIDE_MEDICAL_SAFETY_TEXT}"
    return answer


def _enforce_guide_safety(answer: str, risk_level: str) -> str:
    result = answer.strip()
    if risk_level in {"medical", "high"} and "不能替代兽医诊断" not in result:
        result = f"{result}\n\n{GUIDE_MEDICAL_SAFETY_TEXT}"
    if risk_level == "high" and "宠物医院" not in result and "兽医" not in result:
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
    history_summary: str | None = None,
    guide_state: dict[str, Any] | None = None,
    session_id: int | None = None,
) -> GuideWorkflowState:
    product_candidates = products or []
    state: GuideWorkflowState = {
        "question": question,
        "session_id": session_id,
        "risk_level": risk_level,
        "history": history or [],
        "history_summary": history_summary or "",
        "rag_context": rag_context or "",
        "pet_summary": pet_summary,
        "products": product_candidates,
        "guide_state": guide_state or {},
    }
    try:
        graph = _compile_guide_graph_without_checkpointer()
        return await graph.ainvoke(state)
    except Exception as exc:
        logger.exception(
            "guide_agent_workflow_failed",
            extra={
                "stage": "workflow",
                "session_id": session_id,
                "exception_type": type(exc).__name__,
                "error": str(exc),
            },
        )
        answer = build_rule_based_guide_answer(risk_level, product_candidates, pet_summary)
        return {
            **state,
            "answer": _enforce_guide_safety(answer, risk_level),
            "recommendations": _build_guide_recommendations(
                product_candidates,
                len(product_candidates),
                rag_context,
                pet_summary,
            ),
            "references": _build_references(rag_context),
            "next_questions": [],
            "requires_user_confirmation": False,
        }
