from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
import time
import json


def create_market_analyst(llm, toolkit):

    def market_analyst_node(state):
        current_date = state["trade_date"]
        ticker = state["company_of_interest"]
        company_name = state["company_of_interest"]

        if toolkit.config["online_tools"]:
            tools = [
                toolkit.get_YFin_data_online,
                toolkit.get_stockstats_indicators_report_online,
            ]
        else:
            tools = [
                toolkit.get_YFin_data,
                toolkit.get_stockstats_indicators_report,
            ]

        system_message = (
            """당신은 금융 시장을 분석하는 임무를 맡은 트레이딩 어시스턴트입니다. 다음 목록에서 주어진 시장 상황이나 트레이딩 전략에 가장 관련성이 높은 지표들을 선택하는 것이 당신의 역할입니다. 중복 없이 상호 보완적인 통찰력을 제공하는 최대 8개의 지표를 선택하는 것이 목표입니다. 카테고리별 지표들은 다음과 같습니다:

이동평균:
- close_50_sma: 50일 단순이동평균: 중기 트렌드 지표. 사용법: 트렌드 방향을 식별하고 동적 지지/저항 역할. 팁: 가격에 지연이 있으므로 빠른 지표와 결합하여 시기적절한 신호를 얻으세요.
- close_200_sma: 200일 단순이동평균: 장기 트렌드 벤치마크. 사용법: 전체 시장 트렌드를 확인하고 골든/데드 크로스를 식별. 팁: 반응이 느리므로 빈번한 거래 진입보다는 전략적 트렌드 확인에 적합.
- close_10_ema: 10일 지수이동평균: 반응성이 높은 단기 평균. 사용법: 모멘텀의 빠른 변화와 잠재적 진입점을 포착. 팁: 변동성이 큰 시장에서는 노이즈가 발생하기 쉬우므로 장기 평균과 함께 사용하여 잘못된 신호를 필터링하세요.

MACD 관련:
- macd: MACD: EMA의 차이를 통해 모멘텀을 계산. 사용법: 크로스오버와 다이버전스를 트렌드 변화의 신호로 활용. 팁: 낮은 변동성이나 횡보 시장에서는 다른 지표로 확인하세요.
- macds: MACD 시그널: MACD 라인의 EMA 스무딩. 사용법: MACD 라인과의 크로스오버를 거래 신호로 활용. 팁: 거짓 신호를 피하기 위해 광범위한 전략의 일부여야 합니다.
- macdh: MACD 히스토그램: MACD 라인과 시그널 간의 간격 표시. 사용법: 모멘텀 강도를 시각화하고 다이버전스를 조기에 발견. 팁: 변동성이 클 수 있으므로 빠르게 움직이는 시장에서는 추가 필터와 함께 사용하세요.

모멘텀 지표:
- rsi: RSI: 모멘텀을 측정하여 과매수/과매도 상태를 표시. 사용법: 70/30 임계값을 적용하고 다이버전스를 관찰하여 반전 신호를 포착. 팁: 강한 트렌드에서는 RSI가 극값을 유지할 수 있으므로 항상 트렌드 분석과 교차 확인하세요.

변동성 지표:
- boll: 볼린저 미들: 볼린저 밴드의 기준이 되는 20일 SMA. 사용법: 가격 움직임의 동적 벤치마크 역할. 팁: 상단 및 하단 밴드와 결합하여 돌파나 반전을 효과적으로 발견하세요.
- boll_ub: 볼린저 상단 밴드: 일반적으로 중간선에서 표준편차 2배 위. 사용법: 잠재적 과매수 상태와 돌파 구간을 신호. 팁: 다른 도구로 신호를 확인하세요. 강한 트렌드에서는 가격이 밴드를 따라 움직일 수 있습니다.
- boll_lb: 볼린저 하단 밴드: 일반적으로 중간선에서 표준편차 2배 아래. 사용법: 잠재적 과매도 상태를 나타냄. 팁: 거짓 반전 신호를 피하기 위해 추가 분석을 사용하세요.
- atr: ATR: 평균 진폭을 측정하여 변동성을 나타냄. 사용법: 현재 시장 변동성에 따라 손절매 수준을 설정하고 포지션 크기를 조정. 팁: 반응적 측정이므로 광범위한 위험 관리 전략의 일부로 사용하세요.

거래량 기반 지표:
- vwma: VWMA: 거래량으로 가중된 이동평균. 사용법: 가격 행동을 거래량 데이터와 통합하여 트렌드를 확인. 팁: 거래량 급등으로 인한 왜곡된 결과를 주의하고 다른 거래량 분석과 함께 사용하세요.

다양하고 상호 보완적인 정보를 제공하는 지표를 선택하세요. 중복을 피하세요(예: rsi와 stochrsi를 모두 선택하지 마세요). 또한 주어진 시장 상황에 적합한 이유를 간략히 설명하세요. 도구를 호출할 때는 위에 제공된 지표의 정확한 이름을 사용하세요. 정의된 매개변수이므로 그렇지 않으면 호출이 실패합니다. 지표 생성에 필요한 CSV를 검색하기 위해 먼저 get_YFin_data를 호출해야 합니다. 관찰한 트렌드에 대한 매우 상세하고 미묘한 보고서를 작성하세요. 단순히 트렌드가 혼재되어 있다고 말하지 말고, 트레이더들이 결정을 내리는 데 도움이 될 수 있는 상세하고 세밀한 분석과 통찰력을 제공하세요."""
            + """ 보고서의 요점을 정리하고 읽기 쉽게 구성된 마크다운 표를 보고서 끝에 반드시 추가해 주세요."""
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
            "market_report": report,
        }

    return market_analyst_node
