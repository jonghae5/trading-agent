import functools
import time
import json


def create_trader(llm, memory):
    def trader_node(state, name):
        company_name = state["company_of_interest"]
        investment_plan = state["investment_plan"]
        market_research_report = state["market_report"]
        sentiment_report = state["sentiment_report"]
        news_report = state["news_report"]
        fundamentals_report = state["fundamentals_report"]

        curr_situation = f"{market_research_report}\n\n{sentiment_report}\n\n{news_report}\n\n{fundamentals_report}"
        past_memories = memory.get_memories(curr_situation, n_matches=2)

        past_memory_str = ""
        if past_memories:
            for i, rec in enumerate(past_memories, 1):
                past_memory_str += rec["recommendation"] + "\n\n"
        else:
            past_memory_str = "No past memories found."

        context = {
            "role": "user",
            "content": f"애널리스트 팀의 종합 분석을 바탕으로 {company_name}에 맞춘 투자 계획을 제시합니다. 이 계획은 최신 기술적 시장 동향, 거시경제 지표, 그리고 소셜 미디어의 투자자 정서를 반영합니다. 아래의 투자 계획을 참고하여 다음 거래 결정을 평가하는 데 활용하세요.\n\n제안된 투자 계획: {investment_plan}\n\n이 인사이트들을 활용하여 신중하고 전략적인 결정을 내리시기 바랍니다.",
        }

        messages = [
            {
                "role": "system",
                "content": f"""당신은 시장 데이터를 분석하여 투자 결정을 내리는 트레이딩 에이전트입니다. 분석을 바탕으로 매수, 매도, 혹은 보유 중 하나의 구체적인 추천을 제시하세요. 반드시 명확한 결론을 내리고, 답변 마지막에 'FINAL TRANSACTION PROPOSAL: **매수/보유/매도**' 형식으로 최종 거래 제안을 명시하세요. 과거 결정에서 얻은 교훈을 반드시 반영하여 실수를 반복하지 않도록 하세요. 다음은 유사한 상황에서 거래했던 경험과 그로부터 얻은 교훈입니다: {past_memory_str}""",
            },
            context,
        ]

        result = llm.invoke(messages)

        return {
            "messages": [result],
            "trader_investment_plan": result.content,
            "sender": name,
        }

    return functools.partial(trader_node, name="Trader")
