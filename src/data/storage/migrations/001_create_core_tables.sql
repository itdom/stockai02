-- AI3 core tables aligned with src/data/storage/table_registry.py.
-- MySQL 8.x / InnoDB / utf8mb4.

CREATE TABLE IF NOT EXISTS `instrument` (
  `symbol` VARCHAR(16) NOT NULL,
  `name` VARCHAR(128) NULL,
  `market` VARCHAR(16) NULL,
  `exchange` VARCHAR(16) NULL,
  `asset_type` VARCHAR(32) NULL,
  `list_status` VARCHAR(16) NULL,
  `list_date` CHAR(8) NULL,
  `delist_date` CHAR(8) NULL,
  `industry` VARCHAR(128) NULL,
  `source` VARCHAR(32) NULL,
  `ingested_at` VARCHAR(64) NULL,
  PRIMARY KEY (`symbol`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `market_bar_daily` (
  `symbol` VARCHAR(16) NOT NULL,
  `trade_date` CHAR(8) NOT NULL,
  `frequency` VARCHAR(8) NOT NULL,
  `open` DECIMAL(20, 6) NULL,
  `high` DECIMAL(20, 6) NULL,
  `low` DECIMAL(20, 6) NULL,
  `close` DECIMAL(20, 6) NULL,
  `pre_close` DECIMAL(20, 6) NULL,
  `change` DECIMAL(20, 6) NULL,
  `pct_chg` DECIMAL(20, 6) NULL,
  `volume` DECIMAL(24, 6) NULL,
  `amount` DECIMAL(24, 6) NULL,
  `source` VARCHAR(32) NOT NULL,
  `ingested_at` VARCHAR(64) NULL,
  PRIMARY KEY (`symbol`, `trade_date`, `frequency`, `source`),
  KEY `idx_market_bar_daily_trade_date` (`trade_date`),
  KEY `idx_market_bar_daily_symbol_date` (`symbol`, `trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `market_bar_weekly` (
  `symbol` VARCHAR(16) NOT NULL,
  `trade_date` CHAR(8) NOT NULL,
  `frequency` VARCHAR(8) NOT NULL,
  `open` DECIMAL(20, 6) NULL,
  `high` DECIMAL(20, 6) NULL,
  `low` DECIMAL(20, 6) NULL,
  `close` DECIMAL(20, 6) NULL,
  `pre_close` DECIMAL(20, 6) NULL,
  `change` DECIMAL(20, 6) NULL,
  `pct_chg` DECIMAL(20, 6) NULL,
  `volume` DECIMAL(24, 6) NULL,
  `amount` DECIMAL(24, 6) NULL,
  `source` VARCHAR(32) NOT NULL,
  `ingested_at` VARCHAR(64) NULL,
  PRIMARY KEY (`symbol`, `trade_date`, `frequency`, `source`),
  KEY `idx_market_bar_weekly_trade_date` (`trade_date`),
  KEY `idx_market_bar_weekly_symbol_date` (`symbol`, `trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `raw_social_post` (
  `post_id` VARCHAR(64) NOT NULL,
  `author_id` VARCHAR(64) NULL,
  `author_username` VARCHAR(128) NULL,
  `created_at` VARCHAR(64) NULL,
  `text` TEXT NULL,
  `lang` VARCHAR(16) NULL,
  `like_count` BIGINT NULL,
  `repost_count` BIGINT NULL,
  `reply_count` BIGINT NULL,
  `quote_count` BIGINT NULL,
  `view_count` BIGINT NULL,
  `query` VARCHAR(512) NULL,
  `query_type` VARCHAR(32) NULL,
  `source` VARCHAR(32) NOT NULL,
  `raw_json` JSON NULL,
  `ingested_at` VARCHAR(64) NULL,
  PRIMARY KEY (`post_id`, `source`),
  KEY `idx_raw_social_post_created_at` (`created_at`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `feature_kdj` (
  `symbol` VARCHAR(16) NOT NULL,
  `trade_date` CHAR(8) NOT NULL,
  `frequency` VARCHAR(8) NOT NULL,
  `rsv` DECIMAL(20, 10) NULL,
  `k` DECIMAL(20, 10) NULL,
  `d` DECIMAL(20, 10) NULL,
  `j` DECIMAL(20, 10) NULL,
  `source` VARCHAR(32) NOT NULL,
  `ingested_at` VARCHAR(64) NULL,
  PRIMARY KEY (`symbol`, `trade_date`, `frequency`, `source`),
  KEY `idx_feature_kdj_trade_date` (`trade_date`),
  KEY `idx_feature_kdj_symbol_date` (`symbol`, `trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `signal_kdj_cross` (
  `symbol` VARCHAR(16) NOT NULL,
  `trade_date` CHAR(8) NOT NULL,
  `frequency` VARCHAR(8) NOT NULL,
  `signal_type` VARCHAR(64) NOT NULL,
  `k` DECIMAL(20, 10) NULL,
  `d` DECIMAL(20, 10) NULL,
  `j` DECIMAL(20, 10) NULL,
  `source` VARCHAR(32) NOT NULL,
  `created_at` VARCHAR(64) NULL,
  PRIMARY KEY (`symbol`, `trade_date`, `frequency`, `signal_type`, `source`),
  KEY `idx_signal_kdj_cross_trade_date` (`trade_date`),
  KEY `idx_signal_kdj_cross_symbol_date` (`symbol`, `trade_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `backtest_holding_return` (
  `symbol` VARCHAR(16) NOT NULL,
  `signal_date` CHAR(8) NOT NULL,
  `signal_type` VARCHAR(64) NOT NULL,
  `source` VARCHAR(32) NOT NULL,
  `entry_date` CHAR(8) NULL,
  `entry_close` DECIMAL(20, 6) NULL,
  `horizon` INT NOT NULL,
  `exit_date` CHAR(8) NULL,
  `exit_close` DECIMAL(20, 6) NULL,
  `return_pct` DECIMAL(20, 10) NULL,
  `created_at` VARCHAR(64) NULL,
  PRIMARY KEY (`symbol`, `signal_date`, `signal_type`, `source`, `horizon`),
  KEY `idx_backtest_holding_return_signal_date` (`signal_date`),
  KEY `idx_backtest_holding_return_symbol_date` (`symbol`, `signal_date`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;

CREATE TABLE IF NOT EXISTS `pipeline_run_batch` (
  `run_id` VARCHAR(64) NOT NULL,
  `pipeline_name` VARCHAR(128) NOT NULL,
  `started_at` VARCHAR(64) NOT NULL,
  `finished_at` VARCHAR(64) NULL,
  `status` VARCHAR(32) NOT NULL,
  `duration_seconds` DECIMAL(20, 6) NULL,
  `parameters_json` JSON NULL,
  `metrics_json` JSON NULL,
  `failed_dates_json` JSON NULL,
  `error_message` TEXT NULL,
  PRIMARY KEY (`run_id`),
  KEY `idx_pipeline_run_batch_started_at` (`started_at`),
  KEY `idx_pipeline_run_batch_status` (`status`)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COLLATE=utf8mb4_unicode_ci;
