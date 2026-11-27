#property strict
#property version   "0.23"
#property description "TradingAI batched multi-timeframe market-data bridge. No order execution."

input string BackendUrl = "https://YOUR_BACKEND_HOST";
input string BridgeToken = "SET_A_LONG_RANDOM_TOKEN";
input int UploadIntervalSeconds = 10;
input int CandleCount = 120;
input bool UploadAllTimeframes = true;
input ENUM_TIMEFRAMES SingleUploadTimeframe = PERIOD_M5;
input bool SendContractSpecification = true;

string Number(double value, int digits)
{
   return DoubleToString(value, digits);
}

bool IsValidSymbolData(string symbol)
{
   double bid = MarketInfo(symbol, MODE_BID);
   double ask = MarketInfo(symbol, MODE_ASK);
   return (bid > 0 && ask >= bid);
}

// Recognizes standard major/minor pairs and XAU/XAG, including broker suffixes/prefixes.
bool IsSupportedFxSymbol(string brokerSymbol)
{
   string raw = brokerSymbol;
   StringToUpper(raw);
   string letters = "";
   for(int i = 0; i < StringLen(raw); i++)
   {
      int ch = StringGetCharacter(raw, i);
      if(ch >= 65 && ch <= 90)
         letters += StringSubstr(raw, i, 1);
   }

   string allowed[30] = {
      "EURUSD", "GBPUSD", "USDJPY", "USDCHF", "USDCAD", "AUDUSD", "NZDUSD",
      "EURGBP", "EURJPY", "EURCHF", "EURCAD", "EURAUD", "EURNZD",
      "GBPJPY", "GBPCHF", "GBPCAD", "GBPAUD", "GBPNZD",
      "AUDJPY", "AUDCHF", "AUDCAD", "AUDNZD",
      "NZDJPY", "NZDCHF", "NZDCAD", "CADJPY", "CADCHF", "CHFJPY",
      "XAUUSD", "XAGUSD"
   };

   for(int start = 0; start <= StringLen(letters) - 6; start++)
   {
      string candidate = StringSubstr(letters, start, 6);
      for(int p = 0; p < 30; p++)
         if(candidate == allowed[p]) return true;
   }
   return false;
}

string TimeframeName(ENUM_TIMEFRAMES timeframe)
{
   if(timeframe == PERIOD_M1) return "M1";
   if(timeframe == PERIOD_M5) return "M5";
   if(timeframe == PERIOD_M15) return "M15";
   if(timeframe == PERIOD_M30) return "M30";
   if(timeframe == PERIOD_H1) return "H1";
   if(timeframe == PERIOD_H4) return "H4";
   if(timeframe == PERIOD_D1) return "D1";
   return "";
}

string BuildCandles(string symbol, ENUM_TIMEFRAMES timeframe)
{
   string out = "[";
   int total = iBars(symbol, timeframe);
   int count = MathMin(CandleCount, total - 1); // exclude current, still-open candle
   bool first = true;

   for(int shift = count; shift >= 1; shift--)
   {
      datetime t = iTime(symbol, timeframe, shift);
      double o = iOpen(symbol, timeframe, shift);
      double h = iHigh(symbol, timeframe, shift);
      double l = iLow(symbol, timeframe, shift);
      double c = iClose(symbol, timeframe, shift);
      long volume = iVolume(symbol, timeframe, shift);

      if(t <= 0 || o <= 0 || h <= 0 || l <= 0 || c <= 0) continue;
      if(h < MathMax(o, c) || l > MathMin(o, c) || h < l) continue;

      if(!first) out += ",";
      out += StringFormat(
         "{\"time\":\"%s\",\"open\":%s,\"high\":%s,\"low\":%s,\"close\":%s,\"tick_volume\":%d,\"isOpen\":false}",
         TimeToString(t, TIME_DATE|TIME_SECONDS),
         Number(o, (int)MarketInfo(symbol, MODE_DIGITS)),
         Number(h, (int)MarketInfo(symbol, MODE_DIGITS)),
         Number(l, (int)MarketInfo(symbol, MODE_DIGITS)),
         Number(c, (int)MarketInfo(symbol, MODE_DIGITS)),
         volume
      );
      first = false;
   }
   out += "]";
   return out;
}

string BuildContract(string symbol)
{
   // MT4 MODE_TICKSIZE is in points; convert to the actual price increment.
   double tickSize = MarketInfo(symbol, MODE_TICKSIZE) * MarketInfo(symbol, MODE_POINT);
   double tickValue = MarketInfo(symbol, MODE_TICKVALUE);
   double minLot = MarketInfo(symbol, MODE_MINLOT);
   double lotStep = MarketInfo(symbol, MODE_LOTSTEP);
   double maxLot = MarketInfo(symbol, MODE_MAXLOT);

   if(tickSize <= 0 || tickValue <= 0 || minLot <= 0 || lotStep <= 0 || maxLot <= 0)
      return "null";

   return StringFormat(
      "{\"tick_size\":%s,\"tick_value_per_lot\":%s,\"min_lot\":%s,\"lot_step\":%s,\"max_lot\":%s}",
      DoubleToString(tickSize, 8), DoubleToString(tickValue, 8),
      DoubleToString(minLot, 4), DoubleToString(lotStep, 4), DoubleToString(maxLot, 4)
   );
}

