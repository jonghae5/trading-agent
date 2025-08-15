from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json


def create_social_media_analyst(llm, toolkit):
    def social_media_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        company_name = state["company_of_interest"]

        if toolkit.config["online_tools"]:
            tools = [toolkit.get_stock_news_openai]
        else:
            tools = [
                toolkit.get_reddit_stock_info,
            ]

        system_message = (
            "당신은 지난 주 동안 특정 회사의 소셜 미디어 게시물, 최근 회사 뉴스, 그리고 대중의 정서를 분석하는 임무를 맡은 소셜 미디어 및 회사별 뉴스 연구원/분석가입니다. 회사명이 주어지면, 소셜 미디어와 사람들이 그 회사에 대해 말하는 것을 살펴보고, 사람들이 매일 회사에 대해 느끼는 감정 데이터를 분석하고, 최근 회사 뉴스를 살펴본 후 이 회사의 현재 상태에 대한 분석, 통찰력, 그리고 트레이더와 투자자들에게 미치는 시사점을 자세히 설명하는 포괄적이고 긴 보고서를 작성하는 것이 목표입니다. 소셜 미디어부터 감정, 뉴스까지 가능한 모든 소스를 살펴보도록 노력하세요. 단순히 트렌드가 혼재되어 있다고 말하지 말고, 트레이더들이 결정을 내리는 데 도움이 될 수 있는 상세하고 세밀한 분석과 통찰력을 제공해 주세요."
            + """ 보고서의 요점을 정리하고 읽기 쉽게 구성된 마크다운 표를 보고서 끝에 반드시 추가해 주세요.""",
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
                    "참고로 현재 날짜는 {current_date}입니다. 현재 분석하고자 하는 회사는 {ticker}입니다.",
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
            "sentiment_report": report,
        }

    return social_media_analyst_node
