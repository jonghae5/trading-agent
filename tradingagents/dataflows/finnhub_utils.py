import json
import os
import requests
from datetime import datetime
from typing import List, Dict, Any


def get_data_in_range(ticker, start_date, end_date, data_type, data_dir, period=None):
    """
    Gets finnhub data saved and processed on disk.
    Args:
        start_date (str): Start date in YYYY-MM-DD format.
        end_date (str): End date in YYYY-MM-DD format.
        data_type (str): Type of data from finnhub to fetch. Can be insider_trans, SEC_filings, news_data, insider_senti, or fin_as_reported.
        data_dir (str): Directory where the data is saved.
        period (str): Default to none, if there is a period specified, should be annual or quarterly.
    """

    if period:
        data_path = os.path.join(
            data_dir,
            "finnhub_data",
            data_type,
            f"{ticker}_{period}_data_formatted.json",
        )
    else:
        data_path = os.path.join(
            data_dir, "finnhub_data", data_type, f"{ticker}_data_formatted.json"
        )

    data = open(data_path, "r")
    data = json.load(data)

    # filter keys (date, str in format YYYY-MM-DD) by the date range (str, str in format YYYY-MM-DD)
    filtered_data = {}
    for key, value in data.items():
        if start_date <= key <= end_date and len(value) > 0:
            filtered_data[key] = value
    return filtered_data


def get_finnhub_api_key():
    """환경 변수에서 Finnhub API 키를 가져옵니다."""
    api_key = os.getenv('FINNHUB_API_KEY')
    if not api_key:
        raise ValueError("FINNHUB_API_KEY 환경 변수가 설정되지 않았습니다.")
    return api_key


