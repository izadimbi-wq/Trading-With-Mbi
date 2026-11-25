#property strict
#property version   "0.10"
#property description "TradingAI demo-first bridge skeleton. No order execution."

input bool EnableHeartbeat = false;
input int HeartbeatSeconds = 30;

datetime lastHeartbeat = 0;

int OnInit()
{
   Print("TradingAI bridge initialized. Order execution is DISABLED.");
   return(INIT_SUCCEEDED);
}

void OnTick()
{
   if(!EnableHeartbeat) return;
   if(TimeCurrent() - lastHeartbeat < HeartbeatSeconds) return;

   lastHeartbeat = TimeCurrent();

   // Integration TODO:
   // Send authenticated HTTPS heartbeat/market snapshot to your own backend.
   // Do not send account passwords or investor/master credentials.
   // Implement TLS endpoint allow-list, token rotation, request signing,
   // unique message IDs, timestamp validation and replay protection.
   Print("TradingAI heartbeat: ", Symbol(),
         " Bid=", DoubleToString(Bid, Digits),
         " Ask=", DoubleToString(Ask, Digits),
         " Time=", TimeToString(TimeCurrent(), TIME_DATE|TIME_SECONDS));
}

// Deliberately no OrderSend() implementation in this starter.
