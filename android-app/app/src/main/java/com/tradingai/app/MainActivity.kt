package com.tradingai.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Modifier
import androidx.compose.ui.text.input.KeyboardOptions
import androidx.compose.ui.text.input.KeyboardType
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.CancellationException
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.withContext
import org.json.JSONArray
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.Locale

private const val API_BASE = "https://trading-with-mbi-3.onrender.com"
private const val RISK_PERCENT = 1.0

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MaterialTheme { TradingDashboard() } }
    }
}

private data class MarketState(
    val bid: Double? = null,
    val ask: Double? = null,
    val mid: Double? = null,
    val spread: Double? = null,
    val stale: Boolean = true,
    val age: String = "—",
    val provider: String = "—",
    val timestamp: String = "—",
    val candles: Int = 0,
    val analysis: JSONObject? = null,
    val loading: Boolean = true,
    val error: String? = null
)

@Composable
private fun TradingDashboard() {
    var symbol by rememberSaveable { mutableStateOf("XAUUSD") }
    var timeframe by rememberSaveable { mutableStateOf("5m") }
    var balanceText by rememberSaveable { mutableStateOf("50") }
    var refresh by remember { mutableIntStateOf(0) }
    var tab by rememberSaveable { mutableStateOf(0) }
    var market by remember { mutableStateOf(MarketState()) }
    val balance = balanceText.trim().replace(',', '.').toDoubleOrNull()
    val validBalance = balance != null && balance.isFinite() && balance > 0.0

    LaunchedEffect(symbol, timeframe, balanceText, refresh) {
        while (isActive) {
            if (!validBalance) {
                market = market.copy(loading = false, analysis = JSONObject()
                    .put("signal", "NO TRADE")
                    .put("signal_status", "INVALID_ACCOUNT_BALANCE")
                    .put("signal_reason", "موجودی حساب باید عددی بزرگ‌تر از صفر باشد."))
            } else {
                market = market.copy(loading = true, error = null)
                try {
                    market = withContext(Dispatchers.IO) {
                        loadMarket(symbol, timeframe, balance!!)
                    }
                } catch (e: CancellationException) {
                    throw e
                } catch (e: Exception) {
                    market = market.copy(loading = false, error = e.message ?: "خطای دریافت اطلاعات")
                }
            }
            delay(5000)
        }
    }

    Scaffold(bottomBar = {
        NavigationBar {
            NavigationBarItem(selected = tab == 0, onClick = { tab = 0 },
                icon = { Text("01") }, label = { Text("بازار") })
            NavigationBarItem(selected = tab == 1, onClick = { tab = 1 },
                icon = { Text("02") }, label = { Text("تحلیل") })
        }
    }) { padding ->
        Column(Modifier.fillMaxSize().padding(padding).verticalScroll(rememberScrollState()).padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)) {
            Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
                Column {
                    Text("Trading With Mbi", style = MaterialTheme.typography.headlineSmall)
                    Text("SMART MARKET ANALYSIS")
                }
                Button(onClick = { refresh++ }) { Text("به‌روزرسانی") }
            }
            HorizontalDivider()
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("انتخاب نماد", style = MaterialTheme.typography.titleMedium)
                    Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                        listOf("XAUUSD", "XAGUSD", "EURUSD").forEach { item ->
                            FilterChip(selected = symbol == item, onClick = { symbol = item }, label = { Text(item) })
                        }
                    }
                    Text("تایم‌فریم")
                    Row(horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                        listOf("1m", "5m", "15m", "30m", "1h", "4h", "1d").forEach { item ->
                            FilterChip(selected = timeframe == item, onClick = { timeframe = item }, label = { Text(item) })
                        }
                    }
                }
            }
            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("مدیریت سرمایه", style = MaterialTheme.typography.titleMedium)
                    OutlinedTextField(value = balanceText, onValueChange = { balanceText = it },
                        modifier = Modifier.fillMaxWidth(), singleLine = true,
                        keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                        label = { Text("موجودی حساب (USD)") }, isError = !validBalance)
                    Text(if (validBalance) "ریسک هر معامله: ۱٪ | بودجه ریسک: ${usd(balance!! * RISK_PERCENT / 100)}"
                        else "موجودی معتبر وارد کنید.", style = MaterialTheme.typography.bodySmall)
                }
            }
            if (tab == 0) {
                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
                        Text("قیمت لحظه‌ای $symbol", style = MaterialTheme.typography.titleLarge)
                        Text(market.mid?.let { fmt(symbol, it) } ?: "—", style = MaterialTheme.typography.headlineLarge)
                        ValueRow("قیمت فروش / Bid", market.bid?.let { fmt(symbol, it) } ?: "—")
                        ValueRow("قیمت خرید / Ask", market.ask?.let { fmt(symbol, it) } ?: "—")
                        ValueRow("فاصله قیمت / Spread", market.spread?.let { fmt(symbol, it) } ?: "—")
                        ValueRow("منبع", market.provider)
                        ValueRow("سن قیمت (ثانیه)", market.age)
                        ValueRow("زمان", market.timestamp)
                        Text(if (market.stale) "هشدار: قیمت کهنه یا تأییدنشده است." else "قیمت تازه دریافت شده",
                            color = if (market.stale) MaterialTheme.colorScheme.error else MaterialTheme.colorScheme.primary)
                    }
                }
            } else {
                AnalysisPanel(symbol, balance, market)
            }
            if (market.loading) LinearProgressIndicator(Modifier.fillMaxWidth())
            market.error?.let { Text("خطا: $it", color = MaterialTheme.colorScheme.error) }
            Text("تعداد کندل‌های دریافت‌شده: ${market.candles} | به‌روزرسانی هر ۵ ثانیه",
                style = MaterialTheme.typography.bodySmall)
            Text("این برنامه فقط تحلیل و سیگنال ارائه می‌کند؛ سفارش باید دستی در MT4 ثبت شود.",
                style = MaterialTheme.typography.bodySmall)
        }
    }
}

