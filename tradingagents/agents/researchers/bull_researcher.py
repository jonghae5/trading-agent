from langchain_core.messages import AIMessage
import time
import json


def create_bull_researcher(llm, memory):
    def bull_node(state) -> dict:
        investment_debate_state = state["investment_debate_state"]
        history = investment_debate_state.get("history", "")
        bull_history = investment_debate_state.get("bull_history", "")

        current_response = investment_debate_state.get("current_response", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        prompt = f"""당신은 주식 투자를 옹호하는 강세 분석가입니다. 성장 잠재력, 경쟁 우위, 긍정적 시장 지표를 강조하는 강력하고 증거 기반의 논증을 구축하는 것이 당신의 임무입니다. 제공된 연구와 데이터를 활용하여 우려사항을 해결하고 약세 논증에 효과적으로 반박하세요.

집중해야 할 핵심 포인트:
- 성장 잠재력: 회사의 시장 기회, 매출 전망, 확장성을 강조하세요.
- 경쟁 우위: 독특한 제품, 강력한 브랜딩, 지배적 시장 지위와 같은 요소들을 강조하세요.
- 긍정적 지표: 재무 건전성, 산업 트렌드, 최근 긍정적 뉴스를 증거로 사용하세요.
- 약세 반박: 구체적 데이터와 건전한 논리로 약세 논증을 비판적으로 분석하고, 우려사항을 철저히 다루며 강세 관점이 더 강력한 근거를 가지는 이유를 보여주세요.
- 참여: 약세 분석가의 포인트에 직접 관여하고 단순히 데이터를 나열하는 것이 아니라 효과적으로 토론하는 대화형 스타일로 논증을 제시하세요.

사용 가능한 자료:
시장 조사 보고서: {market_research_report}
소셜 미디어 감정 보고서: {sentiment_report}
최신 세계 동향 뉴스: {news_report}
회사 펀더멘털 보고서: {fundamentals_report}
토론의 대화 히스토리: {history}
마지막 약세 논증: {current_response}
유사 상황의 성찰과 교훈: {past_memory_str}
이 정보를 사용하여 설득력 있는 강세 논증을 전달하고, 약세의 우려를 반박하며, 강세 포지션의 강점을 보여주는 역동적인 토론에 참여하세요. 또한 과거의 성찰을 다루고 과거의 교훈과 실수로부터 학습해야 합니다.
답변은 가급적 한글로 작성해주시고, 꼭 필요한 경우에만 영어를 사용해주시기 바랍니다.
"""

        response = llm.invoke(prompt)

        argument = f"Bull Analyst: {response.content}"

        new_investment_debate_state = {
            "history": history + "\n" + argument,
            "bull_history": bull_history + "\n" + argument,
            "bear_history": investment_debate_state.get("bear_history", ""),
            "current_response": argument,
            "count": investment_debate_state["count"] + 1,
        }

        return {"investment_debate_state": new_investment_debate_state}

    return bull_node
