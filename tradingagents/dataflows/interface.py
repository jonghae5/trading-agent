from typing import Annotated, Dict
from .reddit_utils import fetch_top_from_category
from .yfin_utils import *
from .stockstats_utils import *
from .googlenews_utils import *
from .finnhub_utils import get_data_in_range, fetch_company_news_online, fetch_insider_sentiment_online, fetch_insider_transactions_online, fetch_balance_sheet_online, fetch_income_statement_online, fetch_cash_flow_online
from dateutil.relativedelta import relativedelta
from concurrent.futures import ThreadPoolExecutor
from datetime import datetime
import json
import os
import pandas as pd
from tqdm import tqdm
import yfinance as yf
from openai import OpenAI
from .config import get_config, set_config, DATA_DIR


def get_finnhub_news(
    ticker: Annotated[
        str,
        "Search query of a company's, e.g. 'AAPL, TSM, etc.",
    ],
    curr_date: Annotated[str, "Current date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "how many days to look back"],
):
    """
    Retrieve news about a company within a time frame using Finnhub API

    Args
        ticker (str): ticker for the company you are interested in
        curr_date (str): Current date in yyyy-mm-dd format
        look_back_days (int): how many days to look back
    Returns
        str: formatted string containing the news of the company in the time frame

    """

    start_date = datetime.strptime(curr_date, "%Y-%m-%d")
    before = start_date - relativedelta(days=look_back_days)
    before = before.strftime("%Y-%m-%d")

    result = fetch_company_news_online(ticker, before, curr_date)
    
    if len(result) == 0:
        return ""

    combined_result = ""
    for entry in result:
        headline = entry.get("headline", "No headline")
        summary = entry.get("summary", "No summary")
        publish_date = datetime.fromtimestamp(entry.get("datetime", 0)).strftime("%Y-%m-%d") if entry.get("datetime") else "Unknown date"
        
        current_news = (
            "### " + headline + f" ({publish_date})" + "\n" + summary
        )
        combined_result += current_news + "\n\n"

    return f"## {ticker} News, from {before} to {curr_date}:\n" + str(combined_result)


def get_finnhub_company_insider_sentiment(
    ticker: Annotated[str, "ticker symbol for the company"],
    curr_date: Annotated[
        str,
        "current date of you are trading at, yyyy-mm-dd",
    ],
    look_back_days: Annotated[int, "number of days to look back"],
):
    """
    Retrieve insider sentiment about a company using Finnhub API (retrieved from public SEC information)
    Args:
        ticker (str): ticker symbol of the company
        curr_date (str): current date you are trading on, yyyy-mm-dd
        look_back_days (int): number of days to look back
    Returns:
        str: a report of the sentiment data
    """

    date_obj = datetime.strptime(curr_date, "%Y-%m-%d")
    before = date_obj - relativedelta(days=look_back_days)
    before = before.strftime("%Y-%m-%d")

    data = fetch_insider_sentiment_online(ticker, before, curr_date)
    
    if len(data) == 0:
        return ""

    result_str = ""
    seen_dicts = []
    for entry in data:
        if entry not in seen_dicts:
            year = entry.get('year', 'Unknown')
            month = entry.get('month', 'Unknown') 
            change = entry.get('change', 'Unknown')
            mspr = entry.get('mspr', 'Unknown')
            
            result_str += f"### {year}-{month}:\nChange: {change}\nMonthly Share Purchase Ratio: {mspr}\n\n"
            seen_dicts.append(entry)

    return (
        f"## {ticker} Insider Sentiment Data for {before} to {curr_date}:\n"
        + result_str
        + "The change field refers to the net buying/selling from all insiders' transactions. The mspr field refers to monthly share purchase ratio."
    )


def get_finnhub_company_insider_transactions(
    ticker: Annotated[str, "ticker symbol"],
    curr_date: Annotated[
        str,
        "current date you are trading at, yyyy-mm-dd",
    ],
    look_back_days: Annotated[int, "how many days to look back"],
):
    """
    Retrieve insider transaction information about a company using Finnhub API (retrieved from public SEC information)
    Args:
        ticker (str): ticker symbol of the company
        curr_date (str): current date you are trading at, yyyy-mm-dd
        look_back_days (int): how many days to look back
    Returns:
        str: a report of the company's insider transaction/trading information
    """

    date_obj = datetime.strptime(curr_date, "%Y-%m-%d")
    before = date_obj - relativedelta(days=look_back_days)
    before = before.strftime("%Y-%m-%d")

    data = fetch_insider_transactions_online(ticker, before, curr_date)
    
    if len(data) == 0:
        return ""

    result_str = ""
    seen_dicts = []
    for entry in data:
        if entry not in seen_dicts:
            filing_date = entry.get('filingDate', 'Unknown')
            name = entry.get('name', 'Unknown')
            change = entry.get('change', 'Unknown')
            share = entry.get('share', 'Unknown')
            transaction_price = entry.get('transactionPrice', 'Unknown')
            transaction_code = entry.get('transactionCode', 'Unknown')
            
            result_str += f"### Filing Date: {filing_date}, {name}:\nChange:{change}\nShares: {share}\nTransaction Price: {transaction_price}\nTransaction Code: {transaction_code}\n\n"
            seen_dicts.append(entry)

    return (
        f"## {ticker} insider transactions from {before} to {curr_date}:\n"
        + result_str
        + "The change field reflects the variation in share count—here a negative number indicates a reduction in holdings—while share specifies the total number of shares involved. The transactionPrice denotes the per-share price at which the trade was executed, and transactionDate marks when the transaction occurred. The name field identifies the insider making the trade, and transactionCode (e.g., S for sale) clarifies the nature of the transaction. FilingDate records when the transaction was officially reported, and the unique id links to the specific SEC filing, as indicated by the source. Additionally, the symbol ties the transaction to a particular company, isDerivative flags whether the trade involves derivative securities, and currency notes the currency context of the transaction."
    )


def get_simfin_balance_sheet(
    ticker: Annotated[str, "ticker symbol"],
    freq: Annotated[
        str,
        "reporting frequency of the company's financial history: annual / quarterly",
    ],
    curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
):
    """
    Retrieve balance sheet data for a company using online Finnhub API
    
    Args:
        ticker (str): ticker symbol of the company
        freq (str): reporting frequency - "annual" or "quarterly"
        curr_date (str): current date you are trading at, yyyy-mm-dd
    
    Returns:
        str: formatted balance sheet data
    """
    # curr_date를 to_date로 사용하여 해당 날짜 이전의 재무제표만 가져오기
    data = fetch_balance_sheet_online(ticker, freq, to_date=curr_date)
    
    if not data or 'data' not in data:
        return f"No balance sheet data available for {ticker}"
    
    # Get the most recent report
    reports = data['data']
    if not reports:
        return f"No {freq} balance sheet reports found for {ticker}"
    
    latest_report = reports[0]  # Reports are typically ordered by date (most recent first)
    
    # Extract balance sheet information
    report_date = latest_report.get('filedDate', 'Unknown')
    period = latest_report.get('period', 'Unknown')
    year = latest_report.get('year', 'Unknown')
    
    result_str = f"## {freq.title()} Balance Sheet for {ticker} (Period: {period}, Year: {year}, Filed: {report_date}):\n\n"
    
    # Extract balance sheet data from the report
    if 'report' in latest_report and 'bs' in latest_report['report']:
        bs_data = latest_report['report']['bs']
        
        # Group the data by categories
        assets = {}
        liabilities = {}
        equity = {}
        
        for item in bs_data:
            concept = item.get('concept', '')
            value = item.get('value', 0)
            unit = item.get('unit', '')
            
            # Categorize based on common balance sheet concepts
            if any(keyword in concept.lower() for keyword in ['asset', 'cash', 'inventory', 'receivable', 'investment']):
                assets[concept] = f"{value:,} {unit}" if isinstance(value, (int, float)) else str(value)
            elif any(keyword in concept.lower() for keyword in ['liability', 'debt', 'payable', 'accrued']):
                liabilities[concept] = f"{value:,} {unit}" if isinstance(value, (int, float)) else str(value)
            elif any(keyword in concept.lower() for keyword in ['equity', 'capital', 'retained', 'stockholder']):
                equity[concept] = f"{value:,} {unit}" if isinstance(value, (int, float)) else str(value)
        
        # Format the output
        if assets:
            result_str += "### Assets:\n"
            for concept, value in assets.items():
                result_str += f"- {concept}: {value}\n"
            result_str += "\n"
        
        if liabilities:
            result_str += "### Liabilities:\n"
            for concept, value in liabilities.items():
                result_str += f"- {concept}: {value}\n"
            result_str += "\n"
        
        if equity:
            result_str += "### Equity:\n"
            for concept, value in equity.items():
                result_str += f"- {concept}: {value}\n"
            result_str += "\n"
    else:
        result_str += "Balance sheet details not available in the expected format.\n"
    
    result_str += "\nThis balance sheet shows the company's financial position, including assets (what the company owns), liabilities (what it owes), and equity (shareholders' ownership). The fundamental accounting equation Assets = Liabilities + Equity must balance."
    
    return result_str


def get_simfin_cashflow(
    ticker: Annotated[str, "ticker symbol"],
    freq: Annotated[
        str,
        "reporting frequency of the company's financial history: annual / quarterly",
    ],
    curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
):
    """
    Retrieve cash flow statement data for a company using online Finnhub API
    
    Args:
        ticker (str): ticker symbol of the company
        freq (str): reporting frequency - "annual" or "quarterly"
        curr_date (str): current date you are trading at, yyyy-mm-dd
    
    Returns:
        str: formatted cash flow statement data
    """
    # curr_date를 to_date로 사용하여 해당 날짜 이전의 현금흐름표만 가져오기
    data = fetch_cash_flow_online(ticker, freq, to_date=curr_date)
    
    if not data or 'data' not in data:
        return f"No cash flow data available for {ticker}"
    
    # Get the most recent report
    reports = data['data']
    if not reports:
        return f"No {freq} cash flow reports found for {ticker}"
    
    latest_report = reports[0]  # Reports are typically ordered by date (most recent first)
    
    # Extract cash flow information
    report_date = latest_report.get('filedDate', 'Unknown')
    period = latest_report.get('period', 'Unknown')
    year = latest_report.get('year', 'Unknown')
    
    result_str = f"## {freq.title()} Cash Flow Statement for {ticker} (Period: {period}, Year: {year}, Filed: {report_date}):\n\n"
    
    # Extract cash flow data from the report
    if 'report' in latest_report and 'cf' in latest_report['report']:
        cf_data = latest_report['report']['cf']
        
        # Group the data by categories
        operating = {}
        investing = {}
        financing = {}
        other = {}
        
        for item in cf_data:
            concept = item.get('concept', '')
            value = item.get('value', 0)
            unit = item.get('unit', '')
            
            # Categorize based on common cash flow concepts
            if any(keyword in concept.lower() for keyword in ['operating', 'depreciation', 'working']):
                operating[concept] = f"{value:,} {unit}" if isinstance(value, (int, float)) else str(value)
            elif any(keyword in concept.lower() for keyword in ['investing', 'investment', 'acquisition', 'disposal']):
                investing[concept] = f"{value:,} {unit}" if isinstance(value, (int, float)) else str(value)
            elif any(keyword in concept.lower() for keyword in ['financing', 'debt', 'dividend', 'share', 'stock']):
                financing[concept] = f"{value:,} {unit}" if isinstance(value, (int, float)) else str(value)
            else:
                other[concept] = f"{value:,} {unit}" if isinstance(value, (int, float)) else str(value)
        
        # Format the output
        if operating:
            result_str += "### Operating Activities:\n"
            for concept, value in operating.items():
                result_str += f"- {concept}: {value}\n"
            result_str += "\n"
        
        if investing:
            result_str += "### Investing Activities:\n"
            for concept, value in investing.items():
                result_str += f"- {concept}: {value}\n"
            result_str += "\n"
        
        if financing:
            result_str += "### Financing Activities:\n"
            for concept, value in financing.items():
                result_str += f"- {concept}: {value}\n"
            result_str += "\n"
        
        if other:
            result_str += "### Other Items:\n"
            for concept, value in other.items():
                result_str += f"- {concept}: {value}\n"
            result_str += "\n"
    else:
        result_str += "Cash flow statement details not available in the expected format.\n"
    
    result_str += "\nThis cash flow statement shows how cash moves in and out of the company through operating activities (core business), investing activities (asset purchases/sales), and financing activities (debt, equity, dividends)."
    
    return result_str


def get_simfin_income_statements(
    ticker: Annotated[str, "ticker symbol"],
    freq: Annotated[
        str,
        "reporting frequency of the company's financial history: annual / quarterly",
    ],
    curr_date: Annotated[str, "current date you are trading at, yyyy-mm-dd"],
):
    """
    Retrieve income statement data for a company using online Finnhub API
    
    Args:
        ticker (str): ticker symbol of the company
        freq (str): reporting frequency - "annual" or "quarterly"
        curr_date (str): current date you are trading at, yyyy-mm-dd
    
    Returns:
        str: formatted income statement data
    """
    # curr_date를 to_date로 사용하여 해당 날짜 이전의 손익계산서만 가져오기
    data = fetch_income_statement_online(ticker, freq, to_date=curr_date)
    
    if not data or 'data' not in data:
        return f"No income statement data available for {ticker}"
    
    # Get the most recent report
    reports = data['data']
    if not reports:
        return f"No {freq} income statement reports found for {ticker}"
    
    latest_report = reports[0]  # Reports are typically ordered by date (most recent first)
    
    # Extract income statement information
    report_date = latest_report.get('filedDate', 'Unknown')
    period = latest_report.get('period', 'Unknown')
    year = latest_report.get('year', 'Unknown')
    
    result_str = f"## {freq.title()} Income Statement for {ticker} (Period: {period}, Year: {year}, Filed: {report_date}):\n\n"
    
    # Extract income statement data from the report
    if 'report' in latest_report and 'ic' in latest_report['report']:
        ic_data = latest_report['report']['ic']
        
        # Group the data by categories
        revenue = {}
        expenses = {}
        other_income = {}
        
        for item in ic_data:
            concept = item.get('concept', '')
            value = item.get('value', 0)
            unit = item.get('unit', '')
            
            # Categorize based on common income statement concepts
            if any(keyword in concept.lower() for keyword in ['revenue', 'sales', 'income']):
                if not any(keyword in concept.lower() for keyword in ['expense', 'cost', 'loss']):
                    revenue[concept] = f"{value:,} {unit}" if isinstance(value, (int, float)) else str(value)
            elif any(keyword in concept.lower() for keyword in ['expense', 'cost', 'depreciation', 'amortization']):
                expenses[concept] = f"{value:,} {unit}" if isinstance(value, (int, float)) else str(value)
            else:
                other_income[concept] = f"{value:,} {unit}" if isinstance(value, (int, float)) else str(value)
        
        # Format the output
        if revenue:
            result_str += "### Revenue & Income:\n"
            for concept, value in revenue.items():
                result_str += f"- {concept}: {value}\n"
            result_str += "\n"
        
        if expenses:
            result_str += "### Expenses & Costs:\n"
            for concept, value in expenses.items():
                result_str += f"- {concept}: {value}\n"
            result_str += "\n"
        
        if other_income:
            result_str += "### Other Items:\n"
            for concept, value in other_income.items():
                result_str += f"- {concept}: {value}\n"
            result_str += "\n"
    else:
        result_str += "Income statement details not available in the expected format.\n"
    
    result_str += "\nThis income statement shows the company's financial performance over a specific period, including revenues (money earned), expenses (costs incurred), and net income (profit or loss)."
    
    return result_str


def get_google_news(
    query: Annotated[str, "Query to search with"],
    curr_date: Annotated[str, "Curr date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "how many days to look back"],
) -> str:
    query = query.replace(" ", "+")

    start_date = datetime.strptime(curr_date, "%Y-%m-%d")
    before = start_date - relativedelta(days=look_back_days)
    before = before.strftime("%Y-%m-%d")

    news_results = getNewsData(query, before, curr_date)

    news_str = ""

    for news in news_results:
        news_str += (
            f"### {news['title']} (source: {news['source']}) \n\n{news['snippet']}\n\n"
        )

    if len(news_results) == 0:
        return ""

    return f"## {query} Google News, from {before} to {curr_date}:\n\n{news_str}"


def get_reddit_global_news(
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "how many days to look back"],
    max_limit_per_day: Annotated[int, "Maximum number of news per day"],
) -> str:
    """
    Retrieve the latest top reddit news
    Args:
        start_date: Start date in yyyy-mm-dd format
        end_date: End date in yyyy-mm-dd format
    Returns:
        str: A formatted dataframe containing the latest news articles posts on reddit and meta information in these columns: "created_utc", "id", "title", "selftext", "score", "num_comments", "url"
    """

    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    before = start_date - relativedelta(days=look_back_days)
    before = before.strftime("%Y-%m-%d")

    posts = []
    # iterate from start_date to end_date
    curr_date = datetime.strptime(before, "%Y-%m-%d")

    total_iterations = (start_date - curr_date).days + 1
    pbar = tqdm(desc=f"Getting Global News on {start_date}", total=total_iterations)

    while curr_date <= start_date:
        curr_date_str = curr_date.strftime("%Y-%m-%d")
        fetch_result = fetch_top_from_category(
            "global_news",
            curr_date_str,
            max_limit_per_day,
            data_path=os.path.join(DATA_DIR, "reddit_data"),
        )
        posts.extend(fetch_result)
        curr_date += relativedelta(days=1)
        pbar.update(1)

    pbar.close()

    if len(posts) == 0:
        return ""

    news_str = ""
    for post in posts:
        if post["content"] == "":
            news_str += f"### {post['title']}\n\n"
        else:
            news_str += f"### {post['title']}\n\n{post['content']}\n\n"

    return f"## Global News Reddit, from {before} to {curr_date}:\n{news_str}"


def get_reddit_company_news(
    ticker: Annotated[str, "ticker symbol of the company"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "how many days to look back"],
    max_limit_per_day: Annotated[int, "Maximum number of news per day"],
) -> str:
    """
    Retrieve the latest top reddit news
    Args:
        ticker: ticker symbol of the company
        start_date: Start date in yyyy-mm-dd format
        end_date: End date in yyyy-mm-dd format
    Returns:
        str: A formatted dataframe containing the latest news articles posts on reddit and meta information in these columns: "created_utc", "id", "title", "selftext", "score", "num_comments", "url"
    """

    start_date = datetime.strptime(start_date, "%Y-%m-%d")
    before = start_date - relativedelta(days=look_back_days)
    before = before.strftime("%Y-%m-%d")

    posts = []
    # iterate from start_date to end_date
    curr_date = datetime.strptime(before, "%Y-%m-%d")

    total_iterations = (start_date - curr_date).days + 1
    pbar = tqdm(
        desc=f"Getting Company News for {ticker} on {start_date}",
        total=total_iterations,
    )

    while curr_date <= start_date:
        curr_date_str = curr_date.strftime("%Y-%m-%d")
        fetch_result = fetch_top_from_category(
            "company_news",
            curr_date_str,
            max_limit_per_day,
            ticker,
            data_path=os.path.join(DATA_DIR, "reddit_data"),
        )
        posts.extend(fetch_result)
        curr_date += relativedelta(days=1)

        pbar.update(1)

    pbar.close()

    if len(posts) == 0:
        return ""

    news_str = ""
    for post in posts:
        if post["content"] == "":
            news_str += f"### {post['title']}\n\n"
        else:
            news_str += f"### {post['title']}\n\n{post['content']}\n\n"

    return f"##{ticker} News Reddit, from {before} to {curr_date}:\n\n{news_str}"


def get_stock_stats_indicators_window(
    symbol: Annotated[str, "ticker symbol of the company"],
    indicator: Annotated[str, "technical indicator to get the analysis and report of"],
    curr_date: Annotated[
        str, "The current trading date you are trading on, YYYY-mm-dd"
    ],
    look_back_days: Annotated[int, "how many days to look back"],
    online: Annotated[bool, "to fetch data online or offline"],
) -> str:

    best_ind_params = {
        # Moving Averages
        "close_50_sma": (
            "50 SMA: A medium-term trend indicator. "
            "Usage: Identify trend direction and serve as dynamic support/resistance. "
            "Tips: It lags price; combine with faster indicators for timely signals."
        ),
        "close_200_sma": (
            "200 SMA: A long-term trend benchmark. "
            "Usage: Confirm overall market trend and identify golden/death cross setups. "
            "Tips: It reacts slowly; best for strategic trend confirmation rather than frequent trading entries."
        ),
        "close_10_ema": (
            "10 EMA: A responsive short-term average. "
            "Usage: Capture quick shifts in momentum and potential entry points. "
            "Tips: Prone to noise in choppy markets; use alongside longer averages for filtering false signals."
        ),
        # MACD Related
        "macd": (
            "MACD: Computes momentum via differences of EMAs. "
            "Usage: Look for crossovers and divergence as signals of trend changes. "
            "Tips: Confirm with other indicators in low-volatility or sideways markets."
        ),
        "macds": (
            "MACD Signal: An EMA smoothing of the MACD line. "
            "Usage: Use crossovers with the MACD line to trigger trades. "
            "Tips: Should be part of a broader strategy to avoid false positives."
        ),
        "macdh": (
            "MACD Histogram: Shows the gap between the MACD line and its signal. "
            "Usage: Visualize momentum strength and spot divergence early. "
            "Tips: Can be volatile; complement with additional filters in fast-moving markets."
        ),
        # Momentum Indicators
        "rsi": (
            "RSI: Measures momentum to flag overbought/oversold conditions. "
            "Usage: Apply 70/30 thresholds and watch for divergence to signal reversals. "
            "Tips: In strong trends, RSI may remain extreme; always cross-check with trend analysis."
        ),
        # Volatility Indicators
        "boll": (
            "Bollinger Middle: A 20 SMA serving as the basis for Bollinger Bands. "
            "Usage: Acts as a dynamic benchmark for price movement. "
            "Tips: Combine with the upper and lower bands to effectively spot breakouts or reversals."
        ),
        "boll_ub": (
            "Bollinger Upper Band: Typically 2 standard deviations above the middle line. "
            "Usage: Signals potential overbought conditions and breakout zones. "
            "Tips: Confirm signals with other tools; prices may ride the band in strong trends."
        ),
        "boll_lb": (
            "Bollinger Lower Band: Typically 2 standard deviations below the middle line. "
            "Usage: Indicates potential oversold conditions. "
            "Tips: Use additional analysis to avoid false reversal signals."
        ),
        "atr": (
            "ATR: Averages true range to measure volatility. "
            "Usage: Set stop-loss levels and adjust position sizes based on current market volatility. "
            "Tips: It's a reactive measure, so use it as part of a broader risk management strategy."
        ),
        # Volume-Based Indicators
        "vwma": (
            "VWMA: A moving average weighted by volume. "
            "Usage: Confirm trends by integrating price action with volume data. "
            "Tips: Watch for skewed results from volume spikes; use in combination with other volume analyses."
        ),
        "mfi": (
            "MFI: The Money Flow Index is a momentum indicator that uses both price and volume to measure buying and selling pressure. "
            "Usage: Identify overbought (>80) or oversold (<20) conditions and confirm the strength of trends or reversals. "
            "Tips: Use alongside RSI or MACD to confirm signals; divergence between price and MFI can indicate potential reversals."
        ),
    }

    if indicator not in best_ind_params:
        raise ValueError(
            f"Indicator {indicator} is not supported. Please choose from: {list(best_ind_params.keys())}"
        )

    end_date = curr_date
    curr_date = datetime.strptime(curr_date, "%Y-%m-%d")
    before = curr_date - relativedelta(days=look_back_days)

    if not online:
        # read from YFin data
        data = pd.read_csv(
            os.path.join(
                DATA_DIR,
                f"market_data/price_data/{symbol}-YFin-data-2015-01-01-2025-03-25.csv",
            )
        )
        data["Date"] = pd.to_datetime(data["Date"], utc=True)
        dates_in_df = data["Date"].astype(str).str[:10]

        ind_string = ""
        while curr_date >= before:
            # only do the trading dates
            if curr_date.strftime("%Y-%m-%d") in dates_in_df.values:
                indicator_value = get_stockstats_indicator(
                    symbol, indicator, curr_date.strftime("%Y-%m-%d"), online
                )

                ind_string += f"{curr_date.strftime('%Y-%m-%d')}: {indicator_value}\n"

            curr_date = curr_date - relativedelta(days=1)
    else:
        # online gathering
        ind_string = ""
        while curr_date >= before:
            indicator_value = get_stockstats_indicator(
                symbol, indicator, curr_date.strftime("%Y-%m-%d"), online
            )

            ind_string += f"{curr_date.strftime('%Y-%m-%d')}: {indicator_value}\n"

            curr_date = curr_date - relativedelta(days=1)

    result_str = (
        f"## {indicator} values from {before.strftime('%Y-%m-%d')} to {end_date}:\n\n"
        + ind_string
        + "\n\n"
        + best_ind_params.get(indicator, "No description available.")
    )

    return result_str


def get_stockstats_indicator(
    symbol: Annotated[str, "ticker symbol of the company"],
    indicator: Annotated[str, "technical indicator to get the analysis and report of"],
    curr_date: Annotated[
        str, "The current trading date you are trading on, YYYY-mm-dd"
    ],
    online: Annotated[bool, "to fetch data online or offline"],
) -> str:

    curr_date = datetime.strptime(curr_date, "%Y-%m-%d")
    curr_date = curr_date.strftime("%Y-%m-%d")

    try:
        indicator_value = StockstatsUtils.get_stock_stats(
            symbol,
            indicator,
            curr_date,
            os.path.join(DATA_DIR, "market_data", "price_data"),
            online=online,
        )
    except Exception as e:
        print(
            f"Error getting stockstats indicator data for indicator {indicator} on {curr_date}: {e}"
        )
        return ""

    return str(indicator_value)


def get_YFin_data_window(
    symbol: Annotated[str, "ticker symbol of the company"],
    curr_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    look_back_days: Annotated[int, "how many days to look back"],
) -> str:
    # calculate past days
    date_obj = datetime.strptime(curr_date, "%Y-%m-%d")
    before = date_obj - relativedelta(days=look_back_days)
    start_date = before.strftime("%Y-%m-%d")

    # read in data
    data = pd.read_csv(
        os.path.join(
            DATA_DIR,
            f"market_data/price_data/{symbol}-YFin-data-2015-01-01-2025-03-25.csv",
        )
    )

    # Extract just the date part for comparison
    data["DateOnly"] = data["Date"].str[:10]

    # Filter data between the start and end dates (inclusive)
    filtered_data = data[
        (data["DateOnly"] >= start_date) & (data["DateOnly"] <= curr_date)
    ]

    # Drop the temporary column we created
    filtered_data = filtered_data.drop("DateOnly", axis=1)

    # Set pandas display options to show the full DataFrame
    with pd.option_context(
        "display.max_rows", None, "display.max_columns", None, "display.width", None
    ):
        df_string = filtered_data.to_string()

    return (
        f"## Raw Market Data for {symbol} from {start_date} to {curr_date}:\n\n"
        + df_string
    )


def get_YFin_data_online(
    symbol: Annotated[str, "ticker symbol of the company"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
):

    datetime.strptime(start_date, "%Y-%m-%d")
    datetime.strptime(end_date, "%Y-%m-%d")

    # Create ticker object
    ticker = yf.Ticker(symbol.upper())

    # Fetch historical data for the specified date range
    data = ticker.history(start=start_date, end=end_date)

    # Check if data is empty
    if data.empty:
        return (
            f"No data found for symbol '{symbol}' between {start_date} and {end_date}"
        )

    # Remove timezone info from index for cleaner output
    if data.index.tz is not None:
        data.index = data.index.tz_localize(None)

    # Round numerical values to 2 decimal places for cleaner display
    numeric_columns = ["Open", "High", "Low", "Close", "Adj Close"]
    for col in numeric_columns:
        if col in data.columns:
            data[col] = data[col].round(2)

    # Convert DataFrame to CSV string
    csv_string = data.to_csv()

    # Add header information
    header = f"# Stock data for {symbol.upper()} from {start_date} to {end_date}\n"
    header += f"# Total records: {len(data)}\n"
    header += f"# Data retrieved on: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"

    return header + csv_string


def get_YFin_data(
    symbol: Annotated[str, "ticker symbol of the company"],
    start_date: Annotated[str, "Start date in yyyy-mm-dd format"],
    end_date: Annotated[str, "End date in yyyy-mm-dd format"],
) -> str:
    # read in data
    data = pd.read_csv(
        os.path.join(
            DATA_DIR,
            f"market_data/price_data/{symbol}-YFin-data-2015-01-01-2025-03-25.csv",
        )
    )

    if end_date > "2025-03-25":
        raise Exception(
            f"Get_YFin_Data: {end_date} is outside of the data range of 2015-01-01 to 2025-03-25"
        )

    # Extract just the date part for comparison
    data["DateOnly"] = data["Date"].str[:10]

    # Filter data between the start and end dates (inclusive)
    filtered_data = data[
        (data["DateOnly"] >= start_date) & (data["DateOnly"] <= end_date)
    ]

    # Drop the temporary column we created
    filtered_data = filtered_data.drop("DateOnly", axis=1)

    # remove the index from the dataframe
    filtered_data = filtered_data.reset_index(drop=True)

    return filtered_data


def get_stock_news_openai(ticker, curr_date):
    config = get_config()
    client = OpenAI(base_url=config["backend_url"])

    response = client.responses.create(
        model=config["quick_think_llm"],
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"Can you search Social Media for {ticker} from 7 days before {curr_date} to {curr_date}? Make sure you only get the data posted during that period.",
                    }
                ],
            }
        ],
        text={"format": {"type": "text"}},
        reasoning={},
        tools=[
            {
                "type": "web_search_preview",
                "user_location": {"type": "approximate"},
                "search_context_size": "low",
            }
        ],
        temperature=1,
        max_output_tokens=4096,
        top_p=1,
        store=True,
    )

    return response.output[1].content[0].text


