import time
import json


def create_neutral_debator(llm):
    def neutral_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        neutral_history = risk_debate_state.get("neutral_history", "")

        current_risky_response = risk_debate_state.get("current_risky_response", "")
        current_safe_response = risk_debate_state.get("current_safe_response", "")

        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        trader_decision = state["trader_investment_plan"]

        prompt = f"""당신은 중립적 위험 분석가(Neutral Risk Analyst)입니다. 당신의 역할은 트레이더의 결정이나 계획에 대해 잠재적 이익과 위험을 모두 균형 있게 평가하고, 균형 잡힌 시각을 제공하는 것입니다. 시장의 전반적 트렌드, 경제적 변화 가능성, 분산 투자 전략 등을 고려하여 장점과 단점을 모두 분석하는 데 중점을 두세요.
        
트레이더의 결정은 다음과 같습니다:

{trader_decision}

당신의 임무는 공격적(High-Risk) 및 보수적(Safe) 분석가의 관점을 모두 비판적으로 검토하고, 각 관점이 지나치게 낙관적이거나 지나치게 조심스러운 부분을 지적하는 것입니다. 아래의 데이터 소스에서 얻은 인사이트를 활용하여 트레이더의 결정을 보다 중립적이고 지속 가능한 전략으로 조정할 수 있도록 하세요.

시장 조사 보고서: {market_research_report}
소셜 미디어 감정 보고서: {sentiment_report}
최신 세계 동향 뉴스: {news_report}
회사 펀더멘털 보고서: {fundamentals_report}
현재 대화 히스토리: {history}
마지막 공격적 분석가의 응답: {current_risky_response}
마지막 보수적 분석가의 응답: {current_safe_response}
만약 다른 관점의 응답이 없다면, 내용을 지어내지 말고 본인의 의견만 제시하세요.

양측의 논리를 비판적으로 분석하며, 공격적/보수적 논거의 약점을 짚고, 보다 균형 잡힌 접근법을 옹호하세요. 각 관점의 주장에 반박하며, 중간 위험 전략이 성장 가능성과 극단적 변동성 방지라는 두 가지 장점을 모두 제공할 수 있음을 보여주세요. 단순히 데이터를 나열하지 말고, 토론에 집중하여 균형 잡힌 시각이 가장 신뢰할 만한 결과로 이어질 수 있음을 설득력 있게 전달하세요. 특별한 형식 없이 대화체로 출력하세요.
답변은 가급적 한글로 작성해주시고, 꼭 필요한 경우에만 영어를 사용해주시기 바랍니다.
"""

        response = llm.invoke(prompt)

        argument = f"Neutral Analyst: {response.content}"

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "risky_history": risk_debate_state.get("risky_history", ""),
            "safe_history": risk_debate_state.get("safe_history", ""),
            "neutral_history": neutral_history + "\n" + argument,
            "latest_speaker": "Neutral",
            "current_risky_response": risk_debate_state.get(
                "current_risky_response", ""
            ),
            "current_safe_response": risk_debate_state.get("current_safe_response", ""),
            "current_neutral_response": argument,
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return neutral_node
