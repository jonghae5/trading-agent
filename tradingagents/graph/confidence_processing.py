# TradingAgents/graph/signal_processing.py

from langchain_openai import ChatOpenAI

class ConfidenceProcessor:
    """Processes trading signals to extract a confidence score (0% ~ 100%)."""

    def __init__(self, quick_thinking_llm: ChatOpenAI):
        """Initialize with an LLM for processing."""
        self.quick_thinking_llm = quick_thinking_llm

    def process_confidence(self, full_signal: str) -> str:
        """
        Process a full trading signal to extract the confidence score (0% ~ 100%).

        Args:
            full_signal: Complete trading signal text

        Returns:
            Confidence score as a percentage string (e.g., "85%")
        """
        messages = [
            (
                "system",
                "당신은 애널리스트 그룹이 제공한 단락이나 금융 보고서를 분석하여, 투자 결정의 신뢰도(Confidence Score)를 0%에서 100% 사이의 값으로만 추출하는 어시스턴트야. 추가 설명이나 텍스트 없이, 오직 신뢰도 수치(예: 85%)만을 출력해줘.",
            ),
            ("human", full_signal),
        ]

        return self.quick_thinking_llm.invoke(messages).content

