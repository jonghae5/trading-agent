# TradingAgents/graph/signal_processing.py

from langchain_openai import ChatOpenAI


class SignalProcessor:
    """Processes trading signals to extract actionable decisions."""

    def __init__(self, quick_thinking_llm: ChatOpenAI):
        """Initialize with an LLM for processing."""
        self.quick_thinking_llm = quick_thinking_llm

    def process_signal(self, full_signal: str) -> str:
        """
        Process a full trading signal to extract the core decision.

        Args:
            full_signal: Complete trading signal text

        Returns:
            Extracted decision (BUY, SELL, or HOLD)
        """
        messages = [
            (
                "system",
                "당신은 애널리스트 그룹이 제공한 단락이나 금융 보고서를 분석하도록 설계된 효율적인 어시스턴트입니다. 투자 결정인 매도(SELL), 매수(BUY), 또는 보유(HOLD)를 추출하는 것이 당신의 임무입니다. 추가 텍스트나 정보를 추가하지 말고 추출된 결정(매도, 매수, 또는 보유)만을 출력으로 제공해 주세요.",
            ),
            ("human", full_signal),
        ]

        return self.quick_thinking_llm.invoke(messages).content
