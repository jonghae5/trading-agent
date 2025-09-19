import yfinance as yf
from pykrx import stock

def is_korea_stock(ticker: str) -> bool:
    """한국 주식 코드인지 확인 (6자리 숫자)"""
    if ticker.isdigit() and len(ticker) == 6:
        return True
    return False


def get_stock_name(ticker: str):
    """
    주식 티커에 대해 종목 이름을 반환합니다.
    한국 주식이면 pykrx, 아니면 yfinance를 사용합니다.
    """
    if is_korea_stock(ticker):
        try:
            ticker_name = stock.get_market_ticker_name(ticker)
            return ticker_name
        except Exception:
            return ""
    else:
        try:
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info
            # shortName이 있으면 그걸, 없으면 longName, 둘 다 없으면 ""
            return info.get("shortName") or info.get("longName") or ""
        except Exception:
            return ""

def guess_korea_market(ticker: str) -> str:
    """한국 주식의 시장을 추정하여 적절한 접미사를 붙여 반환

    Args:
        ticker: 주식 티커 (예: "005930")

    Returns:
        str: 시장 접미사가 붙은 티커 (예: "005930.KS") 또는 원본 티커
    """
    # 코스피: .KS, 코스닥: .KQ
    # 이미 .KS나 .KQ가 붙어 있으면 제거
    if ticker.endswith(".KS") or ticker.endswith(".KQ"):
        ticker = ticker[:-3]
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