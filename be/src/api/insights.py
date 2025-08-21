"""Advanced insights API endpoints for comprehensive stock analysis."""

import logging
import asyncio
from typing import Optional, Dict, Any, List
from datetime import datetime
from fastapi import APIRouter, Depends, HTTPException, Query, status
from sqlalchemy.orm import Session

from src.core.database import get_db
from src.core.security import User
from src.core.security import get_current_user
from src.services.technical_analysis_service import get_technical_analysis_service
from src.services.fundamental_analysis_service import get_fundamental_analysis_service
from src.services.market_data_service import get_market_data_service
from src.services.fred_service import get_fred_service
from src.services.sentiment_analysis_service import get_sentiment_analysis_service
from src.services.stock_search_service import get_stock_search_service
from src.schemas.common import ApiResponse
from src.models.base import get_kst_now

router = APIRouter()
logger = logging.getLogger(__name__)

# Service instances
technical_service = get_technical_analysis_service()
fundamental_service = get_fundamental_analysis_service()
market_service = get_market_data_service()
fred_service = get_fred_service()
sentiment_service = get_sentiment_analysis_service()
search_service = get_stock_search_service()


@router.get("/technical/{ticker}")
async def get_technical_analysis(
    ticker: str,
    period: str = Query("6mo", description="Analysis period (1mo, 3mo, 6mo, 1y, 2y)"),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive technical analysis for a ticker."""
    try:
        ticker = ticker.upper()
        
        # Validate period
        valid_periods = ["1mo", "3mo", "6mo", "1y", "2y"]
        if period not in valid_periods:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Invalid period. Must be one of: {', '.join(valid_periods)}"
            )
        
        # Get technical analysis - Note: This needs to be converted to sync in the service layer
        analysis = technical_service.get_comprehensive_analysis(ticker, period)
        
        # Convert to dict for JSON response
        result = {
            "ticker": analysis.ticker,
            "timestamp": analysis.timestamp.isoformat(),
            "indicators": [
                {
                    "name": ind.name,
                    "value": ind.value,
                    "signal": ind.signal,
                    "strength": ind.strength,
                    "description": ind.description
                } for ind in analysis.indicators
            ],
            "overall_signal": analysis.overall_signal,
            "confidence": analysis.confidence,
            "support_levels": analysis.support_levels,
            "resistance_levels": analysis.resistance_levels,
            "trend_direction": analysis.trend_direction,
            "volatility": analysis.volatility
        }
        
        logger.info(f"Technical analysis completed for {ticker} (user: {current_user.username})")
        
        return ApiResponse(
            success=True,
            message="Technical analysis completed successfully",
            data=result
        )
        
    except ValueError as e:
        logger.warning(f"Invalid ticker or data not available: {ticker} - {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No data available for ticker {ticker}"
        )
    except Exception as e:
        logger.error(f"Technical analysis failed for {ticker}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Technical analysis failed"
        )


@router.get("/fundamental/{ticker}")
async def get_fundamental_analysis(
    ticker: str,
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive fundamental analysis for a ticker."""
    try:
        ticker = ticker.upper()
        
        # Get fundamental analysis - Note: This needs to be converted to sync in the service layer
        analysis = fundamental_service.get_fundamental_analysis(ticker)
        
        # Convert to dict for JSON response
        result = {
            "ticker": analysis.ticker,
            "company_name": analysis.company_name,
            "timestamp": analysis.timestamp.isoformat(),
            "current_price": analysis.current_price,
            "market_cap": analysis.market_cap,
            "valuation_metrics": [
                {
                    "name": metric.name,
                    "value": metric.value,
                    "fair_value_estimate": metric.fair_value_estimate,
                    "rating": metric.rating,
                    "description": metric.description
                } for metric in analysis.valuation_metrics
            ],
            "financial_ratios": [
                {
                    "name": ratio.name,
                    "value": ratio.value,
                    "industry_avg": ratio.industry_avg,
                    "rating": ratio.rating,
                    "description": ratio.description
                } for ratio in analysis.financial_ratios
            ],
            "growth_metrics": [
                {
                    "name": metric.name,
                    "current_value": metric.current_value,
                    "historical_avg": metric.historical_avg,
                    "trend": metric.trend,
                    "description": metric.description
                } for metric in analysis.growth_metrics
            ],
            "overall_rating": analysis.overall_rating,
            "confidence": analysis.confidence,
            "fair_value": analysis.fair_value,
            "upside_potential": analysis.upside_potential,
            "risk_factors": analysis.risk_factors,
            "strengths": analysis.strengths
        }
        
        logger.info(f"Fundamental analysis completed for {ticker} (user: {current_user.username})")
        
        return ApiResponse(
            success=True,
            message="Fundamental analysis completed successfully",
            data=result
        )
        
    except ValueError as e:
        logger.warning(f"Invalid ticker or data not available: {ticker} - {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No fundamental data available for ticker {ticker}"
        )
    except Exception as e:
        logger.error(f"Fundamental analysis failed for {ticker}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Fundamental analysis failed"
        )


@router.get("/comprehensive/{ticker}")
async def get_comprehensive_insights(
    ticker: str,
    period: str = Query("6mo", description="Technical analysis period"),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive insights combining technical, fundamental, and market analysis."""
    try:
        ticker = ticker.upper()
        
        # Run analyses sequentially - Note: Services need to be converted to sync
        results = {}
        
        # Technical analysis
        try:
            results['technical'] = technical_service.get_comprehensive_analysis(ticker, period)
        except Exception as e:
            logger.warning(f"Failed to get technical data for {ticker}: {e}")
            results['technical'] = None
            
        # Fundamental analysis
        try:
            results['fundamental'] = fundamental_service.get_fundamental_analysis(ticker)
        except Exception as e:
            logger.warning(f"Failed to get fundamental data for {ticker}: {e}")
            results['fundamental'] = None
            
        # Sentiment analysis
        try:
            results['sentiment'] = sentiment_service.get_sentiment_analysis(ticker)
        except Exception as e:
            logger.warning(f"Failed to get sentiment data for {ticker}: {e}")
            results['sentiment'] = None
            
        # Market context
        try:
            results['market_context'] = market_service.get_market_context()
        except Exception as e:
            logger.warning(f"Failed to get market_context data for {ticker}: {e}")
            results['market_context'] = None
            
        # Economic data
        try:
            results['economic_data'] = fred_service.get_economic_summary()
        except Exception as e:
            logger.warning(f"Failed to get economic_data for {ticker}: {e}")
            results['economic_data'] = None
        
        # Combine insights
        technical = results.get('technical')
        fundamental = results.get('fundamental')
        sentiment = results.get('sentiment')
        market_context = results.get('market_context', {})
        economic_data = results.get('economic_data', {})
        
        # Calculate combined signal
        signals = []
        if technical:
            if technical.overall_signal == "bullish":
                signals.append(1)
            elif technical.overall_signal == "bearish":
                signals.append(-1)
            else:
                signals.append(0)
        
        if fundamental:
            if fundamental.overall_rating in ["strong_buy", "buy"]:
                signals.append(1)
            elif fundamental.overall_rating in ["strong_sell", "sell"]:
                signals.append(-1)
            else:
                signals.append(0)
        
        if sentiment:
            if sentiment.overall_sentiment.compound > 0.2:
                signals.append(1)
            elif sentiment.overall_sentiment.compound < -0.2:
                signals.append(-1)
            else:
                signals.append(0)
        
        # Calculate overall signal
        if signals:
            avg_signal = sum(signals) / len(signals)
            if avg_signal > 0.3:
                combined_signal = "bullish"
            elif avg_signal < -0.3:
                combined_signal = "bearish"
            else:
                combined_signal = "neutral"
        else:
            combined_signal = "neutral"
        
        # Calculate combined confidence
        confidences = []
        if technical:
            confidences.append(technical.confidence)
        if fundamental:
            confidences.append(fundamental.confidence)
        if sentiment:
            confidences.append(sentiment.overall_sentiment.confidence * 100)
        
        combined_confidence = sum(confidences) / len(confidences) if confidences else 50
        
        # Create comprehensive result
        result = {
            "ticker": ticker,
            "timestamp": get_kst_now().isoformat(),
            "combined_signal": combined_signal,
            "combined_confidence": combined_confidence,
            "technical_analysis": {
                "overall_signal": technical.overall_signal if technical else None,
                "confidence": technical.confidence if technical else None,
                "trend_direction": technical.trend_direction if technical else None,
                "volatility": technical.volatility if technical else None,
                "key_indicators": [
                    {
                        "name": ind.name,
                        "signal": ind.signal,
                        "strength": ind.strength
                    } for ind in technical.indicators[:5]  # Top 5 indicators
                ] if technical else []
            },
            "fundamental_analysis": {
                "overall_rating": fundamental.overall_rating if fundamental else None,
                "confidence": fundamental.confidence if fundamental else None,
                "fair_value": fundamental.fair_value if fundamental else None,
                "upside_potential": fundamental.upside_potential if fundamental else None,
                "key_strengths": fundamental.strengths[:3] if fundamental else [],
                "key_risks": fundamental.risk_factors[:3] if fundamental else []
            },
            "sentiment_analysis": {
                "overall_sentiment": sentiment.overall_sentiment.compound if sentiment else None,
                "sentiment_strength": sentiment.sentiment_strength if sentiment else None,
                "news_sentiment": sentiment.news_sentiment.compound if sentiment else None,
                "social_sentiment": sentiment.social_sentiment.compound if sentiment else None,
                "key_positive_factors": sentiment.key_positive_factors[:3] if sentiment else [],
                "key_negative_factors": sentiment.key_negative_factors[:3] if sentiment else [],
                "market_impact_score": sentiment.market_impact_score if sentiment else None
            },
            "market_context": {
                "economic_indicators": economic_data,
                "market_sentiment": market_context.get('sentiment', 'neutral')
            }
        }
        
        logger.info(f"Comprehensive analysis completed for {ticker} (user: {current_user.username})")
        
        return ApiResponse(
            success=True,
            message="Comprehensive insights generated successfully",
            data=result
        )
        
    except Exception as e:
        logger.error(f"Comprehensive analysis failed for {ticker}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Comprehensive analysis failed"
        )


@router.get("/economic/summary")
async def get_economic_summary(
    current_user: User = Depends(get_current_user)
):
    """Get economic indicators summary from FRED."""
    try:
        # Get economic summary - Note: Service needs to be converted to sync
        economic_data = fred_service.get_economic_summary()
        
        return ApiResponse(
            success=True,
            message="Economic summary retrieved successfully",
            data=economic_data
        )
        
    except Exception as e:
        logger.error(f"Failed to get economic summary: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve economic data"
        )


@router.get("/economic/detailed")
async def get_detailed_economic_data(
    current_user: User = Depends(get_current_user)
):
    """Get detailed economic data including GDP, employment, inflation, and rates."""
    try:
        # Get detailed economic data sequentially - Note: Services need to be converted to sync
        results = {}
        
        # GDP data
        try:
            results['gdp'] = fred_service.get_gdp_data()
        except Exception as e:
            logger.warning(f"Failed to get gdp data: {e}")
            results['gdp'] = {}
            
        # Employment data
        try:
            results['employment'] = fred_service.get_employment_data()
        except Exception as e:
            logger.warning(f"Failed to get employment data: {e}")
            results['employment'] = {}
            
        # Inflation data
        try:
            results['inflation'] = fred_service.get_inflation_data()
        except Exception as e:
            logger.warning(f"Failed to get inflation data: {e}")
            results['inflation'] = {}
            
        # Interest rates data
        try:
            results['rates'] = fred_service.get_interest_rates_data()
        except Exception as e:
            logger.warning(f"Failed to get rates data: {e}")
            results['rates'] = {}
            
        # Housing data
        try:
            results['housing'] = fred_service.get_housing_data()
        except Exception as e:
            logger.warning(f"Failed to get housing data: {e}")
            results['housing'] = {}
        
        return ApiResponse(
            success=True,
            message="Detailed economic data retrieved successfully",
            data=results
        )
        
    except Exception as e:
        logger.error(f"Failed to get detailed economic data: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve detailed economic data"
        )


@router.get("/market/context")
async def get_market_context(
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive market context including indices, sentiment, and economic data."""
    try:
        # Get market context - Note: Service needs to be converted to sync
        context = market_service.get_market_context()
        
        return ApiResponse(
            success=True,
            message="Market context retrieved successfully",
            data=context
        )
        
    except Exception as e:
        logger.error(f"Failed to get market context: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve market context"
        )


@router.get("/sentiment/{ticker}")
async def get_sentiment_analysis(
    ticker: str,
    days: int = Query(7, description="Number of days to analyze", ge=1, le=30),
    current_user: User = Depends(get_current_user)
):
    """Get comprehensive sentiment analysis for a ticker."""
    try:
        ticker = ticker.upper()
        
        # Get sentiment analysis - Note: Service needs to be converted to sync
        analysis = sentiment_service.get_sentiment_analysis(ticker, days)
        
        # Convert to dict for JSON response
        result = {
            "ticker": analysis.ticker,
            "timestamp": analysis.timestamp.isoformat(),
            "overall_sentiment": {
                "positive": analysis.overall_sentiment.positive,
                "neutral": analysis.overall_sentiment.neutral,
                "negative": analysis.overall_sentiment.negative,
                "compound": analysis.overall_sentiment.compound,
                "confidence": analysis.overall_sentiment.confidence
            },
            "news_sentiment": {
                "positive": analysis.news_sentiment.positive,
                "neutral": analysis.news_sentiment.neutral,
                "negative": analysis.news_sentiment.negative,
                "compound": analysis.news_sentiment.compound,
                "confidence": analysis.news_sentiment.confidence
            },
            "social_sentiment": {
                "positive": analysis.social_sentiment.positive,
                "neutral": analysis.social_sentiment.neutral,
                "negative": analysis.social_sentiment.negative,
                "compound": analysis.social_sentiment.compound,
                "confidence": analysis.social_sentiment.confidence
            },
            "analyst_sentiment": {
                "positive": analysis.analyst_sentiment.positive,
                "neutral": analysis.analyst_sentiment.neutral,
                "negative": analysis.analyst_sentiment.negative,
                "compound": analysis.analyst_sentiment.compound,
                "confidence": analysis.analyst_sentiment.confidence
            },
            "metrics": {
                "sentiment_strength": analysis.sentiment_strength,
                "sentiment_consistency": analysis.sentiment_consistency,
                "market_impact_score": analysis.market_impact_score
            },
            "insights": {
                "key_positive_factors": analysis.key_positive_factors,
                "key_negative_factors": analysis.key_negative_factors,
                "sentiment_drivers": analysis.sentiment_drivers
            },
            "news_articles": [
                {
                    "title": article.title,
                    "source": article.source,
                    "published_at": article.published_at.isoformat(),
                    "sentiment_compound": article.sentiment.compound,
                    "relevance": article.relevance,
                    "impact_score": article.impact_score,
                    "url": article.url
                } for article in analysis.news_articles
            ],
            "sentiment_trend": [
                {
                    "date": date.isoformat(),
                    "sentiment": sentiment
                } for date, sentiment in analysis.sentiment_trend
            ]
        }
        
        logger.info(f"Sentiment analysis completed for {ticker} (user: {current_user.username})")
        
        return ApiResponse(
            success=True,
            message="Sentiment analysis completed successfully",
            data=result
        )
        
    except ValueError as e:
        logger.warning(f"Invalid ticker or data not available: {ticker} - {e}")
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail=f"No sentiment data available for ticker {ticker}"
        )
    except Exception as e:
        logger.error(f"Sentiment analysis failed for {ticker}: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Sentiment analysis failed"
        )


@router.get("/screener/value")
async def value_screener(
    min_market_cap: Optional[float] = Query(None, description="Minimum market cap in billions"),
    max_pe_ratio: Optional[float] = Query(25, description="Maximum P/E ratio"),
    min_dividend_yield: Optional[float] = Query(None, description="Minimum dividend yield"),
    current_user: User = Depends(get_current_user)
):
    """Screen for value stocks based on fundamental criteria."""
    try:
        # This would integrate with a stock screener API or database
        # For now, return a sample response
        
        screener_results = {
            "criteria": {
                "min_market_cap": min_market_cap,
                "max_pe_ratio": max_pe_ratio,
                "min_dividend_yield": min_dividend_yield
            },
            "results": [
                {
                    "ticker": "JNJ",
                    "company_name": "Johnson & Johnson",
                    "pe_ratio": 15.8,
                    "dividend_yield": 2.9,
                    "market_cap": 445.2,
                    "score": 8.5
                },
                {
                    "ticker": "PG",
                    "company_name": "Procter & Gamble",
                    "pe_ratio": 24.1,
                    "dividend_yield": 2.4,
                    "market_cap": 368.7,
                    "score": 7.8
                }
            ],
            "total_matches": 2,
            "timestamp": get_kst_now().isoformat()
        }
        
        return ApiResponse(
            success=True,
            message="Value screening completed",
            data=screener_results
        )
        
    except Exception as e:
        logger.error(f"Value screening failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Value screening failed"
        )


@router.get("/portfolio/analysis")
async def analyze_portfolio(
    tickers: str = Query(..., description="Comma-separated list of tickers"),
    current_user: User = Depends(get_current_user)
):
    """Analyze a portfolio of stocks for risk, correlation, and optimization."""
    try:
        ticker_list = [t.strip().upper() for t in tickers.split(",") if t.strip()]
        
        if len(ticker_list) > 20:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Maximum 20 tickers allowed"
            )
        
        # Get analysis for each ticker - Note: Services need to be converted to sync
        analyses = []
        for ticker in ticker_list:
            try:
                technical = technical_service.get_comprehensive_analysis(ticker, "6mo")
                fundamental = fundamental_service.get_fundamental_analysis(ticker)
                
                analyses.append({
                    "ticker": ticker,
                    "technical": technical,
                    "fundamental": fundamental
                })
            except Exception as e:
                logger.warning(f"Failed to analyze {ticker}: {e}")
        
        if not analyses:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="No valid ticker data found"
            )
        
        # Calculate portfolio metrics
        portfolio_signals = []
        portfolio_volatilities = []
        
        for analysis in analyses:
            technical = analysis.get('technical')
            if technical:
                if technical.overall_signal == "bullish":
                    portfolio_signals.append(1)
                elif technical.overall_signal == "bearish":
                    portfolio_signals.append(-1)
                else:
                    portfolio_signals.append(0)
                
                portfolio_volatilities.append(technical.volatility)
        
        # Calculate portfolio-level metrics
        avg_signal = sum(portfolio_signals) / len(portfolio_signals) if portfolio_signals else 0
        avg_volatility = sum(portfolio_volatilities) / len(portfolio_volatilities) if portfolio_volatilities else 0
        
        result = {
            "tickers": ticker_list,
            "analysis_count": len(analyses),
            "portfolio_metrics": {
                "average_signal": avg_signal,
                "average_volatility": avg_volatility,
                "diversification_score": min(len(analyses) * 10, 100),  # Simple score based on count
                "risk_level": "high" if avg_volatility > 30 else "medium" if avg_volatility > 15 else "low"
            },
            "individual_analyses": [
                {
                    "ticker": analysis["ticker"],
                    "technical_signal": analysis["technical"].overall_signal if analysis.get("technical") else None,
                    "fundamental_rating": analysis["fundamental"].overall_rating if analysis.get("fundamental") else None,
                    "volatility": analysis["technical"].volatility if analysis.get("technical") else None,
                    "upside_potential": analysis["fundamental"].upside_potential if analysis.get("fundamental") else None
                } for analysis in analyses
            ],
            "timestamp": get_kst_now().isoformat()
        }
        
        logger.info(f"Portfolio analysis completed for {len(ticker_list)} tickers (user: {current_user.username})")
        
        return ApiResponse(
            success=True,
            message="Portfolio analysis completed successfully",
            data=result
        )
        
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Portfolio analysis failed: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Portfolio analysis failed"
        )


