import pandas as pd

class TechnicalIndicators:
    """
    Mathematical engine for ArthaGuard AI.
    Calculates RSI, MACD, and Bollinger Bands on raw DataFrames.
    """
    
    @staticmethod
    def add_all_indicators(df: pd.DataFrame) -> pd.DataFrame:
        if df.empty:
            return df
            
        df = TechnicalIndicators._rsi(df)
        df = TechnicalIndicators._macd(df)
        df = TechnicalIndicators._bollinger_bands(df)
        return df

    @staticmethod
    def _rsi(df: pd.DataFrame, window=14) -> pd.DataFrame:
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=window).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=window).mean()
        rs = gain / loss
        df['RSI'] = 100 - (100 / (1 + rs))
        return df

    @staticmethod
    def _macd(df: pd.DataFrame) -> pd.DataFrame:
        ema_12 = df['Close'].ewm(span=12, adjust=False).mean()
        ema_26 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = ema_12 - ema_26
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
        return df

    @staticmethod
    def _bollinger_bands(df: pd.DataFrame) -> pd.DataFrame:
        df['SMA_20'] = df['Close'].rolling(window=20).mean()
        df['Std_Dev'] = df['Close'].rolling(window=20).std()
        df['Upper_Band'] = df['SMA_20'] + (df['Std_Dev'] * 2)
        df['Lower_Band'] = df['SMA_20'] - (df['Std_Dev'] * 2)
        return df