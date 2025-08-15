from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json


def create_fundamentals_analyst(llm, toolkit):
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        company_name = state["company_of_interest"]

        if toolkit.config["online_tools"]:
            tools = [toolkit.get_fundamentals_openai]
        else:
            tools = [
                toolkit.get_finnhub_company_insider_sentiment,
                toolkit.get_finnhub_company_insider_transactions,
                toolkit.get_simfin_balance_sheet,
                toolkit.get_simfin_cashflow,
                toolkit.get_simfin_income_stmt,
            ]

        system_message = (
            "당신은 회사의 지난 주 펀더멘털 정보를 분석하는 임무를 맡은 연구원입니다. 재무 문서, 회사 프로필, 기본 회사 재무, 회사 재무 이력, 내부자 정서 및 내부자 거래 등 회사의 펀더멘털 정보에 대한 종합적인 보고서를 작성하여 트레이더들에게 정보를 제공하기 위해 회사의 펀더멘털 정보에 대한 전체적인 관점을 제공해 주세요. 가능한 한 많은 세부 사항을 포함시켜 주세요. 단순히 트렌드가 혼재되어 있다고 말하지 말고, 트레이더들이 결정을 내리는 데 도움이 될 수 있는 상세하고 세밀한 분석과 통찰력을 제공해 주세요."
            + " 보고서의 요점을 정리하고 읽기 쉽게 구성된 마크다운 표를 보고서 끝에 반드시 추가해 주세요.",
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
            "fundamentals_report": report,
        }

    return fundamentals_analyst_node
