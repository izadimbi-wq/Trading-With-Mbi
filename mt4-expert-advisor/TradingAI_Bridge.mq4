#property strict
#property version   "0.20"
#property description "TradingAI multi-symbol market-data bridge. No order execution."

input string BackendUrl = "https://YOUR_BACKEND_HOST";
input string BridgeToken = "SET_A_LONG_RANDOM_TOKEN";
input int UploadIntervalSeconds = 5;
input int CandleCount = 120;
input ENUM_TIMEFRAMES UploadTimeframe = PERIOD_M5;
input bool SendContractSpecification = true;

datetime lastUpload = 0;

string JsonEscape(string value)
{
   StringReplace(value, "\\", "\\\\");
   StringReplace(value, "\"", "\\\"");
   return value;
}

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

string BuildCandles(string symbol)
{
   string out = "[";
   int total = iBars(symbol, UploadTimeframe);
   int count = MathMin(CandleCount, total - 1); // exclude live candle at index 0
   bool first = true;

   for(int shift = count; shift >= 1; shift--)
   {
      datetime t = iTime(symbol, UploadTimeframe, shift);
      double o = iOpen(symbol, UploadTimeframe, shift);
      double h = iHigh(symbol, UploadTimeframe, shift);
      double l = iLow(symbol, UploadTimeframe, shift);
      double c = iClose(symbol, UploadTimeframe, shift);
      long volume = iVolume(symbol, UploadTimeframe, shift);

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
   double tickSize = MarketInfo(symbol, MODE_TICKSIZE);
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

bool UploadSymbol(string symbol)
{
   if(!IsValidSymbolData(symbol)) return false;

   int digits = (int)MarketInfo(symbol, MODE_DIGITS);
   double bid = MarketInfo(symbol, MODE_BID);
   double ask = MarketInfo(symbol, MODE_ASK);
   string tf = "M5";
   if(UploadTimeframe == PERIOD_M1) tf = "M1";
   else if(UploadTimeframe == PERIOD_M15) tf = "M15";
   else if(UploadTimeframe == PERIOD_M30) tf = "M30";
   else if(UploadTimeframe == PERIOD_H1) tf = "H1";
   else if(UploadTimeframe == PERIOD_H4) tf = "H4";
   else if(UploadTimeframe == PERIOD_D1) tf = "D1";

   string contract = SendContractSpecification ? BuildContract(symbol) : "null";
   string body = StringFormat(
      "{\"symbol\":\"%s\",\"timeframe\":\"%s\",\"bid\":%s,\"ask\":%s,\"candles\":%s,\"contract\":%s}",
      JsonEscape(symbol), tf, Number(bid, digits), Number(ask, digits),
      BuildCandles(symbol), contract
   );

   char post[];
   char result[];
   string headers = "Content-Type: application/json\r\nX-TradingAI-Token: " + BridgeToken + "\r\n";
   StringToCharArray(body, post, 0, WHOLE_ARRAY, CP_UTF8);
   if(ArraySize(post) > 0) ArrayResize(post, ArraySize(post) - 1);

   string responseHeaders;
   ResetLastError();
   int code = WebRequest("POST", BackendUrl + "/api/v1/mt4/market-data",
                         headers, 5000, post, result, responseHeaders);
   if(code == -1)
   {
      Print("TradingAI upload failed for ", symbol, ". Error=", GetLastError(),
            ". Add backend URL to MT4: Tools > Options > Expert Advisors > Allow WebRequest.");
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
   Print("TradingAI multi-symbol bridge initialized. Order execution is DISABLED.");
   return INIT_SUCCEEDED;
}

void OnDeinit(const int reason)
{
   EventKillTimer();
}

void OnTimer()
{
   int total = SymbolsTotal(true); // symbols visible in Market Watch
   for(int i = 0; i < total; i++)
   {
      string symbol = SymbolName(i, true);
      if(symbol == "") continue;
      UploadSymbol(symbol);
   }
}

// This EA sends market data only. It deliberately contains no OrderSend/OrderClose calls.
void OnTick() {}
