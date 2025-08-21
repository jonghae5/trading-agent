"""Sentiment analysis service for market and stock sentiment."""

import logging
import asyncio
import aiohttp
import re
from typing import Dict, List, Optional, Any, Tuple
from datetime import datetime, timedelta
from dataclasses import dataclass
import json
import hashlib
from src.models.base import get_kst_now

logger = logging.getLogger(__name__)


@dataclass
class SentimentScore:
    """Sentiment score data."""
    positive: float
    neutral: float
    negative: float
    compound: float  # Overall sentiment score (-1 to 1)
    confidence: float


@dataclass
class NewsArticle:
    """News article data."""
    title: str
    content: str
    source: str
    published_at: datetime
    url: str
    sentiment: SentimentScore
    relevance: float
    impact_score: float


@dataclass
class SentimentAnalysisResult:
    """Complete sentiment analysis result."""
    ticker: str
    timestamp: datetime
    overall_sentiment: SentimentScore
    news_sentiment: SentimentScore
    social_sentiment: SentimentScore
    analyst_sentiment: SentimentScore
    
    # Detailed data
    news_articles: List[NewsArticle]
    sentiment_trend: List[Tuple[datetime, float]]  # Historical sentiment
    
    # Summary metrics
    sentiment_strength: float  # 0-100
    sentiment_consistency: float  # How consistent sentiment is across sources
    market_impact_score: float  # Estimated impact on stock price
    
    # Key insights
    key_positive_factors: List[str]
    key_negative_factors: List[str]
    sentiment_drivers: List[str]


