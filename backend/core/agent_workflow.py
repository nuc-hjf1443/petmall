from functools import lru_cache
from typing import Any, TypedDict

from settings.config import get_settings


MEDICAL_SAFETY_TEXT = "以下内容仅供参考，不能替代兽医诊断。"
HIGH_RISK_TEXT = "你描述的情况可能存在急症风险，请尽快联系线下兽医或宠物医院。"


class QaWorkflowState(TypedDict, total=False):
    question: str
    risk_level: str
    history: list[dict[str, str]]
    answer: str
    references: str | None


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


def _build_system_prompt(risk_level: str) -> str:
    return (
        "你是宠物综合服务平台的养宠知识问答助手。"
        "请用中文回答，表达清晰、谨慎、可执行。"
        "当前 RAG 检索尚未接入，不能声称引用了私人知识库、平台知识库或宠物档案。"
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


async def _call_deepseek(question: str, risk_level: str, history: list[dict[str, str]] | None) -> str | None:
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
    if history_text:
        user_prompt = f"最近对话：\n{history_text}\n\n{user_prompt}"
    response = await llm.ainvoke(
        [
            SystemMessage(content=_build_system_prompt(risk_level)),
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


async def _generate_answer_node(state: QaWorkflowState) -> QaWorkflowState:
    risk_level = state.get("risk_level", "normal")
    answer = await _call_deepseek(
        state.get("question", ""),
        risk_level,
        state.get("history"),
    )
    if answer is None:
        answer = build_rule_based_qa_answer(risk_level)
    return {
        **state,
        "answer": _enforce_safety(answer, risk_level),
        "references": None,
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
    session_id: int | None = None,
) -> QaWorkflowState:
    state: QaWorkflowState = {
        "question": question,
        "risk_level": risk_level,
        "history": history or [],
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
