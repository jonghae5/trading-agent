import time
import json


def create_research_manager(llm, memory):
    def research_manager_node(state) -> dict:
        history = state["investment_debate_state"].get("history", "")
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        investment_debate_state = state["investment_debate_state"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        for i, rec in enumerate(past_memories, 1):
            past_memory_str += rec["recommendation"] + "\n\n"

        prompt = f"""포트폴리오 매니저이자 토론 진행자로서, 이번 토론을 비판적으로 평가하고 명확한 결정을 내리는 것이 당신의 역할입니다: 하락 분석가, 상승 분석가 중 한 쪽에 동조하거나, 제시된 논증에 기반하여 강력하게 뒷받침되는 경우에만 보유를 선택하세요.

가장 설득력 있는 증거나 논리에 집중하여, 양측의 핵심 포인트를 간결하게 요약하십시오. 당신의 추천(매수, 매도, 또는 보유)은 명확하고 실행 가능해야 합니다. 양측 모두 타당한 포인트가 있다고 해서 단순히 보유를 기본 선택으로 삼지 마시고, 토론에서 가장 강력한 논증에 근거하여 입장을 정하십시오.

또한 트레이더를 위한 상세한 투자 계획을 수립하세요. 이는 다음을 포함해야 합니다:

당신의 추천: 가장 설득력 있는 논증에 의해 뒷받침되는 결정적인 입장.
근거: 왜 이러한 논증이 당신의 결론으로 이끄는지에 대한 설명.
전략적 행동: 추천을 실행하기 위한 구체적인 단계.
유사한 상황에서의 과거 실수를 고려하세요. 이러한 통찰력을 사용하여 의사결정을 개선하고 학습하며 발전하고 있음을 확실히 하세요. 특별한 형식 없이 자연스럽게 말하는 것처럼 대화형으로 분석을 제시하세요.



실수에 대한 과거 성찰:
\"{past_memory_str}\"

토론 내용:
토론 히스토리:
{history}

답변은 가급적 한글로 작성해주시고, 꼭 필요한 경우에만 영어를 사용해주시기 바랍니다.
"""
        response = llm.invoke(prompt)

        new_investment_debate_state = {
            "judge_decision": response.content,
            "history": investment_debate_state.get("history", ""),
            "bear_history": investment_debate_state.get("bear_history", ""),
            "bull_history": investment_debate_state.get("bull_history", ""),
            "current_response": response.content,
            "count": investment_debate_state["count"],
        }

        return {
            "investment_debate_state": new_investment_debate_state,
            "investment_plan": response.content,
        }

    return research_manager_node
