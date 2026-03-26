import yfinance as yf

data = yf.download('NVDA', period='1d')
price = float(data['Close'].iloc[-1])
print(f'NVDA: ${price:.2f}')