def fetch_company_news_online(ticker: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Finnhub API를 사용하여 회사 뉴스를 가져옵니다.
    
    Args:
        ticker: 회사 티커 심볼
        start_date: 시작 날짜 (YYYY-MM-DD)
        end_date: 종료 날짜 (YYYY-MM-DD)
    
    Returns:
        뉴스 데이터 리스트
    """
    api_key = get_finnhub_api_key()
    
    # 날짜를 Unix timestamp로 변환
    start_timestamp = int(datetime.strptime(start_date, "%Y-%m-%d").timestamp())
    end_timestamp = int(datetime.strptime(end_date, "%Y-%m-%d").timestamp())
    
    url = f"https://finnhub.io/api/v1/company-news"
    params = {
        'symbol': ticker.upper(),
        'from': start_date,
        'to': end_date,
        'token': api_key
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        news_data = response.json()
        print(f"Finnhub에서 {len(news_data)}개의 회사 뉴스 결과를 수집했습니다.")
        return news_data
    except requests.exceptions.RequestException as e:
        print(f"뉴스 데이터 가져오기 실패: {e}")
        return []


def fetch_insider_sentiment_online(ticker: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Finnhub API를 사용하여 내부자 감정 데이터를 가져옵니다.
    
    Args:
        ticker: 회사 티커 심볼
        start_date: 시작 날짜 (YYYY-MM-DD)
        end_date: 종료 날짜 (YYYY-MM-DD)
    
    Returns:
        내부자 감정 데이터 리스트
    """
    api_key = get_finnhub_api_key()
    
    url = f"https://finnhub.io/api/v1/stock/insider-sentiment"
    params = {
        'symbol': ticker.upper(),
        'from': start_date,
        'to': end_date,
        'token': api_key
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        senti_data = data.get('data', [])
        print(f"Finnhub에서 {len(senti_data)}개의 내부자 감정 데이터 결과를 수집했습니다.")
        return senti_data
    except requests.exceptions.RequestException as e:
        print(f"내부자 감정 데이터 가져오기 실패: {e}")
        return []


def fetch_insider_transactions_online(ticker: str, start_date: str, end_date: str) -> List[Dict[str, Any]]:
    """
    Finnhub API를 사용하여 내부자 거래 데이터를 가져옵니다.
    
    Args:
        ticker: 회사 티커 심볼
        start_date: 시작 날짜 (YYYY-MM-DD)
        end_date: 종료 날짜 (YYYY-MM-DD)
    
    Returns:
        내부자 거래 데이터 리스트
    """
    api_key = get_finnhub_api_key()
    
    url = f"https://finnhub.io/api/v1/stock/insider-transactions"
    params = {
        'symbol': ticker.upper(),
        'from': start_date,
        'to': end_date,
        'token': api_key
    }
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        trans_data = data.get('data', [])
        print(f"Finnhub에서 {len(trans_data)}개의 내부자 거래 데이터 결과를 수집했습니다.")
        return trans_data
    except requests.exceptions.RequestException as e:
        print(f"내부자 거래 데이터 가져오기 실패: {e}")
        return []


def fetch_financials_reported_online(ticker: str, freq: str = "annual", from_date: str = None, to_date: str = None) -> Dict[str, Any]:
    """
    Finnhub API를 사용하여 재무제표 전체 데이터를 가져옵니다 (As Reported).
    이 데이터에는 Balance Sheet, Income Statement, Cash Flow가 모두 포함됩니다.
    
    Args:
        ticker: 회사 티커 심볼
        freq: 보고 주기 ("annual" 또는 "quarterly")
        from_date: 시작 날짜 (YYYY-MM-DD) - endDate 필터링용
        to_date: 종료 날짜 (YYYY-MM-DD) - endDate 필터링용
    
    Returns:
        재무제표 전체 데이터 (bs, ic, cf 포함)
    """
    api_key = get_finnhub_api_key()
    
    url = f"https://finnhub.io/api/v1/stock/financials-reported"
    params = {
        'symbol': ticker.upper(),
        'freq': freq,
        'token': api_key
    }
    
    # 날짜 필터링 추가
    if from_date:
        params['from'] = from_date
    if to_date:
        params['to'] = to_date
    
    try:
        response = requests.get(url, params=params)
        response.raise_for_status()
        data = response.json()
        # 데이터 구조에 따라 count를 출력 (list면 len, dict면 keys 등)
        if isinstance(data, dict) and "data" in data and isinstance(data["data"], list):
            print(f"Finnhub에서 {len(data['data'])}개의 재무제표(As Reported) 결과를 수집했습니다.")
        else:
            print(f"Finnhub에서 재무제표(As Reported) 데이터를 수집했습니다.")
        return data
    except requests.exceptions.RequestException as e:
        print(f"재무제표 데이터 가져오기 실패: {e}")
        return {}


def fetch_balance_sheet_online(ticker: str, freq: str = "annual", from_date: str = None, to_date: str = None) -> Dict[str, Any]:
    """
    Finnhub API를 사용하여 재무제표(Balance Sheet) 데이터를 가져옵니다.
    
    Args:
        ticker: 회사 티커 심볼
        freq: 보고 주기 ("annual" 또는 "quarterly")
        from_date: 시작 날짜 (YYYY-MM-DD) - endDate 필터링용
        to_date: 종료 날짜 (YYYY-MM-DD) - endDate 필터링용
    
    Returns:
        재무제표 데이터
    """
    data = fetch_financials_reported_online(ticker, freq, from_date, to_date)
    print(f"[Finnhub]fetch_balance_sheet_online")
    return data 


def fetch_income_statement_online(ticker: str, freq: str = "annual", from_date: str = None, to_date: str = None) -> Dict[str, Any]:
    """
    Finnhub API를 사용하여 손익계산서(Income Statement) 데이터를 가져옵니다.
    
    Args:
        ticker: 회사 티커 심볼
        freq: 보고 주기 ("annual" 또는 "quarterly")
        from_date: 시작 날짜 (YYYY-MM-DD) - endDate 필터링용
        to_date: 종료 날짜 (YYYY-MM-DD) - endDate 필터링용
    
    Returns:
        손익계산서 데이터
    """
    data = fetch_financials_reported_online(ticker, freq, from_date, to_date)
    print(f"[Finnhub]fetch_income_statement_online")
    return data


def fetch_cash_flow_online(ticker: str, freq: str = "annual", from_date: str = None, to_date: str = None) -> Dict[str, Any]:
    """
    Finnhub API를 사용하여 현금흐름표(Cash Flow Statement) 데이터를 가져옵니다.
    
    Args:
        ticker: 회사 티커 심볼
        freq: 보고 주기 ("annual" 또는 "quarterly")
        from_date: 시작 날짜 (YYYY-MM-DD) - endDate 필터링용
        to_date: 종료 날짜 (YYYY-MM-DD) - endDate 필터링용
    
    Returns:
        현금흐름표 데이터
    """
    data = fetch_financials_reported_online(ticker, freq, from_date, to_date)
    print(f"[Finnhub]fetch_cash_flow_online")
    return data