class SentimentAnalysisService:
    """Service for analyzing market and stock sentiment from various sources."""
    
    def __init__(self):
        self.cache = {}
        self.cache_duration = 1800  # 30 minutes
        
        # Sentiment keywords for basic analysis
        self.positive_keywords = {
            'financial': [
                'profit', 'revenue', 'growth', 'earnings', 'beat', 'exceeded',
                'strong', 'robust', 'solid', 'healthy', 'positive', 'optimistic',
                'bullish', 'upgrade', 'outperform', 'buy', 'rally', 'surge',
                'momentum', 'expansion', 'innovation', 'breakthrough', 'success'
            ],
            'market': [
                'rally', 'bull', 'up', 'rise', 'gain', 'advance', 'climb',
                'surge', 'boom', 'recovery', 'rebound', 'strength', 'momentum',
                'optimism', 'confidence', 'stability', 'growth'
            ]
        }
        
        self.negative_keywords = {
            'financial': [
                'loss', 'decline', 'fell', 'drop', 'miss', 'disappointed',
                'weak', 'poor', 'negative', 'bearish', 'downgrade', 'sell',
                'concern', 'risk', 'challenge', 'struggle', 'crisis',
                'bankruptcy', 'debt', 'layoffs', 'cut'
            ],
            'market': [
                'crash', 'bear', 'down', 'fall', 'loss', 'decline', 'plunge',
                'slump', 'recession', 'correction', 'volatility', 'uncertainty',
                'fear', 'panic', 'stress', 'weakness', 'pressure'
            ]
        }
        
        # Impact multipliers based on source credibility
        self.source_credibility = {
            'reuters': 1.0,
            'bloomberg': 1.0,
            'wsj': 0.95,
            'cnbc': 0.9,
            'marketwatch': 0.85,
            'yahoo': 0.7,
            'seeking_alpha': 0.8,
            'motley_fool': 0.6,
            'reddit': 0.4,
            'twitter': 0.3,
            'unknown': 0.5
        }
    
    def _get_cache_key(self, ticker: str, analysis_type: str) -> str:
        """Generate cache key."""
        return f"sentiment_{ticker}_{analysis_type}_{get_kst_now().strftime('%Y%m%d%H%M')}"
    
    def _is_cache_valid(self, cache_time: datetime) -> bool:
        """Check if cache is still valid."""
        return get_kst_now() - cache_time < timedelta(seconds=self.cache_duration)
    
    def analyze_text_sentiment(self, text: str, context: str = 'financial') -> SentimentScore:
        """Analyze sentiment of text using keyword-based approach."""
        try:
            text_lower = text.lower()
            
            # Remove common stop words and normalize
            text_clean = re.sub(r'[^\w\s]', ' ', text_lower)
            words = text_clean.split()
            
            positive_count = 0
            negative_count = 0
            
            # Count positive keywords
            for keyword in self.positive_keywords.get(context, []):
                positive_count += text_lower.count(keyword)
            
            # Count negative keywords
            for keyword in self.negative_keywords.get(context, []):
                negative_count += text_lower.count(keyword)
            
            total_sentiment_words = positive_count + negative_count
            total_words = len(words)
            
            if total_sentiment_words == 0:
                return SentimentScore(
                    positive=0.5,
                    neutral=1.0,
                    negative=0.5,
                    compound=0.0,
                    confidence=0.3  # Low confidence for neutral text
                )
            
            # Calculate scores
            positive_ratio = positive_count / total_sentiment_words if total_sentiment_words > 0 else 0
            negative_ratio = negative_count / total_sentiment_words if total_sentiment_words > 0 else 0
            neutral_ratio = max(0, 1 - positive_ratio - negative_ratio)
            
            # Compound score (simplified)
            compound = (positive_count - negative_count) / max(total_words, 1)
            compound = max(-1.0, min(1.0, compound * 10))  # Scale and clamp
            
            # Confidence based on sentiment word density
            confidence = min(total_sentiment_words / max(total_words, 1) * 2, 1.0)
            
            return SentimentScore(
                positive=positive_ratio,
                neutral=neutral_ratio,
                negative=negative_ratio,
                compound=compound,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Error analyzing text sentiment: {e}")
            return SentimentScore(0.5, 1.0, 0.5, 0.0, 0.1)
    
    def get_source_credibility(self, source: str) -> float:
        """Get credibility score for a news source."""
        source_lower = source.lower()
        
        for key, credibility in self.source_credibility.items():
            if key in source_lower:
                return credibility
        
        return self.source_credibility['unknown']
    
    async def get_mock_news_data(self, ticker: str, days: int = 7) -> List[NewsArticle]:
        """Get mock news data for demonstration purposes."""
        try:
            # In a real implementation, this would fetch from news APIs
            mock_articles = [
                {
                    'title': f'{ticker} Reports Strong Q4 Earnings, Beats Expectations',
                    'content': f'{ticker} announced strong fourth-quarter results, with revenue growth exceeding analyst expectations. The company showed robust performance across all segments.',
                    'source': 'Reuters',
                    'published_at': get_kst_now() - timedelta(hours=2),
                    'url': f'https://reuters.com/markets/{ticker.lower()}-earnings'
                },
                {
                    'title': f'Analysts Upgrade {ticker} to Buy Rating on Growth Prospects',
                    'content': f'Several Wall Street analysts upgraded {ticker} citing strong fundamentals and positive growth outlook for the coming quarters.',
                    'source': 'Bloomberg',
                    'published_at': get_kst_now() - timedelta(hours=6),
                    'url': f'https://bloomberg.com/news/{ticker.lower()}-upgrade'
                },
                {
                    'title': f'Market Concerns Over {ticker} Regulatory Challenges',
                    'content': f'Investors are expressing concerns about potential regulatory challenges facing {ticker}, which could impact future growth plans.',
                    'source': 'CNBC',
                    'published_at': get_kst_now() - timedelta(days=1),
                    'url': f'https://cnbc.com/markets/{ticker.lower()}-regulatory'
                },
                {
                    'title': f'{ticker} Innovation Initiative Drives Positive Sentiment',
                    'content': f'{ticker} unveiled new innovation initiatives that have generated positive reactions from industry experts and investors.',
                    'source': 'MarketWatch',
                    'published_at': get_kst_now() - timedelta(days=2),
                    'url': f'https://marketwatch.com/{ticker.lower()}-innovation'
                }
            ]
            
            # Analyze sentiment for each article
            articles = []
            for article_data in mock_articles:
                sentiment = self.analyze_text_sentiment(
                    article_data['title'] + ' ' + article_data['content']
                )
                
                credibility = self.get_source_credibility(article_data['source'])
                
                article = NewsArticle(
                    title=article_data['title'],
                    content=article_data['content'],
                    source=article_data['source'],
                    published_at=article_data['published_at'],
                    url=article_data['url'],
                    sentiment=sentiment,
                    relevance=0.8 + (hash(ticker) % 20) / 100,  # Mock relevance
                    impact_score=sentiment.compound * credibility
                )
                articles.append(article)
            
            return articles
            
        except Exception as e:
            logger.error(f"Error fetching news data for {ticker}: {e}")
            return []
    
    def calculate_aggregated_sentiment(self, articles: List[NewsArticle]) -> SentimentScore:
        """Calculate aggregated sentiment from multiple articles."""
        if not articles:
            return SentimentScore(0.5, 1.0, 0.5, 0.0, 0.1)
        
        try:
            total_weight = 0
            weighted_positive = 0
            weighted_negative = 0
            weighted_compound = 0
            
            for article in articles:
                # Weight by recency (more recent = higher weight)
                hours_old = (get_kst_now() - article.published_at).total_seconds() / 3600
                recency_weight = max(0.1, 1.0 / (1.0 + hours_old / 24))  # Decay over days
                
                # Weight by credibility and relevance
                credibility = self.get_source_credibility(article.source)
                weight = recency_weight * credibility * article.relevance
                
                total_weight += weight
                weighted_positive += article.sentiment.positive * weight
                weighted_negative += article.sentiment.negative * weight
                weighted_compound += article.sentiment.compound * weight
            
            if total_weight == 0:
                return SentimentScore(0.5, 1.0, 0.5, 0.0, 0.1)
            
            # Calculate weighted averages
            avg_positive = weighted_positive / total_weight
            avg_negative = weighted_negative / total_weight
            avg_neutral = max(0, 1.0 - avg_positive - avg_negative)
            avg_compound = weighted_compound / total_weight
            
            # Confidence based on number of articles and weight distribution
            confidence = min(len(articles) / 10.0, 1.0) * 0.8
            
            return SentimentScore(
                positive=avg_positive,
                neutral=avg_neutral,
                negative=avg_negative,
                compound=avg_compound,
                confidence=confidence
            )
            
        except Exception as e:
            logger.error(f"Error calculating aggregated sentiment: {e}")
            return SentimentScore(0.5, 1.0, 0.5, 0.0, 0.1)
    
    def generate_sentiment_insights(self, articles: List[NewsArticle], 
                                  overall_sentiment: SentimentScore) -> Tuple[List[str], List[str], List[str]]:
        """Generate key insights from sentiment analysis."""
        positive_factors = []
        negative_factors = []
        drivers = []
        
        try:
            # Analyze article titles and content for key themes
            positive_articles = [a for a in articles if a.sentiment.compound > 0.1]
            negative_articles = [a for a in articles if a.sentiment.compound < -0.1]
            
            # Extract positive factors
            for article in positive_articles[:3]:  # Top 3 positive
                if 'earnings' in article.title.lower() or 'beat' in article.title.lower():
                    positive_factors.append("Strong earnings performance")
                elif 'upgrade' in article.title.lower():
                    positive_factors.append("Analyst upgrades")
                elif 'growth' in article.title.lower():
                    positive_factors.append("Growth prospects")
                elif 'innovation' in article.title.lower():
                    positive_factors.append("Innovation initiatives")
            
            # Extract negative factors
            for article in negative_articles[:3]:  # Top 3 negative
                if 'concern' in article.title.lower() or 'challenge' in article.title.lower():
                    negative_factors.append("Market concerns")
                elif 'regulatory' in article.title.lower():
                    negative_factors.append("Regulatory challenges")
                elif 'miss' in article.title.lower():
                    negative_factors.append("Earnings miss")
                elif 'decline' in article.title.lower():
                    negative_factors.append("Performance decline")
            
            # Generate drivers based on sentiment strength
            if overall_sentiment.compound > 0.3:
                drivers.append("Strong positive news flow")
            elif overall_sentiment.compound < -0.3:
                drivers.append("Negative news sentiment")
            
            if overall_sentiment.confidence > 0.7:
                drivers.append("High sentiment consistency")
            elif overall_sentiment.confidence < 0.3:
                drivers.append("Mixed signals from news sources")
            
            # Remove duplicates and limit
            positive_factors = list(set(positive_factors))[:5]
            negative_factors = list(set(negative_factors))[:5]
            drivers = list(set(drivers))[:3]
            
        except Exception as e:
            logger.error(f"Error generating sentiment insights: {e}")
        
        return positive_factors, negative_factors, drivers
    
    def generate_sentiment_trend(self, articles: List[NewsArticle]) -> List[Tuple[datetime, float]]:
        """Generate sentiment trend over time."""
        trend = []
        
        try:
            # Group articles by day
            daily_sentiment = {}
            
            for article in articles:
                date_key = article.published_at.date()
                if date_key not in daily_sentiment:
                    daily_sentiment[date_key] = []
                daily_sentiment[date_key].append(article.sentiment.compound)
            
            # Calculate daily averages
            for date, sentiments in sorted(daily_sentiment.items()):
                avg_sentiment = sum(sentiments) / len(sentiments)
                trend.append((datetime.combine(date, datetime.min.time()), avg_sentiment))
            
            # Fill in missing days with interpolated values
            if len(trend) > 1:
                start_date = trend[0][0].date()
                end_date = trend[-1][0].date()
                
                current_date = start_date
                filled_trend = []
                
                while current_date <= end_date:
                    existing_point = next((t for t in trend if t[0].date() == current_date), None)
                    
                    if existing_point:
                        filled_trend.append(existing_point)
                    else:
                        # Interpolate between nearest points
                        prev_point = max((t for t in trend if t[0].date() < current_date), 
                                       key=lambda x: x[0], default=None)
                        next_point = min((t for t in trend if t[0].date() > current_date), 
                                       key=lambda x: x[0], default=None)
                        
                        if prev_point and next_point:
                            # Linear interpolation
                            ratio = (current_date - prev_point[0].date()).days / (next_point[0].date() - prev_point[0].date()).days
                            interpolated_sentiment = prev_point[1] + ratio * (next_point[1] - prev_point[1])
                            filled_trend.append((datetime.combine(current_date, datetime.min.time()), interpolated_sentiment))
                    
                    current_date += timedelta(days=1)
                
                trend = filled_trend
            
        except Exception as e:
            logger.error(f"Error generating sentiment trend: {e}")
        
        return trend[-7:] if trend else []  # Return last 7 days
    
    async def get_sentiment_analysis(self, ticker: str, days: int = 7) -> SentimentAnalysisResult:
        """Get comprehensive sentiment analysis for a ticker."""
        cache_key = self._get_cache_key(ticker, 'comprehensive')
        
        # Check cache
        if cache_key in self.cache:
            cache_entry = self.cache[cache_key]
            if self._is_cache_valid(cache_entry['timestamp']):
                return cache_entry['result']
        
        try:
            # Get news articles
            articles = await self.get_mock_news_data(ticker, days)
            
            if not articles:
                # Return neutral sentiment if no data
                neutral_sentiment = SentimentScore(0.5, 1.0, 0.5, 0.0, 0.1)
                return SentimentAnalysisResult(
                    ticker=ticker,
                    timestamp=get_kst_now(),
                    overall_sentiment=neutral_sentiment,
                    news_sentiment=neutral_sentiment,
                    social_sentiment=neutral_sentiment,
                    analyst_sentiment=neutral_sentiment,
                    news_articles=[],
                    sentiment_trend=[],
                    sentiment_strength=50.0,
                    sentiment_consistency=0.1,
                    market_impact_score=0.0,
                    key_positive_factors=[],
                    key_negative_factors=[],
                    sentiment_drivers=["Insufficient data"]
                )
            
            # Calculate different sentiment categories
            news_sentiment = self.calculate_aggregated_sentiment(articles)
            
            # Mock social and analyst sentiment (would be from different APIs)
            social_sentiment = SentimentScore(
                positive=news_sentiment.positive * 0.9,
                neutral=news_sentiment.neutral * 1.1,
                negative=news_sentiment.negative * 0.8,
                compound=news_sentiment.compound * 0.85,
                confidence=news_sentiment.confidence * 0.7
            )
            
            analyst_sentiment = SentimentScore(
                positive=news_sentiment.positive * 1.1,
                neutral=news_sentiment.neutral * 0.9,
                negative=news_sentiment.negative * 0.9,
                compound=news_sentiment.compound * 1.15,
                confidence=news_sentiment.confidence * 0.9
            )
            
            # Calculate overall sentiment (weighted average)
            weights = {'news': 0.4, 'social': 0.3, 'analyst': 0.3}
            
            overall_compound = (
                news_sentiment.compound * weights['news'] +
                social_sentiment.compound * weights['social'] +
                analyst_sentiment.compound * weights['analyst']
            )
            
            overall_positive = (
                news_sentiment.positive * weights['news'] +
                social_sentiment.positive * weights['social'] +
                analyst_sentiment.positive * weights['analyst']
            )
            
            overall_negative = (
                news_sentiment.negative * weights['news'] +
                social_sentiment.negative * weights['social'] +
                analyst_sentiment.negative * weights['analyst']
            )
            
            overall_neutral = max(0, 1.0 - overall_positive - overall_negative)
            
            overall_confidence = (
                news_sentiment.confidence * weights['news'] +
                social_sentiment.confidence * weights['social'] +
                analyst_sentiment.confidence * weights['analyst']
            )
            
            overall_sentiment = SentimentScore(
                positive=overall_positive,
                neutral=overall_neutral,
                negative=overall_negative,
                compound=overall_compound,
                confidence=overall_confidence
            )
            
            # Calculate metrics
            sentiment_strength = abs(overall_compound) * 100  # 0-100 scale
            
            # Sentiment consistency (how aligned different sources are)
            sentiment_scores = [news_sentiment.compound, social_sentiment.compound, analyst_sentiment.compound]
            sentiment_variance = sum((s - overall_compound) ** 2 for s in sentiment_scores) / len(sentiment_scores)
            sentiment_consistency = max(0, 1.0 - sentiment_variance)
            
            # Market impact score (sentiment strength * confidence * consistency)
            market_impact_score = sentiment_strength * overall_confidence * sentiment_consistency / 100
            
            # Generate insights
            positive_factors, negative_factors, drivers = self.generate_sentiment_insights(articles, overall_sentiment)
            
            # Generate sentiment trend
            sentiment_trend = self.generate_sentiment_trend(articles)
            
            result = SentimentAnalysisResult(
                ticker=ticker,
                timestamp=get_kst_now(),
                overall_sentiment=overall_sentiment,
                news_sentiment=news_sentiment,
                social_sentiment=social_sentiment,
                analyst_sentiment=analyst_sentiment,
                news_articles=articles,
                sentiment_trend=sentiment_trend,
                sentiment_strength=sentiment_strength,
                sentiment_consistency=sentiment_consistency,
                market_impact_score=market_impact_score,
                key_positive_factors=positive_factors,
                key_negative_factors=negative_factors,
                sentiment_drivers=drivers
            )
            
            # Cache the result
            self.cache[cache_key] = {
                'result': result,
                'timestamp': get_kst_now()
            }
            
            return result
            
        except Exception as e:
            logger.error(f"Error in sentiment analysis for {ticker}: {e}")
            raise


# Global service instance
sentiment_analysis_service = SentimentAnalysisService()


def get_sentiment_analysis_service() -> SentimentAnalysisService:
    """Get the global sentiment analysis service instance."""
    return sentiment_analysis_service