import json
import os
import requests
from datetime import datetime
from typing import List, Dict, Any
import yfinance as yf

def is_korea_stock(ticker: str):
    if ticker.isdigit() and len(ticker) == 6:
        return True
    return False

def guess_korea_market(ticker: str):
    # 코스피: .KS, 코스닥: .KQ
    if is_korea_stock(ticker):
        try:
            info_ks = yf.Ticker(ticker + ".KS").info
            if info_ks and "shortName" in info_ks and info_ks.get("exchange") == "KSC":
                return f"{ticker}.KS"
        except Exception:
            pass
        try:
            info_kq = yf.Ticker(ticker + ".KQ").info
            if info_kq and "shortName" in info_kq and info_kq.get("exchange") == "KOE":
                return f"{ticker}.KQ"
        except Exception:
            pass
    return ticker

def get_korea_stock_name(ticker: str):
    """
    한국 주식 티커에 대해 종목 이름을 반환합니다. (pykrx 사용)
    """
    if is_korea_stock(ticker):
        try:
            from pykrx import stock
            ticker_name = stock.get_market_ticker_name(ticker)
            return ticker_name
        except Exception:
            return ""
    return ""


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

def get_opendartreader_api_key():
    """환경 변수에서 Finnhub API 키를 가져옵니다."""
    api_key = os.getenv('OPENDARTREADER_API_KEY')
    if not api_key:
        raise ValueError("OPENDARTREADER_API_KEY 환경 변수가 설정되지 않았습니다.")
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
        'symbol': guess_korea_market(ticker.upper()),
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
    한국 주식인 경우 빈 데이터 반환 (DART에서 제공하지 않음), 그 외에는 Finnhub API를 사용합니다.
    
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
        'symbol': guess_korea_market(ticker.upper()),
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
    한국 주식인 경우 빈 데이터 반환 (DART에서 제공하지 않음), 그 외에는 Finnhub API를 사용합니다.
    
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
        'symbol': guess_korea_market(ticker.upper()),
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
    한국 주식인 경우 OpenDartReader, 그 외에는 Finnhub API를 사용하여 재무제표 데이터를 가져옵니다.
    
    Args:
        ticker: 회사 티커 심볼
        freq: 보고 주기 ("annual" 또는 "quarterly")
        from_date: 시작 날짜 (YYYY-MM-DD) - endDate 필터링용
        to_date: 종료 날짜 (YYYY-MM-DD) - endDate 필터링용
    
    Returns:
        재무제표 전체 데이터 (bs, ic, cf 포함)
    """
    if is_korea_stock(ticker):
        try:
            import OpenDartReader
            dart_api_key = get_opendartreader_api_key()
            dart = OpenDartReader(dart_api_key)

            # from_date가 YYYYMMDD 형식의 문자열로 들어오면, 연도/월 추출

            def get_report_code_and_form(base_year, year, from_date):
                """
                base_year와 year가 같으면 분기/반기/3분기 보고서, 다르면 연간보고서
                """
                if base_year == year and from_date and len(from_date) >= 6:
                    # from_date: YYYYMMDD or YYYY-MM-DD
                    try:
                        if '-' in from_date:
                            dt = datetime.strptime(from_date[:10], "%Y-%m-%d")
                        else:
                            dt = datetime.strptime(from_date[:8], "%Y%m%d")
                        month = dt.month
                    except Exception:
                        month = 12
                    # 3, 6, 9, 12월 기준
                    if month >= 11:
                        return '11014', '3분기보고서'
                    elif month >= 8:
                        return '11012', '반기보고서'
                    elif month >= 5:
                        return '11013', '1분기보고서'
                    else:
                        return '11011', '사업보고서'
                else:
                    return '11011', '사업보고서'
            
            # from_date가 없으면 오늘 날짜로 기본값 설정 (YYYYMMDD)
            if not from_date:
                from_date = datetime.now().strftime("%Y%m%d")

            # from_date에서 연도 추출, 최근 4개년을 조회 대상으로 설정
            base_year = None
            years_to_try = [2025, 2024, 2023, 2022]  # 기본값

            if from_date and len(from_date) >= 4 and from_date[:4].isdigit():
                base_year = int(from_date[:4])
                years_to_try = [base_year - i for i in range(4)]

            fs_data = None
            fs_data_list = []
            report_code_form_map = {}  # year: (report_code, form)
            for year in years_to_try:
                try:
                    report_code, form_name = get_report_code_and_form(base_year, year, from_date)
                    report_code_form_map[year] = (report_code, form_name)
                    if report_code != "11011":
                        yearly_data = dart.finstate(ticker, year, report_code)
                    else:
                        yearly_data = dart.finstate_all(corp=ticker, bsns_year=year, reprt_code=report_code)
                    if yearly_data is not None and not yearly_data.empty:
                        # form 정보도 같이 저장
                        yearly_data['__dart_form_name'] = form_name
                        yearly_data['__dart_report_code'] = report_code
                        fs_data_list.append(yearly_data)
                except Exception as fs_error:
                    print(f"{year}년 {form_name}({report_code}) 재무제표 조회 실패: {fs_error}")
                    continue
            if fs_data_list:
                import pandas as pd
                fs_data = pd.concat(fs_data_list, ignore_index=True)

            # 기업 개황 정보 가져오기
            company_info = None
            try:
                company_info = dart.company(ticker)
                print(f"OpenDartReader에서 기업 개황 정보를 수집했습니다.")
            except Exception as e:
                print(f"기업 개황 정보 가져오기 실패: {e}")

            # DataFrame이 비어있는지 체크
            has_fs_data = (
                fs_data is not None and
                not (hasattr(fs_data, 'empty') and fs_data.empty) and
                len(fs_data) > 0
            )

            if has_fs_data:
                print(f"OpenDartReader에서 {len(fs_data)}개의 재무제표 결과를 수집했습니다.")

                # Finnhub 형식으로 변환
                def convert_dart_to_finnhub_format(df, ticker):
                    # Get unique business years
                    years = df['bsns_year'].unique()
                    converted_data = []

                    for year in years:
                        year_data = df[df['bsns_year'] == year]
                        # form_name, report_code 추출
                        form_name = year_data['__dart_form_name'].iloc[0] if '__dart_form_name' in year_data.columns else '사업보고서'
                        report_code = year_data['__dart_report_code'].iloc[0] if '__dart_report_code' in year_data.columns else '11011'

                        # filedDate: 가장 최근 frmtrm_dt
                        filed_date = year_data.iloc[0].get('frmtrm_dt', f"{year}-12-31")

                        # 분기 정보 추출
                        if report_code == '11013':
                            period = "Q1"
                            quarter = 1
                        elif report_code == '11012':
                            period = "H1"
                            quarter = 2
                        elif report_code == '11014':
                            period = "Q3"
                            quarter = 3
                        else:
                            period = "FY"
                            quarter = 0

                        # Create Finnhub-like structure
                        report_entry = {
                            "symbol": ticker,
                            "cik": ticker,  # Use ticker as CIK for Korean stocks
                            "accessNumber": f"dart-{ticker}-{year}-{report_code}",
                            "year": int(year),
                            "quarter": quarter,
                            "form": form_name,
                            "filedDate": filed_date,
                            "period": period,
                            "report": {}
                        }
                        
                        # Convert balance sheet (BS) - Finnhub 형식: 리스트로 변환
                        bs_data = year_data[year_data['sj_div'] == 'BS']
                        if not bs_data.empty:
                            bs_list = []
                            for _, row in bs_data.iterrows():
                                account_name = row['account_nm']
                                try:
                                    # Remove commas and convert to number
                                    amount_str = str(row['thstrm_amount']).replace(',', '')
                                    amount = float(amount_str) if amount_str.replace('.', '').replace('-', '').isdigit() else 0
                                except (ValueError, TypeError):
                                    amount = 0
                                
                                bs_list.append({
                                    "concept": account_name,  # 한글 계정명 그대로 사용
                                    "value": amount,
                                    "unit": "KRW"
                                })
                            report_entry["report"]["bs"] = bs_list
                        
                        # Convert income statement (IS) - Finnhub 형식: 리스트로 변환
                        is_data = year_data[year_data['sj_div'].isin(['IS', 'CIS'])]
                        if not is_data.empty:
                            is_list = []
                            for _, row in is_data.iterrows():
                                account_name = row['account_nm']
                                try:
                                    # Remove commas and convert to number
                                    amount_str = str(row['thstrm_amount']).replace(',', '')
                                    amount = float(amount_str) if amount_str.replace('.', '').replace('-', '').isdigit() else 0
                                except (ValueError, TypeError):
                                    amount = 0
                                
                                is_list.append({
                                    "concept": account_name,  # 한글 계정명 그대로 사용
                                    "value": amount,
                                    "unit": "KRW"
                                })
                            report_entry["report"]["ic"] = is_list
                        
                        # Convert cash flow (CF) - Finnhub 형식: 리스트로 변환
                        cf_data = year_data[year_data['sj_div'] == 'CF']
                        if not cf_data.empty:
                            cf_list = []
                            for _, row in cf_data.iterrows():
                                account_name = row['account_nm']
                                try:
                                    # Remove commas and convert to number
                                    amount_str = str(row['thstrm_amount']).replace(',', '')
                                    amount = float(amount_str) if amount_str.replace('.', '').replace('-', '').isdigit() else 0
                                except (ValueError, TypeError):
                                    amount = 0
                                
                                cf_list.append({
                                    "concept": account_name,  # 한글 계정명 그대로 사용
                                    "value": amount,
                                    "unit": "KRW"
                                })
                            report_entry["report"]["cf"] = cf_list
                        
                        converted_data.append(report_entry)
                    
                    return {
                        "symbol": ticker,
                        "data": converted_data
                    }
                
                return convert_dart_to_finnhub_format(fs_data, ticker)
            else:
                print(f"OpenDartReader에서 0개의 재무제표 결과를 수집했습니다.")
                return {
                    "symbol": ticker,
                    "data": []
                }
                    
        except Exception as e:
            print(f"OpenDartReader Error: {e}")
            return {
                "symbol": ticker,
                "data": []
            }
    else:
        # 해외 주식의 경우 기존 Finnhub API 사용
        api_key = get_finnhub_api_key()
        url = f"https://finnhub.io/api/v1/stock/financials-reported"
        params = {
            'symbol': guess_korea_market(ticker.upper()),
            'freq': freq,
            'token': api_key
        }
        
        if from_date:
            params['from'] = from_date
        if to_date:
            params['to'] = to_date
        
        try:
            response = requests.get(url, params=params)
            response.raise_for_status()
            data = response.json()
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
