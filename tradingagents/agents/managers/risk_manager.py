import time
import json


def create_risk_manager(llm, memory):
    def risk_manager_node(state) -> dict:

        company_name = state["company_of_interest"]

        history = state["risk_debate_state"]["history"]
        risk_debate_state = state["risk_debate_state"]
        market_research_report = state["market_report"]
        news_report = state["news_report"]
        fundamentals_report = state["news_report"]
        sentiment_report = state["sentiment_report"]
        trader_plan = state["investment_plan"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        prompt = f"""위험 관리 심판이자 토론 진행자로서, 세 명의 위험 분석가—공격적, 중립적, 안전/보수적—간의 토론을 평가하고 트레이더를 위한 최선의 행동 방침을 결정하는 것이 당신의 목표입니다. 당신의 결정은 명확한 추천으로 귀결되어야 합니다: 매수, 매도, 또는 보유. 모든 측면이 타당해 보일 때의 대안이 아니라 구체적인 논증으로 강력하게 뒷받침되는 경우에만 보유를 선택하세요. 명확성과 결단력을 추구하세요.

의사결정 가이드라인:
1. **핵심 논증 요약**: 각 분석가의 가장 강력한 포인트를 추출하여 맥락과의 관련성에 집중하세요.
2. **근거 제공**: 토론의 직접 인용과 반박 논리로 당신의 추천을 뒷받침하세요.
3. **트레이더 계획 개선**: 트레이더의 원래 계획 **{trader_plan}**에서 시작하여 분석가들의 통찰력을 바탕으로 조정하세요.
4. **과거 실수로부터 학습**: **{past_memory_str}**의 교훈을 사용하여 이전의 잘못된 판단을 해결하고 지금 내리는 결정을 개선하여 돈을 잃는 잘못된 매수/매도/보유 결정을 내리지 않도록 하세요.

제출물:
- 명확하고 실행 가능한 추천: 매수, 매도, 또는 보유.
- 토론과 과거 성찰에 근거한 상세한 근거.

---

**분석가 토론 히스토리:**  
{history}

---

답변은 가급적 한글로 작성해주시고, 꼭 필요한 경우에만 영어를 사용해주시기 바랍니다.
실행 가능한 통찰력과 지속적인 개선에 집중하세요. 과거 교훈을 바탕으로, 모든 관점을 비판적으로 평가하고, 각 결정이 더 나은 결과를 이끌도록 하세요."""

        response = llm.invoke(prompt)

        new_risk_debate_state = {
            "judge_decision": response.content,
            "history": risk_debate_state["history"],
            "risky_history": risk_debate_state["risky_history"],
            "safe_history": risk_debate_state["safe_history"],
            "neutral_history": risk_debate_state["neutral_history"],
            "latest_speaker": "Judge",
            "current_risky_response": risk_debate_state["current_risky_response"],
            "current_safe_response": risk_debate_state["current_safe_response"],
            "current_neutral_response": risk_debate_state["current_neutral_response"],
            "count": risk_debate_state["count"],
        }

        return {
            "risk_debate_state": new_risk_debate_state,
            "final_trade_decision": response.content,
        }

    return risk_manager_node
