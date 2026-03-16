CREATE TABLE IF NOT EXISTS traders (
    wallet_address  VARCHAR(66) PRIMARY KEY,
    total_pnl       DECIMAL(20, 8) DEFAULT 0,
    win_rate        DECIMAL(5, 2) DEFAULT 0,
    trade_count     INTEGER DEFAULT 0,
    max_drawdown    DECIMAL(5, 2) DEFAULT 0,
    avg_hold_time   INTERVAL,
    profit_factor   DECIMAL(10, 4) DEFAULT 0,
    score           DECIMAL(10, 4) DEFAULT 0,
    last_trade_time TIMESTAMP WITH TIME ZONE,
    is_smart_money  BOOLEAN DEFAULT FALSE,
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS trades (
    id              BIGSERIAL PRIMARY KEY,
    wallet_address  VARCHAR(66) NOT NULL REFERENCES traders(wallet_address) ON DELETE CASCADE,
    symbol          VARCHAR(32) NOT NULL,
    side            VARCHAR(5) NOT NULL,
    size            DECIMAL(20, 8) NOT NULL,
    entry_price     DECIMAL(20, 8) NOT NULL,
    exit_price      DECIMAL(20, 8),
    pnl             DECIMAL(20, 8),
    open_time       TIMESTAMP WITH TIME ZONE NOT NULL,
    close_time      TIMESTAMP WITH TIME ZONE,
    is_closed       BOOLEAN DEFAULT FALSE,
    leverage        DECIMAL(5, 2),
    source          VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS signals (
    id              BIGSERIAL PRIMARY KEY,
    symbol          VARCHAR(32) NOT NULL,
    signal_type     VARCHAR(10) NOT NULL,
    confidence      DECIMAL(4, 3) NOT NULL,
    participants    JSONB,
    avg_entry_price DECIMAL(20, 8),
    total_size      DECIMAL(20, 8),
    created_at      TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    expired_at      TIMESTAMP WITH TIME ZONE
);

CREATE TABLE IF NOT EXISTS liquidations (
    id              BIGSERIAL PRIMARY KEY,
    symbol          VARCHAR(32) NOT NULL,
    side            VARCHAR(5) NOT NULL,
    price           DECIMAL(20, 8) NOT NULL,
    qty             DECIMAL(20, 8) NOT NULL,
    usd_value       DECIMAL(20, 2),
    source          VARCHAR(20) NOT NULL,
    timestamp       TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE IF NOT EXISTS orderbook_snapshots (
    id              BIGSERIAL PRIMARY KEY,
    symbol          VARCHAR(32) NOT NULL,
    bids            JSONB NOT NULL,
    asks            JSONB NOT NULL,
    source          VARCHAR(20) NOT NULL,
    timestamp       TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE IF NOT EXISTS open_interest (
    id              BIGSERIAL PRIMARY KEY,
    symbol          VARCHAR(32) NOT NULL,
    long_oi         DECIMAL(20, 8) NOT NULL,
    short_oi        DECIMAL(20, 8) NOT NULL,
    source          VARCHAR(20) NOT NULL,
    timestamp       TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE IF NOT EXISTS funding_rates (
    id              BIGSERIAL PRIMARY KEY,
    symbol          VARCHAR(32) NOT NULL,
    rate            DECIMAL(20, 10) NOT NULL,
    source          VARCHAR(20) NOT NULL,
    timestamp       TIMESTAMP WITH TIME ZONE NOT NULL
);

CREATE TABLE IF NOT EXISTS market_tickers (
    id              BIGSERIAL PRIMARY KEY,
    symbol          VARCHAR(32) NOT NULL,
    price           DECIMAL(20, 8) NOT NULL,
    price_change_24h DECIMAL(10, 4),
    volume_24h      DECIMAL(20, 2),
    high_24h        DECIMAL(20, 8),
    low_24h         DECIMAL(20, 8),
    source          VARCHAR(20) NOT NULL,
    timestamp       TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Unique indexes to prevent duplicate data
CREATE UNIQUE INDEX IF NOT EXISTS uq_trades_dedup
  ON trades (wallet_address, symbol, side, entry_price, open_time, source);

CREATE UNIQUE INDEX IF NOT EXISTS uq_liquidations_dedup
  ON liquidations (symbol, side, price, qty, timestamp, source);

CREATE INDEX IF NOT EXISTS idx_traders_score ON traders(score DESC);
CREATE INDEX IF NOT EXISTS idx_traders_smart_money ON traders(is_smart_money) WHERE is_smart_money = TRUE;
CREATE INDEX IF NOT EXISTS idx_traders_pnl ON traders(total_pnl DESC);

CREATE INDEX IF NOT EXISTS idx_trades_wallet ON trades(wallet_address, open_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_symbol ON trades(symbol, open_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_time ON trades(open_time DESC);
CREATE INDEX IF NOT EXISTS idx_trades_open ON trades(is_closed) WHERE is_closed = FALSE;

CREATE INDEX IF NOT EXISTS idx_signals_time ON signals(created_at DESC);
CREATE INDEX IF NOT EXISTS idx_signals_symbol ON signals(symbol, created_at DESC);

CREATE INDEX IF NOT EXISTS idx_liquidations_time ON liquidations(timestamp DESC);
CREATE INDEX IF NOT EXISTS idx_liquidations_symbol ON liquidations(symbol, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_orderbook_symbol_time ON orderbook_snapshots(symbol, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_oi_symbol_time ON open_interest(symbol, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_funding_symbol_time ON funding_rates(symbol, timestamp DESC);

CREATE INDEX IF NOT EXISTS idx_tickers_symbol_time ON market_tickers(symbol, timestamp DESC);
