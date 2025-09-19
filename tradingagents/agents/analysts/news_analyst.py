from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json


def create_news_analyst(llm, toolkit):
    def news_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]

        if toolkit.config["online_tools"]:
            tools = [toolkit.get_global_news_openai, toolkit.get_google_news, toolkit.get_finnhub_news]
        else:
            tools = [
                toolkit.get_reddit_news,
                toolkit.get_google_news,
            ]

        system_message = (
            "당신은 지난 주의 최근 뉴스와 트렌드를 분석하는 임무를 맡은 뉴스 연구원입니다. "
            + "트레이딩과 거시경제학에 관련된 세계 현황에 대한 종합적인 보고서를 작성해 주세요. "
            + "특히, 최신 뉴스(가장 최근에 보도된 뉴스)에 더 큰 비중을 두고 분석해 주시기 바랍니다. "
            + "최근 뉴스가 시장에 미치는 영향이나 시사점이 있다면 더욱 강조해서 설명해 주세요. "
            + "단순히 트렌드가 혼재되어 있다고 말하지 말고, 트레이더들이 결정을 내리는 데 도움이 될 수 있는 상세하고 세밀한 분석과 통찰력을 제공해 주세요. "
            + "그리고 반드시 'get_google_news' 도구를 우선적으로 사용하여 관련 뉴스를 수집하고, 그 결과를 보고서에 반드시 반영해 주세요. "
            + "보고서의 요점을 정리하고 읽기 쉽게 구성된 마크다운 표를 보고서 끝에 반드시 추가해 주세요."
        )

        prompt = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "당신은 다른 어시스턴트들과 협업하는 도움이 되는 AI 어시스턴트입니다."
                    " 제공된 도구를 사용하여 질문에 답하기 위해 진전을 이루어 주세요."
                    " 완전히 답할 수 없다면 괜찮습니다. 다른 도구를 가진 다른 어시스턴트가"
                    " 당신이 중단한 부분부터 도움을 줄 것입니다. 진전을 이루기 위해 할 수 있는 것을 실행하세요."
                    " 당신이나 다른 어시스턴트가 최종 거래 제안: **매수/보유/매도** 또는 결과물을 가지고 있다면,"
                    " 팀이 중단할 수 있도록 응답에 '최종 거래 제안: **매수/보유/매도**'를 접두사로 붙여주세요."
                    " 다음 도구들에 접근할 수 있습니다: {tool_names}.\n{system_message}"
                    " 답변은 가급적 한글로 작성해주시고, 꼭 필요한 경우에만 영어를 사용해주시기 바랍니다."
                    "참고로 현재 날짜는 {current_date}입니다. 분석하고자 하는 회사는 {ticker}입니다.",
                ),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )

        prompt = prompt.partial(system_message=system_message)
        prompt = prompt.partial(tool_names=", ".join([tool.name for tool in tools]))
        prompt = prompt.partial(current_date=current_date)
        prompt = prompt.partial(ticker=ticker)

        chain = prompt | llm.bind_tools(tools)
        result = chain.invoke(state["messages"])

        report = ""

        if len(result.tool_calls) == 0:
            report = result.content

        return {
            "messages": [result],
            "news_report": report,
        }

    return news_analyst_node
