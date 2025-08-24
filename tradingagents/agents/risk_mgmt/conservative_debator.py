from langchain_core.messages import AIMessage
import time
import json


def create_safe_debator(llm):
    def safe_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        safe_history = risk_debate_state.get("safe_history", "")

        current_risky_response = risk_debate_state.get("current_risky_response", "")
        current_neutral_response = risk_debate_state.get("current_neutral_response", "")

        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]
        ben_graham_report = state["ben_graham_report"]
        warren_buffett_report = state["warren_buffett_report"]

        trader_decision = state["trader_investment_plan"]

        prompt = f"""안전/보수적 리스크 분석가로서 당신의 주요 목표는 자산을 보호하고, 변동성을 최소화하며, 안정적이고 신뢰할 수 있는 성장을 보장하는 것입니다. 당신은 안정성, 보안, 리스크 완화에 우선순위를 두며, 잠재적 손실, 경기 침체, 시장 변동성을 신중하게 평가합니다. 트레이더의 결정이나 계획을 평가할 때, 고위험 요소를 비판적으로 검토하고, 해당 결정이 회사에 과도한 리스크를 초래할 수 있는 부분과 더 신중한 대안이 장기적인 이익을 보장할 수 있는 부분을 지적하세요. 다음은 트레이더의 결정입니다:

{trader_decision}

당신의 임무는 위험 성향 및 중립 성향 분석가의 주장에 적극적으로 반박하며, 그들의 관점이 잠재적 위협을 간과하거나 지속 가능성을 우선시하지 못하는 부분을 강조하는 것입니다. 다음의 데이터 소스를 활용하여 트레이더의 결정을 저위험 관점에서 조정해야 하는 설득력 있는 근거를 제시하며, 그들의 주장에 직접적으로 응답하세요:

시장 조사 보고서: {market_research_report}
소셜 미디어 심리 보고서: {sentiment_report}
최신 세계 정세 보고서: {news_report}
기업 펀더멘털 보고서: {fundamentals_report}
벤자민 그레이엄 보고서: {ben_graham_report}
워렌 버핏 보고서: {warren_buffett_report}

현재 대화 내역: {history} 위험 성향 분석가의 마지막 답변: {current_risky_response} 중립 성향 분석가의 마지막 답변: {current_neutral_response}. 만약 다른 관점의 답변이 없다면, 내용을 지어내지 말고 당신의 의견만 제시하세요.

그들의 낙관론에 의문을 제기하고, 그들이 간과했을 수 있는 잠재적 단점에 초점을 맞추세요. 각 반론에 대응하여 보수적 관점이 회사 자산을 지키는 가장 안전한 길임을 보여주세요. 논쟁과 비판에 집중하여 저위험 전략의 강점을 부각시키세요. 특별한 형식 없이 대화하듯 자연스럽게 답변하세요.
답변은 가급적 한글로 작성해주시고, 꼭 필요한 경우에만 영어를 사용해주시기 바랍니다.
"""

        response = llm.invoke(prompt)

        argument = f"Safe Analyst: {response.content}"

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "risky_history": risk_debate_state.get("risky_history", ""),
            "safe_history": safe_history + "\n" + argument,
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "latest_speaker": "Safe",
            "current_risky_response": risk_debate_state.get(
                "current_risky_response", ""
            ),
            "current_safe_response": argument,
            "current_neutral_response": risk_debate_state.get(
                "current_neutral_response", ""
            ),
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return safe_node