@Composable
private fun AnalysisPanel(symbol: String, balance: Double?, market: MarketState) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(7.dp)) {
            Text("سیگنال معاملاتی", style = MaterialTheme.typography.titleLarge)
            val a = market.analysis
            if (a == null) {
                Text("در انتظار پاسخ موتور تحلیل…")
                return@Column
            }
            val signal = a.optString("signal", "NO TRADE")
            Text(signal, style = MaterialTheme.typography.headlineLarge,
                color = when (signal) {
                    "BUY" -> MaterialTheme.colorScheme.primary
                    "SELL" -> MaterialTheme.colorScheme.error
                    else -> MaterialTheme.colorScheme.onSurface
                })
            ValueRow("وضعیت", a.optString("signal_status", "نامشخص"))
            Text("دلیل: ${a.optString("signal_reason", "—")}")
            HorizontalDivider()
            ValueRow("قیمت خرید (Ask)", a.optDouble("ask", Double.NaN).takeIf { it.isFinite() }?.let { fmt(symbol, it) } ?: "—")
            ValueRow("قیمت فروش (Bid)", a.optDouble("bid", Double.NaN).takeIf { it.isFinite() }?.let { fmt(symbol, it) } ?: "—")
            val entry = when (signal) {
                "BUY" -> a.optDouble("ask", Double.NaN)
                "SELL" -> a.optDouble("bid", Double.NaN)
                else -> Double.NaN
            }
            ValueRow("قیمت ورود پیشنهادی", fmt(symbol, entry))
            ValueRow("نوع قیمت ورود", when (signal) { "BUY" -> "Ask"; "SELL" -> "Bid"; else -> "—" })
            ValueRow("روند", a.optString("trend", "نامشخص"))
            a.optJSONObject("indicators")?.let { indicators ->
                Text("اندیکاتورها", style = MaterialTheme.typography.titleMedium)
                indicators.optJSONObject("rsi")?.let { ValueRow("RSI", it.optString("value", "—")) }
                indicators.optJSONObject("atr")?.let { ValueRow("ATR", it.optString("value", "—")) }
                indicators.optJSONObject("ema")?.let {
                    ValueRow("EMA سریع", it.optString("fast", "—")); ValueRow("EMA کند", it.optString("slow", "—"))
                }
            }
            a.optJSONObject("account_risk_profile")?.let {
                HorizontalDivider()
                Text("مدیریت ریسک", style = MaterialTheme.typography.titleMedium)
                ValueRow("موجودی", "$" + it.optString("balance_usd", balance?.toString() ?: "—"))
                ValueRow("ریسک", it.optString("risk_percent", "1") + "%")
                ValueRow("بودجه ریسک", "$" + it.optString("risk_budget_usd", "—"))
            }
            a.optJSONObject("trade_plan")?.let { plan ->
                HorizontalDivider()
                Text("طرح معامله", style = MaterialTheme.typography.titleMedium)
                ValueRow("وضعیت", plan.optString("status", "نامشخص"))
                if (plan.optString("status") == "ACCEPT_FOR_REVIEW") {
                    ValueRow("حد ضرر", fmt(symbol, plan.optDouble("stop_loss", Double.NaN)))
                    ValueRow("حد سود", fmt(symbol, plan.optDouble("take_profit", Double.NaN)))
                    ValueRow("حجم مجاز", plan.optString("lots", "—"))
                    ValueRow("ریسک برآوردی", "$" + plan.optString("estimated_risk", "—"))
                } else {
                    Text(plan.optString("reason", "حجم معامله تا تأیید مشخصات قرارداد بروکر مسدود است."))
                }
            }
            if (signal == "BUY" || signal == "SELL") {
                Text("تأیید نهایی قیمت، حد ضرر و حجم پیش از ثبت دستی سفارش در MT4 الزامی است.",
                    style = MaterialTheme.typography.bodySmall)
            }
        }
    }
}

