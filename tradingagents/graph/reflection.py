# TradingAgents/graph/reflection.py

from typing import Dict, Any
from langchain_openai import ChatOpenAI


class Reflector:
    """Handles reflection on decisions and updating memory."""

    def __init__(self, quick_thinking_llm: ChatOpenAI):
        """Initialize the reflector with an LLM."""
        self.quick_thinking_llm = quick_thinking_llm
        self.reflection_system_prompt = self._get_reflection_prompt()

    def _get_reflection_prompt(self) -> str:
        """Get the system prompt for reflection."""
        return """
당신은 거래 결정 및 분석을 검토하고, 포괄적이고 단계별로 분석을 제공하는 전문 금융 애널리스트입니다.
당신의 목표는 투자 결정에 대한 상세한 통찰을 제공하고, 개선 기회를 강조하는 것입니다. 아래 지침을 엄격히 준수하세요:

1. 추론(Reasoning):
   - 각 거래 결정이 올바른지(수익 증가) 또는 잘못되었는지(수익 감소) 판단하세요.
   - 성공 또는 실수에 기여한 요인을 분석하세요. 다음을 고려하세요:
     - 시장 정보(마켓 인텔리전스)
     - 기술적 지표
     - 기술적 신호
     - 가격 움직임 분석
     - 전체 시장 데이터 분석
     - 뉴스 분석
     - 소셜 미디어 및 감정 분석
     - 펀더멘털(기초) 데이터 분석
     - 각 요인이 의사결정에 미친 중요도를 평가하세요.

2. 개선(Improvement):
   - 잘못된 결정이 있다면, 수익을 극대화할 수 있도록 수정안을 제시하세요.
   - 구체적인 개선 조치 또는 권장사항을 상세히 나열하세요. (예: 특정 날짜에 HOLD에서 BUY로 변경 등)

3. 요약(Summary):
   - 성공과 실수에서 얻은 교훈을 요약하세요.
   - 이러한 교훈이 향후 거래 상황에 어떻게 적용될 수 있는지, 유사한 상황 간의 연결고리를 강조하여 지식이 실제로 활용될 수 있도록 하세요.

4. 핵심 문장(Query):
   - 요약에서 도출된 핵심 인사이트를 1000토큰 이내의 간결한 한 문장으로 추출하세요.
   - 이 문장은 교훈과 추론의 본질을 쉽게 참고할 수 있도록 압축적으로 담아야 합니다.

위 지침을 반드시 따르며, 결과물은 상세하고, 정확하며, 실행 가능해야 합니다. 분석에 참고할 수 있도록 가격 움직임, 기술적 지표, 뉴스, 감정 등 시장에 대한 객관적 설명도 함께 제공될 것입니다.
답변은 가급적 한글로 작성해주시고, 꼭 필요한 경우에만 영어를 사용해주시기 바랍니다.
"""

    def _extract_current_situation(self, current_state: Dict[str, Any]) -> str:
        """Extract the current market situation from the state."""
        curr_market_report = current_state["market_report"]
        curr_sentiment_report = current_state["sentiment_report"]
        curr_news_report = current_state["news_report"]
        curr_fundamentals_report = current_state["fundamentals_report"]
        curr_ben_graham_report = current_state["ben_graham_report"]
        curr_warren_buffett_report = current_state["warren_buffett_report"]
        

        return f"{curr_market_report}\n\n{curr_sentiment_report}\n\n{curr_news_report}\n\n{curr_fundamentals_report}\n\n{curr_ben_graham_report}\n\n{curr_warren_buffett_report}"

    def _reflect_on_component(
        self, component_type: str, report: str, situation: str, returns_losses
    ) -> str:
        """Generate reflection for a component."""
        messages = [
            ("system", self.reflection_system_prompt),
            (
                "human",
                f"Returns: {returns_losses}\n\nAnalysis/Decision: {report}\n\nObjective Market Reports for Reference: {situation}",
            ),
        ]

        result = self.quick_thinking_llm.invoke(messages).content
        return result

    def reflect_bull_researcher(self, current_state, returns_losses, bull_memory):
        """Reflect on bull researcher's analysis and update memory."""
        situation = self._extract_current_situation(current_state)
        bull_debate_history = current_state["investment_debate_state"]["bull_history"]

        result = self._reflect_on_component(
            "BULL", bull_debate_history, situation, returns_losses
        )
        bull_memory.add_situations([(situation, result)])

    def reflect_bear_researcher(self, current_state, returns_losses, bear_memory):
        """Reflect on bear researcher's analysis and update memory."""
        situation = self._extract_current_situation(current_state)
        bear_debate_history = current_state["investment_debate_state"]["bear_history"]

        result = self._reflect_on_component(
            "BEAR", bear_debate_history, situation, returns_losses
        )
        bear_memory.add_situations([(situation, result)])

    def reflect_trader(self, current_state, returns_losses, trader_memory):
        """Reflect on trader's decision and update memory."""
        situation = self._extract_current_situation(current_state)
        trader_decision = current_state["trader_investment_plan"]

        result = self._reflect_on_component(
            "TRADER", trader_decision, situation, returns_losses
        )
        trader_memory.add_situations([(situation, result)])

    def reflect_invest_judge(self, current_state, returns_losses, invest_judge_memory):
        """Reflect on investment judge's decision and update memory."""
        situation = self._extract_current_situation(current_state)
        judge_decision = current_state["investment_debate_state"]["judge_decision"]

        result = self._reflect_on_component(
            "INVEST JUDGE", judge_decision, situation, returns_losses
        )
        invest_judge_memory.add_situations([(situation, result)])

    def reflect_risk_manager(self, current_state, returns_losses, risk_manager_memory):
        """Reflect on risk manager's decision and update memory."""
        situation = self._extract_current_situation(current_state)
        judge_decision = current_state["risk_debate_state"]["judge_decision"]

        result = self._reflect_on_component(
            "RISK JUDGE", judge_decision, situation, returns_losses
        )
        risk_manager_memory.add_situations([(situation, result)])
