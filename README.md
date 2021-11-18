# pymarketwatch
A Python libary to interact with the MarketWatch Stock Market Game
Based on code from https://github.com/kevindong/MarketWatch_API/

### Example
```
from pymarketwatch import MarketWatch

api = MarketWatch("email", "password", "game-name-from-url", True)
api.buy("AAPL", 100)

print(api.get_pending_orders())
print(api.get_positions())

```
