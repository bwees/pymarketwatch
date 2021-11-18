# Autor: bwees, based on code from https://github.com/kevindong/MarketWatch_API/

import json
from typing import DefaultDict
import requests
from urllib.parse import urlparse
from enum import Enum
from lxml import html
import re
import csv

# Order Types and Enums
class Term(Enum):
	DAY = "Day"
	INDEFINITE = "Cancelled"

class PriceType(Enum):
	MARKET = 1
	LIMIT = 2
	STOP = 3

class OrderType(Enum):
	BUY = "Buy"
	SELL = "Sell"
	SHORT = "Short"
	COVER = "Cover"

# Order structure
class Order:
	def __init__(self, id, ticker, quantity, orderType, priceType, price = None):
		self.id = id
		self.ticker = ticker
		self.quantity = quantity
		self.orderType = orderType
		self.priceType = priceType
		self.price = price

# Position Structure
class Position:
	def __init__(self, ticker, orderType, quantity):
		self.ticker = ticker
		self.orderType = orderType
		self.quantity = quantity

# Main Class for Interacting with MarketWatch API
class MarketWatch:
	def __init__(self, email, password, game, debug = False):
		self.debug = debug
		self.game = game
		self.session = requests.Session()
		
		self.login(email, password)
		self.check_error()

		# Get player ID
		self.playerID = re.findall(";p=[0-9]+", self.session.get("https://www.marketwatch.com/game/"+self.game+"/portfolio").text)[0].split("=")[1]


	# Main login flow, subject to change at any point
	def login(self, email, password):
		r = self.session.get("https://accounts.marketwatch.com/login")

		# parse url and extract query string into dictionary
		url = urlparse(r.url)
		given_params = dict(q.split("=") for q in url.query.split("&"))

		login_data = {
			"client_id": given_params['client'],
			"connection": "DJldap",
			"headers": {"X-REMOTE-USER": email},
			"nonce": given_params["nonce"],
			"ns": "prod/accounts-mw",
			"password": password,
			"protocol": "oauth2",
			"redirect_uri": "https://accounts.marketwatch.com/auth/sso/login",
			"response_type": "code",
			"scope": "openid idp_id roles email given_name family_name djid djUsername djStatus trackid tags prts suuid createTimestamp",
			"state": given_params["state"],
			"tenant": "sso",
			"ui_locales": ",en-us-x-mw-3-8",
			"username": email,
			"_csrf": self.session.cookies.get_dict()['_csrf'],
			"_intstate": "deprecated"
		}

		login = self.session.post("https://sso.accounts.dowjones.com/usernamepassword/login", data=login_data)
		tree = html.fromstring(login.content)

		callback_payload = {
			"wa": tree.xpath("//input[@name='wa']/@value"),
			"wresult": tree.xpath("//input[@name='wresult']/@value"),
			"wctx": tree.xpath("//input[@name='wctx']/@value")
		}

		self.session.post("https://sso.accounts.dowjones.com/login/callback", data=callback_payload)

	def check_error(self):
		if self.session.get("https://www.marketwatch.com/game/"+self.game).status_code != 200:
			raise Exception("Marketwatch Stock Market Game Down")

	# Get current market price for ticker
	def get_price(self, ticker):
		try:
			page = self.session.get("http://www.marketwatch.com/investing/stock/" + ticker)
			tree = html.fromstring(page.content)
			price = tree.xpath("//*[@id='maincontent']/div[2]/div[3]/div/div[2]/h2/bg-quote")
			return round(float(price[0].text), 2)
		except:
			return None

	# Main Order execution functions

	def buy(self, ticker, shares, term = Term.INDEFINITE, priceType = PriceType.MARKET, price = None):
		return self._create_payload(ticker, shares, term, priceType, price, OrderType.BUY)

	def short(self, ticker, shares, term = Term.INDEFINITE, priceType = PriceType.MARKET, price = None):
		return self._create_payload(ticker, shares, term, priceType, price, OrderType.SHORT)

	def sell(self, ticker, shares, term = Term.INDEFINITE, priceType = PriceType.MARKET, price = None):
		return self._create_payload(ticker, shares, term, priceType, price, OrderType.SELL)

	def cover(self, ticker, shares, term = Term.INDEFINITE, priceType = PriceType.MARKET, price = None):
		return self._create_payload(ticker, shares, term, priceType, price, OrderType.COVER)

	# Payload creation for order execution
	def _create_payload(self, ticker, shares, term, priceType, price, orderType):
		ticker = self._get_ticker_uid(ticker)
		payload = [{"Fuid": ticker, "Shares": str(shares), "Type": orderType.value, "Term": term.value}]
		if (priceType == PriceType.LIMIT):
			payload[0]['Limit'] = str(price)
		if (priceType == PriceType.STOP):
			payload[0]['Stop'] = str(price)
		return self._submit(payload)

	# Get UID from ticker name
	def _get_ticker_uid(self, ticker):
		page = self.session.get("http://www.marketwatch.com/investing/stock/" + ticker)
		tree = html.fromstring(page.content)

		try:
			tickerSymbol = self._clean_text(tree.xpath('//*[@id="maincontent"]/div[2]/div[4]/mw-chart')[0].get('data-ticker'))
			tickerParts = tickerSymbol.split("/")
			return tickerParts[0]+"-"+tickerParts[2]+"-"+tickerParts[3]
		except:
			return None

	# Execture order
	def _submit(self, payload):
		url = ('http://www.marketwatch.com/game/%s/trade/submitorder' % self.game)
		headers = {'Content-Type': 'application/json'}
		response = json.loads((self.session.post(url=url, headers=headers, json=payload)).text)
		return response["succeeded"], response["message"]

	def cancel_order(self, id):
		url = ('http://www.marketwatch.com/game/' + self.game + '/trade/cancelorder?id=' + str(id))
		self.session.get(url)

	def cancel_all_orders(self):
		for order in self.getPendingOrders():
			url = ('http://www.marketwatch.com/game/' + self.game + '/trade/cancelorder?id=' + str(order.id))
			self.session.get(url)

	def get_pending_orders(self):
		tree = html.fromstring(self.session.get("http://www.marketwatch.com/game/" + self.game + "/portfolio").content)
		rawOrders = tree.xpath("//*[@id='maincontent']/div[3]/div[1]/div[6]/mw-tabs/div[2]/div[2]/div/table/tbody")

		orders = []
		try:
			numberOfOrders = len(rawOrders[0])
		except:
			return orders
		for i in range(numberOfOrders):
			try:
				cleanID = self._clean_text(rawOrders[0][i][4][0][0].get("data-order"))
			except:
				cleanID = None

			ticker = self._clean_text(rawOrders[0][i][0][0][0].text)
			quantity = int(self._clean_text(rawOrders[0][i][3].text))	
			orderType = self._get_order_type(self._clean_text(rawOrders[0][i][2].text))
			priceType = self._get_price_type(self._clean_text(rawOrders[0][i][2].text))
			price = self._get_order_price(self._clean_text(rawOrders[0][i][2].text))

			orders.append(Order(cleanID, ticker, quantity, orderType, priceType, price))
	
		return orders

	def _clean_text(self, text):
		return text.replace("\r\n", "").replace("\t", "").replace(" ", "").replace(",", "")

	def _get_order_type(self, order):
		if ("Buy" in order):
			return OrderType.BUY
		elif ("Short" in order):
			return OrderType.SHORT
		elif ("Cover" in order):
			return OrderType.COVER
		elif ("Sell" in order):
			return OrderType.SELL
		else:
			return None

	def _get_price_type(self, order):
		if ("market" in order):
			return PriceType.MARKET
		elif ("limit" in order):
			return PriceType.LIMIT
		elif ("stop" in order):
			return PriceType.STOP
		else:
			return None

	def _get_order_price(self, order):
		if ("$" not in order):
			return None
		else:
			return float(order[(order.index('$') + 1):])

	def get_positions(self):
		position_csv = self.session.get("http://www.marketwatch.com/game/" + self.game + "/download?view=holdings&p="+self.playerID).text

		positions = []
		# extract all lines, skipping the header, in the given csv text
		reader = csv.reader(position_csv.split("\n")[1:])
		for parts in reader:
			if len(parts) > 0:
				# create a Position object for each ticker
				positions.append(Position(parts[0], parts[3], int(parts[1])))

		return positions

	def get_portfolio_stats(self):
		tree = html.fromstring(self.session.get("http://www.marketwatch.com/game/" + self.game + "/portfolio").content)

		stats = {
			"cash": float(self._clean_text(tree.xpath("//*[@id='maincontent']/div[3]/div[1]/div[2]/ul/li[5]/span")[0].text.replace("$", ""))),
			"value": float(self._clean_text(tree.xpath("//*[@id='maincontent']/div[3]/div[1]/div[2]/ul/li[1]/span")[0].text.replace("$", ""))),
			"power": float(self._clean_text(tree.xpath("//*[@id='maincontent']/div[3]/div[1]/div[2]/ul/li[6]/span")[0].text.replace("$", ""))),
			"rank": int(self._clean_text(tree.xpath("//*[@id='maincontent']/div[3]/div[1]/div[2]/div[1]/div")[0].text.replace("$", ""))),
			"overall_gains": float(self._clean_text(tree.xpath("//*[@id='maincontent']/div[3]/div[1]/div[2]/ul/li[3]/span")[0].text.replace("$", ""))),
			"short_reserve": float(self._clean_text(tree.xpath("//*[@id='maincontent']/div[3]/div[1]/div[2]/ul/li[7]/span")[0].text.replace("$", ""))),
			"overall_returns": float(self._clean_text(tree.xpath("//*[@id='maincontent']/div[3]/div[1]/div[2]/ul/li[4]/span")[0].text.replace("%", "")))/100,
			"borrowed": float(self._clean_text(tree.xpath("//*[@id='maincontent']/div[3]/div[1]/div[2]/ul/li[8]/span")[0].text.replace("$", "")))
		}
		return stats

	def get_game_settings(self):
		tree = html.fromstring(self.session.get("http://www.marketwatch.com/game/" + self.game + "/settings").content)
		settings = {
			"game_public": self._clean_text(tree.xpath('//*[@id="maincontent"]/div[3]/div[1]/div[2]/div[1]/table[1]/tbody/tr/td[2]')[0].text) == "Public",
			"portfolios_public": self._clean_text(tree.xpath('//*[@id="maincontent"]/div[3]/div[1]/div[2]/div[1]/table[2]/tbody/tr/td[2]')[0].text) == "Public",
			"start_balance": float(self._clean_text(tree.xpath('//*[@id="maincontent"]/div[3]/div[1]/div[2]/div[2]/table[1]/tbody/tr[1]/td[2]')[0].text.replace("$", ""))),
			"commission": float(self._clean_text(tree.xpath('//*[@id="maincontent"]/div[3]/div[1]/div[2]/div[2]/table[1]/tbody/tr[2]/td[2]')[0].text.replace("$", ""))),
			"credit_interest_rate": float(self._clean_text(tree.xpath('//*[@id="maincontent"]/div[3]/div[1]/div[2]/div[2]/table[1]/tbody/tr[3]/td[2]')[0].text.replace("%", "")))/100,
			"leverage_debt_interest_rate": float(self._clean_text(tree.xpath('//*[@id="maincontent"]/div[3]/div[1]/div[2]/div[2]/table[1]/tbody/tr[4]/td[2]')[0].text.replace("%", "")))/100,
			"minimum_stock_price": float(self._clean_text(tree.xpath('//*[@id="maincontent"]/div[3]/div[1]/div[2]/div[2]/table[1]/tbody/tr[5]/td[2]')[0].text.replace("$", ""))),
			"maximum_stock_price": float(self._clean_text(tree.xpath('//*[@id="maincontent"]/div[3]/div[1]/div[2]/div[2]/table[1]/tbody/tr[6]/td[2]')[0].text.replace("$", ""))),
			"volume_limit": float(self._clean_text(tree.xpath('//*[@id="maincontent"]/div[3]/div[1]/div[2]/div[2]/table[2]/tbody/tr[1]/td[2]')[0].text.replace("%", "")))/100,
			"short_selling_enabled": self._clean_text(tree.xpath('//*[@id="maincontent"]/div[3]/div[1]/div[2]/div[2]/table[2]/tbody/tr[2]/td[2]')[0].text) == "Enabled",
			"margin_trading_enabled": self._clean_text(tree.xpath('//*[@id="maincontent"]/div[3]/div[1]/div[2]/div[2]/table[2]/tbody/tr[3]/td[2]')[0].text) == "Enabled",
			"limit_orders_enabled": self._clean_text(tree.xpath('//*[@id="maincontent"]/div[3]/div[1]/div[2]/div[2]/table[2]/tbody/tr[4]/td[2]')[0].text) == "Enabled",
			"stop_loss_orders_enabled": self._clean_text(tree.xpath('//*[@id="maincontent"]/div[3]/div[1]/div[2]/div[2]/table[2]/tbody/tr[5]/td[2]')[0].text) == "Enabled",
			"partial_share_trading_enabled": self._clean_text(tree.xpath('//*[@id="maincontent"]/div[3]/div[1]/div[2]/div[2]/table[2]/tbody/tr[6]/td[2]')[0].text) == "Enabled",
		}

		return settings
