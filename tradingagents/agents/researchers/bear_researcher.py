from langchain_core.messages import AIMessage
import time
import json


def create_bear_researcher(llm, memory):
    def bear_node(state) -> dict:
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bear_history = investment_debate_state.get("bear_history", "")

        current_response = investment_debate_state.get("current_response", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]
        ben_graham_report = state["ben_graham_report"]
        warren_buffett_report = state["warren_buffett_report"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}\n\n{ben_graham_report}\n\n{warren_buffett_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        prompt = f"""당신은 주식 투자에 반대하는 논증을 펼치는 약세 분석가입니다. 당신의 목표는 위험, 도전, 부정적 지표를 강조하는 합리적인 논증을 제시하는 것입니다. 제공된 연구와 데이터를 활용하여 잠재적 하락 요인을 강조하고 강세 논증에 효과적으로 반박하세요.

집중해야 할 핵심 포인트:

- 위험과 도전: 시장 포화, 재무 불안정, 거시경제 위협과 같이 주식 성과를 저해할 수 있는 요인들을 강조하세요.
- 경쟁 약점: 더 약한 시장 지위, 혁신 저하, 경쟁자들의 위협과 같은 취약점을 강조하세요.
- 부정적 지표: 재무 데이터, 시장 트렌드, 최근 부정적 뉴스의 증거를 사용하여 당신의 지위를 뒷받침하세요.
- 강세 반박: 구체적 데이터와 건전한 논리로 강세 논증을 비판적으로 분석하고, 약점이나 지나치게 낙관적인 가정을 드러내세요.
- 참여: 강세 분석가의 포인트에 직접 관여하고 단순히 사실을 나열하는 것이 아니라 효과적으로 토론하는 대화형 스타일로 논증을 제시하세요.

사용 가능한 자료:

시장 조사 보고서: {market_research_report}
소셜 미디어 감정 보고서: {sentiment_report}
최신 세계 동향 뉴스: {news_report}
회사 펀더멘털 보고서: {fundamentals_report}
벤자민 그레이엄 보고서: {ben_graham_report}
워렌 버핏 보고서: {warren_buffett_report}
토론의 대화 히스토리: {history}
마지막 강세 논증: {current_response}
유사 상황의 성찰과 교훈: {past_memory_str}
이 정보를 사용하여 설득력 있는 약세 논증을 전달하고, 강세의 주장을 반박하며, 주식 투자의 위험과 약점을 보여주는 역동적인 토론에 참여하세요. 또한 성찰을 다루고 과거의 교훈과 실수로부터 학습해야 합니다.
답변은 가급적 한글로 작성해주시고, 꼭 필요한 경우에만 영어를 사용해주시기 바랍니다.
"""

        response = llm.invoke(prompt)

        argument = f"Bear Analyst: {response.content}"

        new_investment_debate_state = {
            "history": history + "\n" + argument,
            "bear_history": bear_history + "\n" + argument,
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": argument,
            "count": investment_debate_state["count"] + 1,
        }

        return {"investment_debate_state": new_investment_debate_state}

    return bear_node