@router.get("/search/stocks")
async def search_stocks(
    q: str = Query(..., description="Search query for stock tickers or company names"),
    limit: int = Query(10, description="Maximum number of results", ge=1, le=50)
):  # Public endpoint - no authentication
    """Search for stocks by ticker or company name."""
    try:
        if not q or len(q.strip()) < 1:
            # Return popular stocks if no query - Note: Service needs to be converted to sync
            results = search_service.get_popular_stocks(limit)
        else:
            # Search for stocks - Note: Service needs to be converted to sync
            results = await search_service.search_stocks(q.strip(), limit)
        
        # Convert results to dict
        search_results = [
            {
                "symbol": result.symbol,
                "name": result.name,
                "exchange": result.exchange,
                "type": result.type,
                "sector": result.sector,
                "industry": result.industry,
                "market_cap": result.market_cap,
                "currency": result.currency
            } for result in results
        ]
        
        logger.info(f"Stock search completed for query '{q}' - {len(search_results)} results")
        
        return ApiResponse(
            success=True,
            message="Stock search completed successfully",
            data={
                "query": q,
                "results": search_results,
                "count": len(search_results)
            }
        )
        
    except Exception as e:
        logger.error(f"Stock search failed for query '{q}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Stock search failed"
        )


@router.get("/search/validate/{ticker}")
async def validate_stock_ticker(
    ticker: str
):  # Public endpoint - no authentication
    """Validate if a stock ticker exists and get basic info."""
    try:
        ticker = ticker.upper().strip()
        
        # Validate ticker - Note: Service needs to be converted to sync
        is_valid = search_service.validate_ticker(ticker)
        
        if not is_valid:
            return ApiResponse(
                success=False,
                message=f"Ticker '{ticker}' is not valid or not found",
                data={
                    "ticker": ticker,
                    "valid": False,
                    "info": None
                }
            )
        
        # Get stock info - Note: Service needs to be converted to sync
        stock_info = search_service.get_stock_info(ticker)
        
        result = {
            "ticker": ticker,
            "valid": True,
            "info": {
                "symbol": stock_info.symbol,
                "name": stock_info.name,
                "exchange": stock_info.exchange,
                "type": stock_info.type,
                "sector": stock_info.sector,
                "industry": stock_info.industry,
                "market_cap": stock_info.market_cap,
                "currency": stock_info.currency
            } if stock_info else None
        }
        
        logger.info(f"Ticker validation completed for '{ticker}' - valid: {is_valid}")
        
        return ApiResponse(
            success=True,
            message=f"Ticker '{ticker}' validation completed",
            data=result
        )
        
    except Exception as e:
        logger.error(f"Ticker validation failed for '{ticker}': {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Ticker validation failed"
        )


@router.get("/search/popular")
async def get_popular_stocks(
    limit: int = Query(20, description="Number of popular stocks to return", ge=1, le=50)
):  # Public endpoint - no authentication
    """Get list of popular stocks for quick selection."""
    try:
        results = await search_service.get_popular_stocks(limit)
        
        # Convert results to dict
        popular_stocks = [
            {
                "symbol": result.symbol,
                "name": result.name,
                "exchange": result.exchange,
                "type": result.type,
                "sector": result.sector,
                "industry": result.industry,
                "market_cap": result.market_cap,
                "currency": result.currency
            } for result in results
        ]
        
        logger.info(f"Popular stocks list retrieved - {len(popular_stocks)} stocks")
        
        return ApiResponse(
            success=True,
            message="Popular stocks retrieved successfully",
            data={
                "results": popular_stocks,
                "count": len(popular_stocks)
            }
        )
        
    except Exception as e:
        logger.error(f"Failed to get popular stocks: {e}", exc_info=True)
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Failed to retrieve popular stocks"
        )