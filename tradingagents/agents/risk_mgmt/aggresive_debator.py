import time
import json


def create_risky_debator(llm):
    def risky_node(state) -> dict:
        risk_debate_state = state["risk_debate_state"]
        history = risk_debate_state.get("history", "")
        risky_history = risk_debate_state.get("risky_history", "")

        current_safe_response = risk_debate_state.get("current_safe_response", "")
        current_neutral_response = risk_debate_state.get("current_neutral_response", "")

        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        trader_decision = state["trader_investment_plan"]

        prompt = f"""당신은 공격적(High-Risk) 리스크 분석가입니다. 당신의 역할은 높은 수익과 높은 위험이 수반되는 기회를 적극적으로 옹호하며, 대담한 전략과 경쟁 우위를 강조하는 것입니다. 트레이더의 결정이나 계획을 평가할 때, 잠재적 상승 여력, 성장 가능성, 혁신적 이점에 집중하세요. 위험이 높더라도 그 이점을 부각시키는 데 중점을 두세요. 제공된 시장 데이터와 심리 분석을 활용하여 자신의 주장을 강화하고, 반대 관점에 적극적으로 도전하세요. 특히, 보수적(Safe) 및 중립적(Neutral) 분석가가 제시한 각 논점에 직접적으로 응답하며, 데이터 기반 반박과 설득력 있는 논리를 통해 그들의 신중함이 중요한 기회를 놓치거나 지나치게 보수적일 수 있음을 강조하세요. 다음은 트레이더의 결정입니다:

{trader_decision}

당신의 임무는 트레이더의 결정을 옹호하는 강력한 논거를 제시하는 것입니다. 보수적 및 중립적 관점에 대해 질문하고 비판하며, 왜 당신의 고수익 관점이 최선의 길인지 설득력 있게 보여주세요. 아래의 자료에서 얻은 인사이트를 논거에 적극적으로 반영하세요:

시장 조사 보고서: {market_research_report}
소셜 미디어 심리 보고서: {sentiment_report}
최신 세계 동향 뉴스: {news_report}
회사 펀더멘털 보고서: {fundamentals_report}
현재 대화 히스토리: {history}
마지막 보수적 분석가의 주장: {current_safe_response}
마지막 중립적 분석가의 주장: {current_neutral_response}
만약 다른 관점의 응답이 없다면, 내용을 지어내지 말고 본인의 의견만 제시하세요.

제기된 구체적 우려에 적극적으로 대응하고, 그들의 논리적 약점을 반박하며, 위험 감수의 이점이 시장 평균을 능가할 수 있음을 주장하세요. 단순히 데이터를 나열하지 말고, 토론과 설득에 집중하세요. 각 반론을 적극적으로 반박하며, 왜 고위험 전략이 최적의 선택인지 강조하세요. 특별한 형식 없이 대화체로 출력하세요.
답변은 가급적 한글로 작성해주시고, 꼭 필요한 경우에만 영어를 사용해주시기 바랍니다.
"""

        response = llm.invoke(prompt)

        argument = f"Risky Analyst: {response.content}"

        new_risk_debate_state = {
            "history": history + "\n" + argument,
            "risky_history": risky_history + "\n" + argument,
            "safe_history": risk_debate_state.get("safe_history", ""),
            "neutral_history": risk_debate_state.get("neutral_history", ""),
            "latest_speaker": "Risky",
            "current_risky_response": argument,
            "current_safe_response": risk_debate_state.get("current_safe_response", ""),
            "current_neutral_response": risk_debate_state.get(
                "current_neutral_response", ""
            ),
            "count": risk_debate_state["count"] + 1,
        }

        return {"risk_debate_state": new_risk_debate_state}

    return risky_node