@Composable
private fun ValueRow(label: String, value: String) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween) {
        Text(label); Text(value)
    }
}

private fun loadMarket(symbol: String, timeframe: String, balance: Double): MarketState {
    val tick = runCatching { getJson("$API_BASE/api/v1/market/$symbol/tick") }.getOrNull()
    val candlesResponse = getJson("$API_BASE/api/v1/market/$symbol/ohlc?interval=$timeframe&limit=100")
    val bars = candlesResponse.optJSONArray("bars") ?: JSONArray()
    val candles = JSONArray()
    for (i in 0 until bars.length()) {
        val b = bars.optJSONObject(i) ?: continue
        if (b.optBoolean("isOpen", b.optBoolean("is_open", false))) continue
        val o = b.optDouble("open", Double.NaN); val h = b.optDouble("high", Double.NaN)
        val l = b.optDouble("low", Double.NaN); val c = b.optDouble("close", Double.NaN)
        if (!o.isFinite() || !h.isFinite() || !l.isFinite() || !c.isFinite()) continue
        if (h < maxOf(o, c) || l > minOf(o, c) || h < l) continue
        candles.put(JSONObject().put("open", o).put("high", h).put("low", l).put("close", c))
    }
    val analysis = if (candles.length() > 0) {
        val body = JSONObject().put("symbol", symbol).put("timeframe", timeframeCode(timeframe))
            .put("candles", candles).put("balance", balance).put("risk_percent", RISK_PERCENT)
        runCatching { postJson("$API_BASE/api/v1/analysis", body) }.getOrElse { e ->
            JSONObject().put("signal", "NO TRADE").put("signal_status", "ANALYSIS_REQUEST_FAILED")
                .put("signal_reason", e.message ?: "خطای ارتباط با موتور تحلیل")
        }
    } else JSONObject().put("signal", "NO TRADE").put("signal_status", "NO_VALID_CANDLES")
        .put("signal_reason", "کندل بسته‌شده معتبر دریافت نشد.")

    return MarketState(
        bid = tick?.optDouble("bid")?.takeIf { it.isFinite() },
        ask = tick?.optDouble("ask")?.takeIf { it.isFinite() },
        mid = tick?.optDouble("mid")?.takeIf { it.isFinite() },
        spread = tick?.optDouble("spread")?.takeIf { it.isFinite() },
        stale = tick?.optBoolean("stale", true) != false,
        age = tick?.opt("quote_age_seconds")?.toString() ?: "—",
        provider = tick?.optString("provider", "—") ?: "—",
        timestamp = tick?.optString("timestamp", "—") ?: "—",
        candles = candles.length(), analysis = analysis, loading = false
    )
}

private fun getJson(url: String): JSONObject = requestJson(url, "GET", null)
private fun postJson(url: String, body: JSONObject): JSONObject = requestJson(url, "POST", body)

private fun requestJson(url: String, method: String, body: JSONObject?): JSONObject {
    val connection = URL(url).openConnection() as HttpURLConnection
    try {
        connection.requestMethod = method
        connection.connectTimeout = 15000
        connection.readTimeout = 20000
        connection.setRequestProperty("Accept", "application/json")
        if (body != null) {
            connection.doOutput = true
            connection.setRequestProperty("Content-Type", "application/json; charset=utf-8")
            connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
        }
        val code = connection.responseCode
        val stream = if (code in 200..299) connection.inputStream else connection.errorStream
        val response = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() } ?: ""
        if (code !in 200..299) throw IllegalStateException("HTTP $code: $response")
        return JSONObject(response)
    } finally { connection.disconnect() }
}

private fun timeframeCode(value: String): String = when (value) {
    "1m" -> "M1"; "5m" -> "M5"; "15m" -> "M15"; "30m" -> "M30"
    "1h" -> "H1"; "4h" -> "H4"; "1d" -> "D1"; else -> "M5"
}

private fun fmt(symbol: String, value: Double): String {
    if (!value.isFinite()) return "—"
    val decimals = when (symbol) { "XAUUSD" -> 2; "XAGUSD" -> 3; else -> 5 }
    return String.format(Locale.US, "%.${decimals}f", value)
}

private fun usd(value: Double) = "$" + String.format(Locale.US, "%.2f", value)