// One HTTP request per symbol carries the quote, contract and all seven timeframes.
bool UploadSymbol(string symbol)
{
   if(!IsValidSymbolData(symbol)) return false;

   int digits = (int)MarketInfo(symbol, MODE_DIGITS);
   double bid = MarketInfo(symbol, MODE_BID);
   double ask = MarketInfo(symbol, MODE_ASK);
   string contract = SendContractSpecification ? BuildContract(symbol) : "null";
   string body = "";

   if(UploadAllTimeframes)
   {
      string candlesByTimeframe = "{";
      candlesByTimeframe += "\"M1\":" + BuildCandles(symbol, PERIOD_M1);
      candlesByTimeframe += ",\"M5\":" + BuildCandles(symbol, PERIOD_M5);
      candlesByTimeframe += ",\"M15\":" + BuildCandles(symbol, PERIOD_M15);
      candlesByTimeframe += ",\"M30\":" + BuildCandles(symbol, PERIOD_M30);
      candlesByTimeframe += ",\"H1\":" + BuildCandles(symbol, PERIOD_H1);
      candlesByTimeframe += ",\"H4\":" + BuildCandles(symbol, PERIOD_H4);
      candlesByTimeframe += ",\"D1\":" + BuildCandles(symbol, PERIOD_D1);
      candlesByTimeframe += "}";

      body = StringFormat(
         "{\"symbol\":\"%s\",\"bid\":%s,\"ask\":%s,\"candles_by_timeframe\":%s,\"contract\":%s}",
         symbol, Number(bid, digits), Number(ask, digits), candlesByTimeframe, contract
      );
   }
   else
   {
      string tf = TimeframeName(SingleUploadTimeframe);
      if(tf == "") return false;
      body = StringFormat(
         "{\"symbol\":\"%s\",\"timeframe\":\"%s\",\"bid\":%s,\"ask\":%s,\"candles\":%s,\"contract\":%s}",
         symbol, tf, Number(bid, digits), Number(ask, digits),
         BuildCandles(symbol, SingleUploadTimeframe), contract
      );
   }

   char post[];
   char result[];
   string headers = "Content-Type: application/json\r\nX-TradingAI-Token: " + BridgeToken + "\r\n";
   StringToCharArray(body, post, 0, WHOLE_ARRAY, CP_UTF8);
   if(ArraySize(post) > 0) ArrayResize(post, ArraySize(post) - 1);

   string responseHeaders;
   ResetLastError();
   int code = WebRequest("POST", BackendUrl + "/api/v1/mt4/market-data",
                         headers, 10000, post, result, responseHeaders);
   if(code == -1)
   {
      Print("TradingAI upload failed for ", symbol, ". Error=", GetLastError(),
            ". Add backend URL to MT4 WebRequest allowed list.");
      return false;
   }
   if(code < 200 || code >= 300)
   {
      Print("TradingAI backend rejected ", symbol, ". HTTP=", code,
            " response=", CharArrayToString(result));
      return false;
   }
   return true;
}

int OnInit()
{
   if(StringFind(BackendUrl, "https://") != 0)
   {
      Print("TradingAI: configure HTTPS BackendUrl before enabling the bridge.");
      return INIT_PARAMETERS_INCORRECT;
   }
   if(BridgeToken == "" || BridgeToken == "SET_A_LONG_RANDOM_TOKEN")
   {
      Print("TradingAI: configure BridgeToken in EA inputs.");
      return INIT_PARAMETERS_INCORRECT;
   }
   EventSetTimer(MathMax(1, UploadIntervalSeconds));
   Print("TradingAI batched multi-symbol/multi-timeframe bridge initialized. Order execution is DISABLED.");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
}

void OnTimer()
{
   // Enumerate broker-listed symbols, not only those already visible in Market Watch.
   int total = SymbolsTotal(false);
   for(int i = 0; i < total; i++)
   {
      string symbol = SymbolName(i, false);
      if(symbol == "" || !IsSupportedFxSymbol(symbol)) continue;

      if(!SymbolSelect(symbol, true))
      {
         Print("TradingAI: broker symbol could not be selected: ", symbol);
         continue;
      }

      UploadSymbol(symbol);
   }
}

// Market-data bridge only. There are intentionally no OrderSend/OrderClose calls.
void OnTick() {}
