Binance Futures Testnet Trading BotA clean, production-structured Python CLI for placing orders on the Binance USDT-M Futures Testnet.
Supports Market, Limit, and Stop-Market orders with full input validation, structured logging, and graceful error handling.

Setup
1. Prerequisites

Python 3.9+
A Binance Futures Testnet account

2. Generate Testnet API Credentials

Go to https://testnet.binancefuture.com
Register / log in
Navigate to API Management and generate a new key pair
Copy your API Key and Secret Key

3. Install Dependencies
bashcd trading_bot
pip install -r requirements.txt
4. Configure Credentials
bashcp .env.example .env
# Edit .env and paste your keys
dotenvBINANCE_TESTNET_API_KEY=your_api_key_here
BINANCE_TESTNET_API_SECRET=your_api_secret_here
Then load them into your shell:
bash# Linux / macOS
export $(grep -v '^#' .env | xargs)

# Windows PowerShell
Get-Content .env | Where-Object { $_ -notmatch '^#' } | ForEach-Object {
    $k, $v = $_ -split '=', 2
    [System.Environment]::SetEnvironmentVariable($k, $v, 'Process')
}

How to Run
General syntax
python cli.py <command> [options]
Use --help on any command for a full option list:
bashpython cli.py --help
python cli.py place --help

Place a Market Order
bash# BUY 0.001 BTC at market price (skip confirmation prompt with -y)
python cli.py place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001 -y
Sample output:
┌─── Order Request ───────────────────────────────
│  Symbol     : BTCUSDT
│  Side       : BUY
│  Type       : MARKET
│  Quantity   : 0.001
└────────────────────────────────────────────────
┌─── Order Response ──────────────────────────────
│  Order ID       : 4046119622
│  Client OID     : web_abc123def456
│  Status         : FILLED
│  Executed Qty   : 0.001
│  Avg Fill Price : 64823.5
│  Cum Quote      : 64.8235
│  Updated At     : 1745314322091
└────────────────────────────────────────────────
✔  Order placed successfully!

Place a Limit Order
bash# SELL 0.001 BTC at $67,000 limit
python cli.py place --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.001 --price 67000

Place a Stop-Market Order (Bonus)
bash# Protective SELL stop on ETH — triggers if price drops to $2,900
python cli.py place --symbol ETHUSDT --side SELL --type STOP_MARKET --quantity 0.01 --stop-price 2900 -y

View Account Summary
bashpython cli.py account

List Open Orders
bash# All open orders
python cli.py open-orders

# Filtered by symbol
python cli.py open-orders --symbol BTCUSDT

Verbose / Debug Logging
bashpython cli.py --log-level DEBUG place --symbol BTCUSDT --side BUY --type MARKET --quantity 0.001 -y

Logging
All activity is written to logs/trading_bot.log (rotating, max 5 MB × 3 backups).
LevelGoes toIncludesDEBUGFile onlyFull request params, raw response bodyINFOFile + consoleOrder placed/cancelled, account fetchedWARNINGFile + consoleValidation failuresERRORFile + consoleAPI errors, network failures

Error Handling
ScenarioBehaviourMissing credentialsClear message + exit(1) before any network callInvalid CLI inputValueError caught; printed with ✘ prefixBinance API error (e.g. -1121)BinanceAPIError caught; code + message displayedNetwork timeoutrequests.Timeout caught; logged and reportedConnection failurerequests.ConnectionError caught; logged and reported

Assumptions

Testnet only — The base URL is hardcoded to https://testnet.binancefuture.com. For production swap to https://fapi.binance.com and update TESTNET_BASE_URL in bot/client.py.
One-way position mode — Orders use positionSide=BOTH (default). If your account is in hedge mode, add --position-side LONG/SHORT support.
No leverage / margin management — Leverage is whatever the testnet account defaults to. Adjust via the Binance UI or extend client.py with /fapi/v1/leverage.
Quantity precision — The bot does not auto-round quantities to the symbol's stepSize. If you hit -1111 (Precision is over the maximum defined for this asset), reduce decimal places on your quantity.
Time-in-force — Limit orders default to GTC (Good Till Cancelled).
PROJECT STRUCTURE 
trading_bot/
├── bot/
│   ├── __init__.py          # Package exports
│   ├── client.py            # Binance REST API client (signing, requests, error handling)
│   ├── orders.py            # Order placement logic + response formatting
│   ├── validators.py        # CLI input validation (all raises ValueError)
│   └── logging_config.py   # Rotating file + console logger setup
├── cli.py                   # Argparse CLI entry point
├── logs/
│   └── trading_bot.log      # Auto-created; sample log included
├── .env.example             # Credential template
├── .gitignore
├── requirements.txt
└── README.md


Requirements
requests>=2.31.0
colorama>=0.4.6
python-dotenv>=1.0.0
