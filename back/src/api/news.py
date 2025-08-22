"""News API endpoints for fetching real financial news."""

import logging
from typing import Dict, List, Optional, Any
from fastapi import APIRouter, HTTPException, Query, Depends
from pydantic import BaseModel, Field

from src.core.security import get_current_user
from src.models.user import User
from src.models.base import kst_to_naive
from src.schemas.common import ApiResponse
from src.core.config import get_settings
from src.services.finnhub_service import get_finnhub_service

settings = get_settings()
logger = logging.getLogger(__name__)

router = APIRouter()


class NewsArticle(BaseModel):
    """News article model."""
    id: str
    title: str
    summary: Optional[str] = None
    sentiment: str = Field(..., pattern="^(positive|negative|neutral)$")
    source: str
    published_at: str  # ISO format datetime
    relevance_score: float = Field(..., ge=0.0, le=1.0)
    tags: List[str] = []
    url: Optional[str] = None
    ticker_sentiment: Optional[Dict[str, Any]] = None

class NewsSearchResult(BaseModel):
    """News search result."""
    articles: List[NewsArticle]
    total: int
    has_more: bool
    search_query: Optional[str] = None


class NewsResponse(BaseModel):
    """News categorized response."""
    latest_news: List[NewsArticle]


async def _fetch_news_from_api(limit=20) -> List[NewsArticle]:
    """Fetch real news from FRED service and other financial APIs."""
    articles = []
    
    try:
        finnhub_service = get_finnhub_service()
        
        # Get economic news from FRED service
        raw_articles = await finnhub_service.get_economic_news(limit=20)
        
        # Convert to NewsArticle format (핀허브 포맷에 맞게)
        for i, article in enumerate(raw_articles):
            # Finnhub NewsArticle 객체를 그대로 사용
            news_article = NewsArticle(
                id=article.id if hasattr(article, "id") else f"finnhub-news-{i}",
                title=article.title,
                summary=getattr(article, "description", None),
                sentiment=_determine_sentiment_simple(article.title),
                source=getattr(article, "source", "Finnhub"),
                published_at=kst_to_naive(article.published_at).isoformat() if hasattr(article, "published_at") and article.published_at else "",
                relevance_score=0.8,
                tags=[article.category] if hasattr(article, "category") else ["economic"],
                url=getattr(article, "url", None),
                ticker_sentiment=None
            )
            articles.append(news_article)
        
        logger.info(f"Fetched {len(articles)} news articles from FRED service")

        articles = sorted(articles, key=lambda x: x.published_at, reverse=True)[:limit]
        return articles
        
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        return []


async def _fetch_company_news_from_api(query:str) -> List[NewsArticle]:
    """Fetch real news from FRED service and other financial APIs."""
    articles = []
    
    try:
        finnhub_service = get_finnhub_service()
        
        # Get economic news from FRED service
        raw_articles = await finnhub_service.get_company_news(symbol=query, limit=20)
        
        # Convert to NewsArticle format (핀허브 포맷에 맞게)
        for i, article in enumerate(raw_articles):
            # Finnhub NewsArticle 객체를 그대로 사용
            news_article = NewsArticle(
                id=article.id if hasattr(article, "id") else f"finnhub-news-{i}",
                title=article.title,
                summary=getattr(article, "description", None),
                sentiment=_determine_sentiment_simple(article.title),
                source=getattr(article, "source", "Finnhub"),
                published_at=kst_to_naive(article.published_at).isoformat() if hasattr(article, "published_at") and article.published_at else "",
                relevance_score=0.8,
                tags=[article.category] if hasattr(article, "category") else ["economic"],
                url=getattr(article, "url", None),
                ticker_sentiment=None
            )
            articles.append(news_article)
        
        logger.info(f"Fetched {len(articles)} news articles from FRED service")
        return articles
        
    except Exception as e:
        logger.error(f"Error fetching news: {e}")
        return []

def _determine_sentiment_simple(title: str) -> str:
    """Simple sentiment analysis based on keywords."""
    title_lower = title.lower()
    
    positive_words = ['up', 'rise', 'gain', 'surge', 'rally', 'boost', 'growth', 'profit', 'bull']
    negative_words = ['down', 'fall', 'drop', 'crash', 'decline', 'loss', 'bear', 'recession']
    
    positive_count = sum(1 for word in positive_words if word in title_lower)
    negative_count = sum(1 for word in negative_words if word in title_lower)
    
    if positive_count > negative_count:
        return 'positive'
    elif negative_count > positive_count:
        return 'negative'
    else:
        return 'neutral'



