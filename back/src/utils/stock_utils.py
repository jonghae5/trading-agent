import yfinance as yf


def is_korea_stock(ticker: str) -> bool:
    """한국 주식 코드인지 확인 (6자리 숫자)"""
    if ticker.isdigit() and len(ticker) == 6:
        return True
    return False


def guess_korea_market(ticker: str) -> str:
    """한국 주식의 시장을 추정하여 적절한 접미사를 붙여 반환

    Args:
        ticker: 주식 티커 (예: "005930")

    Returns:
        str: 시장 접미사가 붙은 티커 (예: "005930.KS") 또는 원본 티커
    """
    # 코스피: .KS, 코스닥: .KQ
    if is_korea_stock(ticker):
        # 코스피 먼저 확인
        try:
            info_ks = yf.Ticker(ticker + ".KS").info
            if info_ks and "shortName" in info_ks and info_ks.get("exchange") == "KSC":
                return f"{ticker}.KS"
        except Exception:
            pass

        # 코스닥 확인
        try:
            info_kq = yf.Ticker(ticker + ".KQ").info
            if info_kq and "shortName" in info_kq and info_kq.get("exchange") == "KOE":
                return f"{ticker}.KQ"
        except Exception:
            pass

    return ticker