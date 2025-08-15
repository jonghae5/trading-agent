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


def getNewsData(query, start_date, end_date):
    """
    Scrape Google News search results for a given query and date range.
    query: str - search query
    start_date: str - start date in the format yyyy-mm-dd or mm/dd/yyyy
    end_date: str - end date in the format yyyy-mm-dd or mm/dd/yyyy
    """
    if "-" in start_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        start_date = start_date.strftime("%m/%d/%Y")
    if "-" in end_date:
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        end_date = end_date.strftime("%m/%d/%Y")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/101.0.4951.54 Safari/537.36"
        )
    }

    news_results = []
    page = 0
    while True:
        offset = page * 10
        url = (
            f"https://www.google.com/search?q={query}"
            f"&tbs=cdr:1,cd_min:{start_date},cd_max:{end_date}"
            f"&tbm=nws&start={offset}"
        )

        try:
            response = make_request(url, headers)
            soup = BeautifulSoup(response.content, "html.parser")
            results_on_page = soup.select("div.SoaBEf")

            if not results_on_page:
                break  # No more results found

            for el in results_on_page:
                try:
                    link = el.find("a")["href"]
                    title = el.select_one("div.MBeuO").get_text()
                    snippet = el.select_one(".GI74Re").get_text()
                    date = el.select_one(".LfVVr").get_text()
                    source = el.select_one(".NUnG9d span").get_text()
                    news_results.append(
                        {
                            "link": link,
                            "title": title,
                            "snippet": snippet,
                            "date": date,
                            "source": source,
                        }
                    )
                except Exception as e:
                    print(f"Error processing result: {e}")
                    # If one of the fields is not found, skip this result
                    continue

            # Update the progress bar with the current count of results scraped

            # Check for the "Next" link (pagination)
            next_link = soup.find("a", id="pnnext")
            if not next_link:
                break

            page += 1

        except Exception as e:
            print(f"Failed after multiple retries: {e}")
            break

    return news_results


def getNewsDataV2(query, start_date, end_date, max_results=50):
    """
    개선된 Google News 크롤링 함수 (버전 2)
    - 더 안정적인 CSS 선택자 사용
    - 결과 수 제한 옵션 추가
    - 에러 처리 개선
    """
    if "-" in start_date:
        start_date = datetime.strptime(start_date, "%Y-%m-%d")
        start_date = start_date.strftime("%m/%d/%Y")
    if "-" in end_date:
        end_date = datetime.strptime(end_date, "%Y-%m-%d")
        end_date = end_date.strftime("%m/%d/%Y")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
        "Accept-Language": "ko-KR,ko;q=0.9,en;q=0.8",
        "Accept-Encoding": "gzip, deflate, br",
        "Connection": "keep-alive",
        "Upgrade-Insecure-Requests": "1",
    }

    news_results = []
    page = 0
    
    while len(news_results) < max_results:
        offset = page * 10
        url = (
            f"https://www.google.com/search?q={query}"
            f"&tbs=cdr:1,cd_min:{start_date},cd_max:{end_date}"
            f"&tbm=nws&start={offset}&hl=ko"
        )

        try:
            response = make_request(url, headers)
            if response.status_code != 200:
                print(f"HTTP 상태 코드: {response.status_code}")
                break
                
            soup = BeautifulSoup(response.content, "html.parser")
            
            # 다양한 CSS 선택자 시도
            results_selectors = [
                "div.SoaBEf",
                "div[data-hveid]",
                "div.MjjYud",
                "div.g"
            ]
            
            results_on_page = []
            for selector in results_selectors:
                results_on_page = soup.select(selector)
                if results_on_page:
                    break
            
            if not results_on_page:
                print("더 이상 결과를 찾을 수 없습니다.")
                break

            for el in results_on_page:
                if len(news_results) >= max_results:
                    break
                    
                try:
                    # 링크 추출 시도
                    link_elem = el.find("a")
                    if not link_elem:
                        continue
                    link = link_elem.get("href", "")
                    
                    # 제목 추출 시도 (여러 선택자)
                    title_selectors = ["div.MBeuO", "h3", ".LC20lb", ".DKV0Md"]
                    title = ""
                    for sel in title_selectors:
                        title_elem = el.select_one(sel)
                        if title_elem:
                            title = title_elem.get_text(strip=True)
                            break
                    
                    # 스니펫 추출 시도
                    snippet_selectors = [".GI74Re", ".Y3v8qd", ".VwiC3b"]
                    snippet = ""
                    for sel in snippet_selectors:
                        snippet_elem = el.select_one(sel)
                        if snippet_elem:
                            snippet = snippet_elem.get_text(strip=True)
                            break
                    
                    # 날짜 추출 시도
                    date_selectors = [".LfVVr", ".f", ".slp"]
                    date = ""
                    for sel in date_selectors:
                        date_elem = el.select_one(sel)
                        if date_elem:
                            date = date_elem.get_text(strip=True)
                            break
                    
                    # 소스 추출 시도
                    source_selectors = [".NUnG9d span", ".fxC9Ne", ".CEMjEf"]
                    source = ""
                    for sel in source_selectors:
                        source_elem = el.select_one(sel)
                        if source_elem:
                            source = source_elem.get_text(strip=True)
                            break
                    
                    # 필수 필드가 있는 경우에만 추가
                    if link and title:
                        news_results.append({
                            "link": link,
                            "title": title,
                            "snippet": snippet,
                            "date": date,
                            "source": source,
                        })
                        
                except Exception as e:
                    print(f"결과 처리 중 오류: {e}")
                    continue

            # 다음 페이지 확인
            next_selectors = ["a#pnnext", "a[aria-label='다음']", "a[aria-label='Next']"]
            next_link = None
            for sel in next_selectors:
                next_link = soup.select_one(sel)
                if next_link:
                    break
                    
            if not next_link:
                print("마지막 페이지에 도달했습니다.")
                break

            page += 1
            print(f"페이지 {page} 완료, 현재 결과 수: {len(news_results)}")

        except Exception as e:
            print(f"페이지 {page} 처리 중 오류: {e}")
            break

    print(f"총 {len(news_results)}개의 뉴스 결과를 수집했습니다.")
    return news_results
