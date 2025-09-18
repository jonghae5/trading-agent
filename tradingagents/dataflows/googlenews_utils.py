import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime
import time
import random
from tenacity import (
    retry,
    stop_after_attempt,
    wait_exponential,
    retry_if_exception_type,
    retry_if_result,
)

from duckduckgo_search import DDGS
from datetime import datetime


def is_korea_stock(ticker: str):
    if ticker.isdigit() and len(ticker) == 6:
        return True
    return False

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

def is_rate_limited(response):
    """Check if the response indicates rate limiting (status code 429)"""
    return response.status_code == 429


@retry(
    retry=(retry_if_result(is_rate_limited)),
    wait=wait_exponential(multiplier=1, min=4, max=60),
    stop=stop_after_attempt(5),
)
def make_request(url, headers):
    """Make a request with retry logic for rate limiting"""
    # Random delay before each request to avoid detection
    time.sleep(random.uniform(2, 6))
    response = requests.get(url, headers=headers)
    return response


# def getNewsData(query, start_date, end_date):
#     """
#     Scrape Google News search results for a given query and date range.
#     query: str - search query
#     start_date: str - start date in the format yyyy-mm-dd or mm/dd/yyyy
#     end_date: str - end date in the format yyyy-mm-dd or mm/dd/yyyy
#     """
#     if "-" in start_date:
#         start_date = datetime.strptime(start_date, "%Y-%m-%d")
#         start_date = start_date.strftime("%m/%d/%Y")
#     if "-" in end_date:
#         end_date = datetime.strptime(end_date, "%Y-%m-%d")
#         end_date = end_date.strftime("%m/%d/%Y")

#     headers = {
#         "User-Agent": (
#             "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
#             "AppleWebKit/537.36 (KHTML, like Gecko) "
#             "Chrome/101.0.4951.54 Safari/537.36"
#         )
#     }

#     news_results = []
#     page = 0
#     while True:
#         offset = page * 10
#         url = (
#             f"https://www.google.com/search?q={query}"
#             f"&tbs=cdr:1,cd_min:{start_date},cd_max:{end_date}"
#             f"&tbm=nws&start={offset}"
#         )

#         try:
#             response = make_request(url, headers)
#             soup = BeautifulSoup(response.content, "html.parser")
#             results_on_page = soup.select("div.SoaBEf")

#             if not results_on_page:
#                 break  # No more results found

#             for el in results_on_page:
#                 try:
#                     link = el.find("a")["href"]
#                     title = el.select_one("div.MBeuO").get_text()
#                     snippet = el.select_one(".GI74Re").get_text()
#                     date = el.select_one(".LfVVr").get_text()
#                     source = el.select_one(".NUnG9d span").get_text()
#                     news_results.append(
#                         {
#                             "link": link,
#                             "title": title,
#                             "snippet": snippet,
#                             "date": date,
#                             "source": source,
#                         }
#                     )
#                 except Exception as e:
#                     print(f"Error processing result: {e}")
#                     # If one of the fields is not found, skip this result
#                     continue

#             # Update the progress bar with the current count of results scraped

#             # Check for the "Next" link (pagination)
#             next_link = soup.find("a", id="pnnext")
#             if not next_link:
#                 break

#             page += 1

#         except Exception as e:
#             print(f"Failed after multiple retries: {e}")
#             break

#     return news_results

def getNewsData(query, start_date, end_date):
    """
    구글 뉴스 크롤링 대신, 최신 웹 검색 API(예: DuckDuckGo, SerpAPI, Bing Web Search 등)를 활용하여
    뉴스 결과를 가져오는 방식으로 변경합니다.

    DuckDuckGo의 비공식 API(duckduckgo-search 패키지)를 활용한 예시입니다.
    (pip install duckduckgo-search)
    """

    # 날짜 필터링을 위해 datetime 변환
    def to_datetime(date_str):
        if "-" in date_str:
            return datetime.strptime(date_str, "%Y-%m-%d")
        try:
            return datetime.strptime(date_str, "%m/%d/%Y")
        except Exception:
            return None

    start_dt = to_datetime(start_date)
    end_dt = to_datetime(end_date)

    max_results = 30
    news_results = []

    # DuckDuckGo 뉴스 검색
    try:
        with DDGS() as ddgs:
            # DDGS.news returns a generator
            # DuckDuckGo 뉴스 검색 결과를 반복적으로 가져옵니다.
            # ddgs.news()는 지정한 쿼리(query), 지역(region), 안전검색(safesearch), 기간(timelimit) 옵션에 따라
            # 뉴스 기사들을 generator 형태로 반환합니다.
            # region="wt-wt": 전세계 뉴스, safesearch="Off": 성인/폭력 등 제한 없음, timelimit="m": 최근 1달
            # 최신 뉴스가 우선적으로 반환됩니다.
            print(f"DuckDuckGo 뉴스 검색 시작: 쿼리='{query}', 기간={start_date}~{end_date}")
            query_with_name = get_korea_stock_name(query)
            print(f"DuckDuckGo 뉴스 검색 시작: 쿼리 변환(KR)='{query_with_name}', 기간={start_date}~{end_date}")
            if not query_with_name:
                query_with_name = query

            
            for result in ddgs.news(query_with_name, region="wt-wt", safesearch="Off", timelimit="m"):
                # 새로운 DuckDuckGo 응답 형태 처리
                # date는 이제 timestamp 형태 (예: 1755234060)
                pubdate_raw = result.get("date")
                relative_time = result.get("relative_time", "")
                pub_dt = None
                pubdate_str = ""
                
                if pubdate_raw:
                    try:
                        # timestamp를 datetime으로 변환
                        if isinstance(pubdate_raw, (int, float)):
                            pub_dt = datetime.fromtimestamp(pubdate_raw)
                            pubdate_str = pub_dt.strftime("%Y-%m-%d %H:%M:%S")
                        elif isinstance(pubdate_raw, str):
                            # 문자열인 경우 기존 처리 방식 유지
                            pub_dt = datetime.fromisoformat(pubdate_raw.replace("Z", "+00:00"))
                            pubdate_str = pubdate_raw
                    except Exception as e:
                        # timestamp 변환 실패 시 relative_time 사용
                        print(f"날짜 변환 실패: {pubdate_raw}, 에러: {e}")
                        pubdate_str = relative_time
                        pub_dt = None
                else:
                    pubdate_str = relative_time

                news_results.append({
                    "link": result.get("url", ""),
                    "title": result.get("title", ""),
                    "snippet": result.get("excerpt", ""),  # body -> excerpt로 변경
                    "date": pubdate_str,
                    "source": result.get("source", ""),
                    "relative_time": relative_time,  # 상대 시간 정보 추가
                    "image": result.get("image", ""),  # 이미지 URL 추가
                })
                
                if len(news_results) >= max_results:
                    break

    except Exception as e:
        print(f"DuckDuckGo 뉴스 검색 중 오류 발생: {e}")
        print("빈 결과를 반환합니다.")
        return []

    print(f"DuckDuckGo에서 {len(news_results)}개의 뉴스 결과를 수집했습니다.")
    return news_results
