import json
import re
import os
from datetime import datetime, timedelta
from functools import lru_cache
from typing import Any, Dict, List
from urllib.parse import quote
import requests


class NaverSearchClient:
    def __init__(self):
        self.client_id = os.getenv("NAVER_CLIENT_ID", "I6QgY4M3jZJtB6SV6jU5")
        self.client_secret = os.getenv("NAVER_CLIENT_SECRET", "wMwj8EOwkS") 
        self.base_url = os.getenv("NAVER_SEARCH_BASE_URL", "https://openapi.naver.com/v1/search")
        self.timeout_seconds = 30
        print(f"[NaverNews] 네이버 클라이언트 초기화 완료 - Client ID: {self.client_id[:10]}...")
    
    def _clean_html_tags(self, text: str) -> str:
        """HTML 태그 제거 및 텍스트 정리"""
        if not text:
            return ""
        
        # <b> 태그 제거
        text = re.sub(r'<b>', '', text)
        text = re.sub(r'</b>', '', text)
        
        # 다른 HTML 태그 제거
        text = re.sub(r'<[^>]+>', '', text)
        
        # HTML 엔터티 디코딩
        text = text.replace('&lt;', '<')
        text = text.replace('&gt;', '>')
        text = text.replace('&amp;', '&')
        text = text.replace('&quot;', '"')
        text = text.replace('&#39;', "'")
        
        return text.strip()
    
    def _format_date(self, pub_date: str) -> str:
        """Naver API 날짜를 YYYY-MM-DD 형식으로 변환"""
        try:
            # "Mon, 26 Sep 2016 07:50:00 +0900" -> "2016-09-26"
            dt = datetime.strptime(pub_date, "%a, %d %b %Y %H:%M:%S %z")
            return dt.strftime("%Y-%m-%d")
        except:
            try:
                # 다른 형식 시도
                dt = datetime.strptime(pub_date[:19], "%a, %d %b %Y %H:%M:%S")
                return dt.strftime("%Y-%m-%d")
            except:
                # 파싱 실패시 오늘 날짜
                return datetime.now().strftime("%Y-%m-%d")
    
    def _extract_source_from_url(self, url: str) -> str:
        """URL에서 언론사명 추출"""
        try:
            # 도메인에서 언론사명 추출
            domain_patterns = {
                'yonhapnews': '연합뉴스',
                'chosun': '조선일보',
                'joongang': '중앙일보',
                'donga': '동아일보',
                'hani': '한겨레',
                'khan': '경향신문',
                'segye': '세계일보',
                'munhwa': '문화일보',
                'seoul': '서울신문',
                'kookje': '국제신문',
                'busan': '부산일보',
                'kwnews': '광주일보',
                'etnews': '전자신문',
                'mk': '매일경제',
                'hankyung': '한국경제',
                'fnnews': '파이낸셜뉴스',
                'newsis': '뉴시스',
                'news1': '뉴스1',
                'yna': '연합뉴스',
                'naver': '네이버뉴스'
            }
            
            url_lower = url.lower()
            for pattern, source in domain_patterns.items():
                if pattern in url_lower:
                    return source
            
            # 도메인에서 직접 추출 시도
            import re
            match = re.search(r'://([^/]+)', url)
            if match:
                domain = match.group(1)
                domain = domain.replace('www.', '').replace('.com', '').replace('.co.kr', '')
                return domain.title()
            
            return "언론사"
            
        except:
            return "언론사"
    
    def search_news(self, query: str, display: int = 10, start: int = 1, sort: str = "date") -> Dict[str, Any]:
        """
        Naver News API를 사용한 뉴스 검색
        
        Args:
            query: 검색어
            display: 표시할 결과 수 (기본값: 10, 최대: 100)
            start: 검색 시작 위치 (기본값: 1, 최대: 1000) 
            sort: 정렬 방법 ("sim": 정확도순, "date": 날짜순)
        """
        
        if not self.client_id or not self.client_secret:
            print(f"[NaverNews] ❌ API 키 설정되지 않음 - 검색어: {query}")
            return {
                "query": query,
                "total_count": 0,
                "news": [],
                "error": "Naver API credentials not configured"
            }
        
        # 최신 뉴스 검색을 위한 쿼리 개선
        current_year = datetime.now().year
        
        # 검색어에 최신 키워드 추가 (sort가 date일 때만)
        enhanced_query = query
            
        print(f"[NaverNews] 🔍 뉴스 검색 시작 - 원본: '{query}' → 개선: '{enhanced_query}' (정렬: {sort})")
        encoded_query = enhanced_query
        url = f"{self.base_url}/news.json"
        
        params = {
            'query': encoded_query,
            'display': min(display, 100),  # 최대 100개
            'start': min(start, 1000),     # 최대 1000
            'sort': sort if sort in ['sim', 'date'] else 'date'  # 기본값을 date(최신순)로 변경
        }
        
        headers = {
            'X-Naver-Client-Id': self.client_id,
            'X-Naver-Client-Secret': self.client_secret,
            'User-Agent': 'NaverSearchClient/1.0'
        }
        try:
            print(f"[NaverNews] 📡 API 호출 중... URL: {url}")
            response = requests.get(url, params=params, headers=headers, timeout=self.timeout_seconds)
            
            if response.status_code == 200:
                data = response.json()
                total_count = data.get('total', 0)
                print(f"[NaverNews] ✅ API 응답 성공 - 총 {total_count}개 뉴스 발견")
                return self._parse_naver_response(data, query, enhanced_query)
            else:
                print(f"[NaverNews] ❌ API 오류 - 상태코드: {response.status_code}")
                raise Exception(f"Naver API Error {response.status_code}: {response.text}")
                            
        except Exception as e:
            print(f"[NaverNews] ❌ 요청 실패: {e}")
            return {
                "query": query,
                "total_count": 0,
                "news": [],
                "error": str(e)
            }
    
    def _calculate_relevance_score(self, title: str, query: str) -> int:
        """제목과 쿼리의 관련성 점수 계산 (높을수록 관련성 높음)"""
        title_lower = title.lower().strip()
        query_lower = query.lower().strip()
        
        score = 0
        print(f"[NaverNews] 📊 관련성 점수 계산 - 제목: '{title[:30]}...' vs 쿼리: '{query}'")
        
        # 1. 완전 쿼리 일치 (최고 점수)
        if query_lower in title_lower:
            score += 200  # 완전 일치는 매우 높은 점수
        
        # 2. 띄어쓰기로 구분된 단어별 스코어링
        query_words = [word.strip() for word in query_lower.split() if word.strip()]
        title_words = [word.strip() for word in title_lower.split() if word.strip()]
        
        if not query_words:
            return score
        
        matched_words = 0
        word_scores = []
        
        for query_word in query_words:
            word_score = 0
            
            # 2-1. 정확한 단어 매치
            if query_word in title_words:
                word_score += 50  # 정확한 단어 매치
                matched_words += 1
            
            # 2-2. 제목에 쿼리 단어가 부분적으로 포함
            elif query_word in title_lower:
                word_score += 30  # 부분 포함
                matched_words += 0.7
            
            # 2-3. 제목 단어 중에 쿼리 단어를 포함하는 것이 있는지
            else:
                for title_word in title_words:
                    if len(query_word) >= 2:
                        # 쿼리 단어가 제목 단어에 포함
                        if query_word in title_word:
                            word_score += 20
                            matched_words += 0.5
                            break
                        # 제목 단어가 쿼리 단어에 포함 (짧은 단어의 경우)
                        elif title_word in query_word and len(title_word) >= 2:
                            word_score += 15
                            matched_words += 0.3
                            break
            
            # 2-4. 단어 길이에 따른 가중치 (긴 단어일수록 중요)
            if word_score > 0:
                length_bonus = min(len(query_word) * 2, 10)  # 최대 10점 보너스
                word_score += length_bonus
            
            word_scores.append(word_score)
        
        # 3. 전체 단어 매치 비율 계산
        total_words = len(query_words)
        match_ratio = matched_words / total_words if total_words > 0 else 0
        
        # 4. 점수 합산
        score += sum(word_scores)
        
        # 5. 매치 비율 보너스
        if match_ratio >= 1.0:  # 모든 단어가 매치됨
            score += 100
        elif match_ratio >= 0.8:  # 80% 이상 매치
            score += 50
        elif match_ratio >= 0.5:  # 50% 이상 매치
            score += 25
        
        # 6. 제목에서 쿼리 단어들이 연속적으로 나타나는 경우 보너스
        if len(query_words) > 1:
            query_phrase = ' '.join(query_words)
            if query_phrase in title_lower:
                score += 80  # 연속 구문 매치 보너스
        
        # 7. 제목 길이 대비 매치 비율 (제목이 짧고 매치가 많을수록 높은 점수)
        if title_words:
            title_relevance = (matched_words / len(title_words)) * 20
            score += int(title_relevance)
        
        print(f"[NaverNews] 📊 최종 관련성 점수: {score}")
        return score

    def _parse_naver_response(self, data: Dict[str, Any], query: str, enhanced_query: str = None) -> Dict[str, Any]:
        """Naver API 응답을 파싱하여 통일된 형식으로 변환"""
        
        news_items = []
        items = data.get('items', [])
        print(f"[NaverNews] 📰 뉴스 파싱 시작 - {len(items)}개 원본 아이템")
        
        # 최근 30일 이내 뉴스만 필터링
        cutoff_date = datetime.now() - timedelta(days=30)
        
        for item in items:
            # HTML 태그 정리
            title = self._clean_html_tags(item.get('title', ''))
            description = self._clean_html_tags(item.get('description', ''))
            
            # 원본 링크 우선, 없으면 네이버 링크 사용
            url = item.get('originallink') or item.get('link', '')
            
            # 날짜 형식 변환
            pub_date = self._format_date(item.get('pubDate', ''))
            
            # 30일 이내 뉴스만 포함 (날짜 파싱이 가능한 경우)
            try:
                news_date = datetime.strptime(pub_date, "%Y-%m-%d")
                if news_date < cutoff_date:
                    continue  # 30일 이상 된 뉴스는 제외
            except:
                pass  # 날짜 파싱 실패시 포함
            
            # 언론사명 추출
            source = self._extract_source_from_url(url)
            
            # 관련성 점수 계산
            relevance_score = self._calculate_relevance_score(title, query)
            
            news_item = {
                "title": title,
                "url": url,
                "source": source,
                "published_date": pub_date,
                "summary": description,
                "relevance_score": relevance_score  # 정렬용 점수
            }
            
            news_items.append(news_item)
        
        print(f"[NaverNews] 🔄 스마트 정렬 시작 - {len(news_items)}개 아이템")
        # 스마트 정렬: 1순위 관련성, 2순위 날짜
        news_items.sort(key=lambda x: (
            -x["relevance_score"],  # 관련성 점수 높은 순
            -self._date_to_timestamp(x["published_date"])  # 날짜 최신 순
        ))
        
        # 정렬 후 상위 3개 아이템의 점수 로깅
        if news_items:
            print(f"[NaverNews] 🏆 상위 3개 뉴스:")
            for i, item in enumerate(news_items[:3]):
                score = item.get("relevance_score", 0)
                title = item.get("title", "")[:50]
                print(f"[NaverNews]   {i+1}위. 점수 {score}: {title}...")
        
        # 정렬 후 relevance_score 제거 (응답에서 제외)
        for item in news_items:
            item.pop("relevance_score", None)
        
        result = {
            "query": query,
            "enhanced_query": enhanced_query or query,
            "total_count": data.get('total', 0),
            "start": data.get('start', 1),
            "display": data.get('display', len(news_items)),
            "filtered_count": len(news_items),  # 실제 필터링된 뉴스 수
            "news": news_items
        }
        
        print(f"[NaverNews] ✅ 파싱 완료 - 총 {result['total_count']}개 중 {result['filtered_count']}개 필터링됨")
        return result
    
    def _date_to_timestamp(self, date_str: str) -> int:
        """날짜 문자열을 타임스탬프로 변환 (정렬용)"""
        try:
            dt = datetime.strptime(date_str, "%Y-%m-%d")
            return int(dt.timestamp())
        except:
            return 0  # 파싱 실패시 0 (가장 오래된 것으로 취급)
    
    def search_general(self, query: str, display: int = 10) -> Dict[str, Any]:
        """일반 검색 (뉴스 외)"""
        if not self.client_id or not self.client_secret:
            return {
                "status": "error",
                "query": query,
                "results": [],
                "error": "Naver API credentials not configured"
            }
        
        # 웹문서 검색 API 사용
        encoded_query = quote(query)
        url = f"{self.base_url}/webkr.json"
        
        params = {
            'query': encoded_query,
            'display': min(display, 100),
            'start': 1
        }
        
        headers = {
            'X-Naver-Client-Id': self.client_id,
            'X-Naver-Client-Secret': self.client_secret,
            'User-Agent': 'NaverSearchClient/1.0'
        }
        
        try:
            response = requests.get(url, params=params, headers=headers, timeout=self.timeout_seconds)
            if response.status_code == 200:
                data = response.json()
                return self._parse_web_response(data, query)
            else:
                raise Exception(f"Naver API Error {response.status_code}: {response.text}")
                            
        except Exception as e:
            return {
                "status": "error",
                "query": query,
                "results": [],
                "error": str(e)
            }
    
    def _parse_web_response(self, data: Dict[str, Any], query: str) -> Dict[str, Any]:
        """웹 검색 응답 파싱"""
        
        results = []
        items = data.get('items', [])
        
        for item in items:
            title = self._clean_html_tags(item.get('title', ''))
            description = self._clean_html_tags(item.get('description', ''))
            url = item.get('link', '')
            
            results.append({
                "title": title,
                "url": url,
                "description": description
            })
        
        return {
            "status": "success",
            "query": query,
            "total_count": data.get('total', 0),
            "results": results
        }