def get_global_news_openai(curr_date):
    config = get_config()
    client = OpenAI(base_url=config["backend_url"])

    response = client.responses.create(
        model=config["quick_think_llm"],
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"Can you search global or macroeconomics news from 7 days before {curr_date} to {curr_date} that would be informative for trading purposes? Make sure you only get the data posted during that period.",
                    }
                ],
            }
        ],
        text={"format": {"type": "text"}},
        reasoning={},
        tools=[
            {
                "type": "web_search_preview",
                "user_location": {"type": "approximate"},
                "search_context_size": "low",
            }
        ],
        temperature=1,
        max_output_tokens=4096,
        top_p=1,
        store=True,
    )

    return response.output[1].content[0].text


def get_fundamentals_openai(ticker, curr_date):
    config = get_config()
    client = OpenAI(base_url=config["backend_url"])

    response = client.responses.create(
        model=config["quick_think_llm"],
        input=[
            {
                "role": "system",
                "content": [
                    {
                        "type": "input_text",
                        "text": f"Can you search Fundamental for discussions on {ticker} during of the month before {curr_date} to the month of {curr_date}. Make sure you only get the data posted during that period. List as a table, with PE/PS/Cash flow/ etc",
                    }
                ],
            }
        ],
        text={"format": {"type": "text"}},
        reasoning={},
        tools=[
            {
                "type": "web_search_preview",
                "user_location": {"type": "approximate"},
                "search_context_size": "low",
            }
        ],
        temperature=1,
        max_output_tokens=4096,
        top_p=1,
        store=True,
    )

    return response.output[1].content[0].text