@router.get("", response_model=ApiResponse[NewsResponse])
async def get_news(
    current_user: User = Depends(get_current_user)
):
    """Get financial news."""
    try:
        # Fetch all news articles
        all_articles = await _fetch_news_from_api()
        
        if not all_articles:
            return ApiResponse(
                success=True,
                message="No news available at this time",
                data=NewsResponse(
                    latest_news=[]
                )
            )
        
        return ApiResponse(
            success=True,
            message=f"Successfully fetched {len(all_articles)} news articles",
            data=NewsResponse(
                latest_news=all_articles,
            )
        )
        
    except Exception as e:
        logger.error(f"Error fetching categorized news: {e}")
        return ApiResponse(
            success=False,
            message=f"Failed to fetch news: {str(e)}",
            data=None
        )


def _is_ticker_symbol(query: str) -> bool:
    """Check if query looks like a stock ticker symbol."""
    if not query:
        return False
    
    # Basic ticker symbol validation (1-5 uppercase letters)
    query_upper = query.upper().strip()
    return (len(query_upper) >= 1 and len(query_upper) <= 5 and 
            query_upper.isalpha() and query_upper.isupper())


@router.get("/search", response_model=ApiResponse[NewsSearchResult])
async def search_news(
    query: Optional[str] = Query(None, description="Search query"),
    sentiment: Optional[str] = Query(None, description="Filter by sentiment"),
    limit: int = Query(20, le=100, description="Maximum number of results"),
    current_user: User = Depends(get_current_user)
):
    """Search financial news with filters."""
    try:
        # Fetch all news
        all_news = await _fetch_company_news_from_api(query)
        
        # Apply filters
        filtered_news = all_news
        
        if query:
            query_lower = query.lower()
            filtered_news = [
                article for article in filtered_news
                if (query_lower in article.title.lower() or 
                    (article.summary and query_lower in article.summary.lower()) or
                    any(query_lower in tag.lower() for tag in article.tags))
            ]
        
        if sentiment and sentiment != "all":
            filtered_news = [
                article for article in filtered_news
                if article.sentiment == sentiment
            ]
        
        # Check if query is a ticker symbol and get Finnhub sentiment
        ticker_sentiment_data = None
        if query and _is_ticker_symbol(query):
            try:
                finnhub_service = get_finnhub_service()
                sentiment_data = await finnhub_service.get_news_sentiment(query.upper())
                if sentiment_data:
                    ticker_sentiment_data = {
                        "symbol": sentiment_data.symbol,
                        "mention": sentiment_data.mention,
                        "positive_mention": sentiment_data.positive_mention,
                        "negative_mention": sentiment_data.negative_mention,
                        "positive_score": sentiment_data.positive_score,
                        "negative_score": sentiment_data.negative_score,
                        "compound_score": sentiment_data.compound_score
                    }
                    logger.info(f"Retrieved Finnhub sentiment for ticker {query.upper()}")
            except Exception as e:
                logger.error(f"Error fetching Finnhub sentiment for {query}: {e}")
        
        # Add ticker sentiment to filtered articles if available
        if ticker_sentiment_data:
            for article in filtered_news:
                article.ticker_sentiment = ticker_sentiment_data
        
        # Sort by relevance and limit
        filtered_news.sort(key=lambda x: x.relevance_score, reverse=True)
        total_count = len(filtered_news)
        filtered_news = filtered_news[:limit]
        
        return ApiResponse(
            success=True,
            message=f"Found {total_count} news articles matching your search",
            data=NewsSearchResult(
                articles=filtered_news,
                total=total_count,
                has_more=total_count > limit,
                search_query=query
            )
        )
        
    except Exception as e:
        logger.error(f"Error searching news: {e}")
        return ApiResponse(
            success=False,
            message=f"Search failed: {str(e)}",
            data=NewsSearchResult(
                articles=[],
                total=0,
                has_more=False,
                search_query=query
            )
        )