# 🚀 News-Driven Trading System for MT5

A complete, production-ready automated trading system that trades based on economic news events.

## ✨ Features

- ✅ Real-time economic calendar integration
- ✅ Pre-news and post-news trading strategies
- ✅ Intelligent breakout detection
- ✅ Advanced risk management
- ✅ Position management (breakeven, trailing stops)
- ✅ Telegram notifications
- ✅ AI-adaptive risk sizing
- ✅ Symbol-specific optimizations
- ✅ Trade journaling and performance tracking

## 📋 Requirements

- Windows 10/11
- MetaTrader 5 (Exness or compatible broker)
- Python 3.10+
- Active trading account

## 🛠️ Installation

### 1. Install MetaTrader 5

Download and install MT5 from your broker (Exness):
- https://www.exness.com/metatrader/

### 2. Install Python

Download Python 3.10+ from:
- https://www.python.org/downloads/

**Important**: Check "Add Python to PATH" during installation

### 3. Install Dependencies

```bash
# Open Command Prompt
cd path\to\news_trading_system

# Install required packages
pip install -r requirements.txt

### 4. Configuration

1. **Broker Setup**: Ensure your MT5 terminal is running and logged in to your trading account.
2. **Edit `config.py`**: Set your trading parameters, MT5 connection details, Telegram bot token, and other preferences in `config.py`.
3. **Economic Calendar API**: If using a paid or custom news API, update the API key and endpoint in `news_parser.py` or `config.py` as needed.

### 5. Running the System

Start the trading system with:

```bash
python main.py
```

The system will connect to MT5, monitor news events, and execute trades automatically based on your strategy and risk settings.

## ⚙️ Configuration Overview

- **config.py**: Main configuration file for API keys, trading symbols, risk settings, and notification preferences.
- **news_parser.py**: Handles fetching and parsing economic news events.
- **strategy.py**: Implements trading logic for pre/post-news and breakout strategies.
- **risk_manager.py**: Advanced risk and position management logic.
- **trade_executor.py**: Interfaces with MT5 to place, modify, and close trades.
- **telegram_notifier.py**: Sends trade and system notifications to Telegram.
- **indicators.py**: Custom technical indicators for trade confirmation.
- **utils.py**: Helper functions and utilities.
- **logger_config.py**: Logging setup for debugging and trade journaling.
- **data/**: Stores historical news, trade logs, and performance data.
- **logs/**: System and error logs.

## 📈 Usage Examples

**Basic Run:**

```bash
python main.py
```

**Custom Symbol/Config:**

Edit `config.py` to change trading symbols, risk parameters, or notification settings.

## 📝 File Descriptions

- **main.py**: Entry point; orchestrates the trading workflow.
- **config.py**: User-editable settings.
- **news_parser.py**: News event integration.
- **strategy.py**: Trading strategies.
- **risk_manager.py**: Risk logic.
- **trade_executor.py**: MT5 trade execution.
- **telegram_notifier.py**: Telegram alerts.
- **indicators.py**: Technical indicators.
- **utils.py**: Utilities.
- **logger_config.py**: Logging setup.
- **data/**: Data storage.
- **logs/**: Log files.

