from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json
from datetime import datetime

def create_fundamentals_analyst(llm, toolkit):
    def fundamentals_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        company_name = state["company_of_interest"]

        if toolkit.config["online_tools"]:
            tools = [
                toolkit.get_fundamentals_openai,
                toolkit.get_finnhub_company_insider_sentiment,
                toolkit.get_finnhub_company_insider_transactions,
                toolkit.get_simfin_balance_sheet,
                toolkit.get_simfin_cashflow,
                toolkit.get_simfin_income_stmt
                ]
        else:
            tools = []

        system_message = (
            "당신의 임무는 특정 회사의 지난 주 최신 재무 및 펀더멘털 데이터를 기반으로 심층 분석 보고서를 작성하는 것입니다. "
            + "분석 대상은 다음과 같습니다: "
            + "재무 문서, 회사 프로필, 최근 및 과거 재무 실적, 주요 재무 지표, 내부자 거래 및 내부자 정서, 경쟁사 대비 성과, 업계 트렌드 등. "
            + "단순히 트렌드가 혼재되어 있다고 말하지 말고, 수치와 근거를 활용하여 트레이더가 즉시 의사 결정을 내리는 데 도움이 되는 구체적이고 실행 가능한 인사이트를 제공하세요. "
            + "모든 분석은 최신 데이터 기준으로 하며, 가능한 한 상세하게 작성합니다. "
            + "특히, 분기 보고서와 연간 보고서를 모두 활용하여 증감률 분석(전년 동기 대비, 직전 분기 대비)을 반드시 포함하고, "
            + "매출, 영업이익, 당기순이익, 부채비율, 현금흐름 등 핵심 지표의 변화율을 중심으로 펀더멘털 성장 추세를 평가하세요. "
            + "지표별 YoY(전년동기대비) / QoQ(전분기대비) 성장률을 제시하고, 그 의미를 트레이더 관점에서 해석하세요. "
            + "분석 보고서의 마지막에는 핵심 요점을 정리한 마크다운 표를 반드시 추가하고, 각 지표별 해석과 트레이더 관점에서의 시사점을 명확히 표시하세요. "
            + "추가로, 분석 보고서에는 연간(사업)보고서뿐만 아니라 반기, 1분기, 3분기 보고서 등 다양한 주기의 재무 데이터가 존재합니다. 최신 보고서를 우선적으로 반영하되, 연간(사업)보고서도 충분히 검토하여 분석에 포함하세요. "
            + "보고서의 톤은 전문적이며, 월스트리트 애널리스트 리포트 스타일로 작성됩니다. "
            + f"Year(년도)를 보고 가장 최신년도순을 중점으로 대답을 해주세요. 오늘 년월은 {datetime.now().strftime('%Y%m')}입니다."
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