@lru_cache
def get_naver_search_client():
    return NaverSearchClient()


def is_korea_stock(ticker: str):
    """한국 주식 티커인지 확인"""
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
            from pykrx import stock
            ticker_name = stock.get_market_ticker_name(ticker)
            return ticker_name
        except Exception:
            return ""
    else:
        try:
            import yfinance as yf
            ticker_obj = yf.Ticker(ticker)
            info = ticker_obj.info
            # shortName이 있으면 그걸, 없으면 longName, 둘 다 없으면 ""
            return info.get("shortName") or info.get("longName") or ""
        except Exception:
            return ""


def get_naver_news(
    query: str,
    curr_date: str,
    look_back_days: int = 7,
    display: int = 10
) -> str:
    """
    네이버 뉴스 검색 API를 사용한 뉴스 검색 (기존 interface.py 스타일에 맞춤)
    
    Args:
        query: 검색어
        curr_date: 현재 날짜 (yyyy-mm-dd 형식)
        look_back_days: 검색 기간 (기본 7일)
        display: 표시할 뉴스 개수 (기본 10개)
    
    Returns:
        str: 포맷된 뉴스 문자열
    """
    
    print(f"[NaverNews] 🚀 뉴스 검색 함수 시작 - 쿼리: '{query}', 날짜: {curr_date}, 기간: {look_back_days}일")
    
    # 한국 주식의 경우 종목명도 함께 검색
    stock_name = get_stock_name(query)
    if stock_name:
        enhanced_query = f"{stock_name}"
        print(f"[NaverNews] 🏢 한국 주식 인식 - '{query}' → '{stock_name}' 변경")
    else:
        enhanced_query = query
        print(f"[NaverNews] 🌐 일반 검색어로 처리")
    
    client = get_naver_search_client()
    
    # 네이버 뉴스 검색
    news_results = client.search_news(
        query=enhanced_query,
        display=display,
        sort="date"  # 최신순으로 정렬
    )
    
    if news_results.get("error"):
        print(f"[NaverNews] ❌ API 에러: {news_results['error']}")
        return f"Naver News API Error: {news_results['error']}"
    
    news_items = news_results.get("news", [])
    
    if not news_items:
        print(f"[NaverNews] ⚠️  검색 결과 없음")
        return ""
    
    print(f"[NaverNews] 📰 {len(news_items)}개 뉴스 아이템 확보")
    
    # 날짜 필터링 (look_back_days 기간 내)
    start_date = datetime.strptime(curr_date, "%Y-%m-%d")
    before = start_date - timedelta(days=look_back_days)
    before_str = before.strftime("%Y-%m-%d")
    
    print(f"[NaverNews] 📅 날짜 필터링 - {before_str} ~ {curr_date}")
    
    filtered_items = []
    for item in news_items:
        try:
            item_date = datetime.strptime(item["published_date"], "%Y-%m-%d")
            if item_date >= before:
                filtered_items.append(item)
        except:
            # 날짜 파싱 실패시 포함
            filtered_items.append(item)
    
    print(f"[NaverNews] 📊 날짜 필터링 결과 - {len(news_items)}개 → {len(filtered_items)}개")
    
    # 결과 포매팅 (기존 Google News 스타일과 유사하게)
    print(f"[NaverNews] 📝 결과 포매팅 시작")
    news_str = ""
    for i, news in enumerate(filtered_items):
        news_str += (
            f"### {news['title']} (source: {news['source']}) \n\n{news['summary']}\n\n"
        )
        if i == 0:  # 첫 번째 뉴스만 로깅
            print(f"[NaverNews] 📰 첫 번째 뉴스: {news['title'][:50]}...")
    
    if len(filtered_items) == 0:
        print(f"[NaverNews] ❌ 최종 결과 없음")
        return ""
    
    result = f"## {query} Naver News, from {before_str} to {curr_date}:\n\n{news_str}"
    print(f"[NaverNews] ✅ 최종 결과 생성 완료 - {len(result)}자, {len(filtered_items)}개 뉴스")
    return result