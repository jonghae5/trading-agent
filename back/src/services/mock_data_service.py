"""Centralized mock data service for development and testing."""

from typing import Dict, List, Any


class MockDataService:
    """Centralized service for mock stock and market data."""
    
    def __init__(self):
        # Comprehensive stock database - single source of truth
        self.stock_database = {
            # Tech Giants
            'AAPL': {'name': 'Apple Inc.', 'sector': 'Technology', 'exchange': 'NASDAQ', 'type': 'equity', 'market_cap': '3T'},
            'MSFT': {'name': 'Microsoft Corporation', 'sector': 'Technology', 'exchange': 'NASDAQ', 'type': 'equity', 'market_cap': '3T'},
            'GOOGL': {'name': 'Alphabet Inc. Class A', 'sector': 'Technology', 'exchange': 'NASDAQ', 'type': 'equity', 'market_cap': '2T'},
            'GOOG': {'name': 'Alphabet Inc. Class C', 'sector': 'Technology', 'exchange': 'NASDAQ', 'type': 'equity', 'market_cap': '2T'},
            'AMZN': {'name': 'Amazon.com Inc.', 'sector': 'Consumer Cyclical', 'exchange': 'NASDAQ', 'type': 'equity', 'market_cap': '1.5T'},
            'META': {'name': 'Meta Platforms Inc.', 'sector': 'Technology', 'exchange': 'NASDAQ', 'type': 'equity', 'market_cap': '1.3T'},
            'TSLA': {'name': 'Tesla Inc.', 'sector': 'Consumer Cyclical', 'exchange': 'NASDAQ', 'type': 'equity', 'market_cap': '800B'},
            'NVDA': {'name': 'NVIDIA Corporation', 'sector': 'Technology', 'exchange': 'NASDAQ', 'type': 'equity', 'market_cap': '2T'},
            'NFLX': {'name': 'Netflix Inc.', 'sector': 'Communication Services', 'exchange': 'NASDAQ', 'type': 'equity', 'market_cap': '200B'},
            'CRM': {'name': 'Salesforce Inc.', 'sector': 'Technology', 'exchange': 'NYSE', 'type': 'equity', 'market_cap': '250B'},
            
            # Financial Services
            'JPM': {'name': 'JPMorgan Chase & Co.', 'sector': 'Financial Services', 'exchange': 'NYSE', 'type': 'equity', 'market_cap': '600B'},
            'BAC': {'name': 'Bank of America Corporation', 'sector': 'Financial Services', 'exchange': 'NYSE', 'type': 'equity', 'market_cap': '300B'},
            'V': {'name': 'Visa Inc.', 'sector': 'Financial Services', 'exchange': 'NYSE', 'type': 'equity', 'market_cap': '500B'},
            'MA': {'name': 'Mastercard Incorporated', 'sector': 'Financial Services', 'exchange': 'NYSE', 'type': 'equity', 'market_cap': '400B'},
            'WFC': {'name': 'Wells Fargo & Company', 'sector': 'Financial Services', 'exchange': 'NYSE', 'type': 'equity', 'market_cap': '200B'},
            'GS': {'name': 'Goldman Sachs Group Inc.', 'sector': 'Financial Services', 'exchange': 'NYSE', 'type': 'equity', 'market_cap': '150B'},
            'MS': {'name': 'Morgan Stanley', 'sector': 'Financial Services', 'exchange': 'NYSE', 'type': 'equity', 'market_cap': '150B'},
            'BRK.A': {'name': 'Berkshire Hathaway Inc. Class A', 'sector': 'Financial Services', 'exchange': 'NYSE', 'type': 'equity', 'market_cap': '900B'},
            'BRK.B': {'name': 'Berkshire Hathaway Inc. Class B', 'sector': 'Financial Services', 'exchange': 'NYSE', 'type': 'equity', 'market_cap': '900B'},
            
            # Healthcare
            'JNJ': {'name': 'Johnson & Johnson', 'sector': 'Healthcare', 'exchange': 'NYSE', 'type': 'equity', 'market_cap': '400B'},
            'PFE': {'name': 'Pfizer Inc.', 'sector': 'Healthcare', 'exchange': 'NYSE', 'type': 'equity', 'market_cap': '200B'},
            'UNH': {'name': 'UnitedHealth Group Incorporated', 'sector': 'Healthcare', 'exchange': 'NYSE', 'type': 'equity', 'market_cap': '500B'},
            'ABBV': {'name': 'AbbVie Inc.', 'sector': 'Healthcare', 'exchange': 'NYSE', 'type': 'equity', 'market_cap': '300B'},
            'TMO': {'name': 'Thermo Fisher Scientific Inc.', 'sector': 'Healthcare', 'exchange': 'NYSE', 'type': 'equity', 'market_cap': '200B'},
            
            # Consumer Goods
            'KO': {'name': 'The Coca-Cola Company', 'sector': 'Consumer Defensive', 'exchange': 'NYSE', 'type': 'equity', 'market_cap': '250B'},
            'PEP': {'name': 'PepsiCo Inc.', 'sector': 'Consumer Defensive', 'exchange': 'NASDAQ', 'type': 'equity', 'market_cap': '230B'},
            'PG': {'name': 'The Procter & Gamble Company', 'sector': 'Consumer Defensive', 'exchange': 'NYSE', 'type': 'equity', 'market_cap': '400B'},
            'WMT': {'name': 'Walmart Inc.', 'sector': 'Consumer Defensive', 'exchange': 'NYSE', 'type': 'equity', 'market_cap': '600B'},
            'HD': {'name': 'The Home Depot Inc.', 'sector': 'Consumer Cyclical', 'exchange': 'NYSE', 'type': 'equity', 'market_cap': '400B'},
            'NKE': {'name': 'NIKE Inc.', 'sector': 'Consumer Cyclical', 'exchange': 'NYSE', 'type': 'equity', 'market_cap': '200B'},
            'MCD': {'name': 'McDonald\'s Corporation', 'sector': 'Consumer Cyclical', 'exchange': 'NYSE', 'type': 'equity', 'market_cap': '200B'},
            'SBUX': {'name': 'Starbucks Corporation', 'sector': 'Consumer Cyclical', 'exchange': 'NASDAQ', 'type': 'equity', 'market_cap': '100B'},
            
            # ETFs
            'SPY': {'name': 'SPDR S&P 500 ETF Trust', 'sector': 'Diversified', 'exchange': 'ARCA', 'type': 'etf', 'market_cap': '500B'},
            'QQQ': {'name': 'Invesco QQQ Trust', 'sector': 'Technology', 'exchange': 'NASDAQ', 'type': 'etf', 'market_cap': '200B'},
            'VTI': {'name': 'Vanguard Total Stock Market ETF', 'sector': 'Diversified', 'exchange': 'ARCA', 'type': 'etf', 'market_cap': '300B'},
            'VOO': {'name': 'Vanguard S&P 500 ETF', 'sector': 'Diversified', 'exchange': 'NYSE', 'type': 'etf', 'market_cap': '250B'},
            'IWM': {'name': 'iShares Russell 2000 ETF', 'sector': 'Small Cap', 'exchange': 'ARCA', 'type': 'etf', 'market_cap': '60B'},
        }
        
        # Fear & Greed fallback data
        self.fear_greed_fallback = {
            "value": 45,
            "value_classification": "Neutral",
            "timestamp": "2024-01-01T00:00:00Z",
            "previous_close": 42,
            "previous_1_week": 38,
            "previous_1_month": 55,
            "previous_1_year": 48
        }
    
    def get_all_stocks(self) -> Dict[str, Dict[str, Any]]:
        """Get all stock data."""
        return self.stock_database
    
    def search_stocks(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search stocks by ticker or name."""
        query = query.upper().strip()
        results = []
        
        for ticker, data in self.stock_database.items():
            if (query in ticker or 
                query in data["name"].upper() or 
                ticker.startswith(query)):
                results.append({
                    "ticker": ticker,
                    **data
                })
        
        return results[:limit]
    
    def get_stock_by_ticker(self, ticker: str) -> Dict[str, Any] | None:
        """Get stock data by ticker."""
        return self.stock_database.get(ticker.upper())
    
    def get_popular_stocks(self, limit: int = 20) -> List[Dict[str, Any]]:
        """Get popular stocks (first N entries)."""
        stocks = []
        for ticker, data in list(self.stock_database.items())[:limit]:
            stocks.append({
                "ticker": ticker,
                **data
            })
        return stocks
    
    def get_stocks_by_sector(self, sector: str) -> List[Dict[str, Any]]:
        """Get stocks filtered by sector."""
        results = []
        for ticker, data in self.stock_database.items():
            if data["sector"].lower() == sector.lower():
                results.append({
                    "ticker": ticker,
                    **data
                })
        return results
    
    def get_stocks_by_exchange(self, exchange: str) -> List[Dict[str, Any]]:
        """Get stocks filtered by exchange."""
        results = []
        for ticker, data in self.stock_database.items():
            if data["exchange"].lower() == exchange.lower():
                results.append({
                    "ticker": ticker,
                    **data
                })
        return results
    
    def get_fear_greed_data(self) -> Dict[str, Any]:
        """Get mock Fear & Greed index data."""
        return self.fear_greed_fallback


# Global instance
mock_data_service = MockDataService()