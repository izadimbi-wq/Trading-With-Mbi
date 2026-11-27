package com.tradingai.app

import android.graphics.Paint
import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.Canvas
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.runtime.saveable.rememberSaveable
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.foundation.text.KeyboardOptions
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
private const val ACCOUNT_RISK_PERCENT = 1.0

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent { MaterialTheme { TradingDashboard() } }
    }
}

private data class Quote(
    val bid: Double, val ask: Double, val mid: Double, val spread: Double,
    val timestamp: String, val provider: String, val marketState: String,
    val stale: Boolean, val age: String
)

private data class Candle(
    val open: Double, val high: Double, val low: Double, val close: Double,
    val time: String
)

private data class ScreenState(
    val quote: Quote? = null,
    val candles: List<Candle> = emptyList(),
    val analysis: JSONObject? = null,
    val loading: Boolean = true,
    val error: String? = null
)

private enum class DashboardTab(val title: String) {
    SYMBOLS("نمادها"), CHART("نمودار"), ANALYSIS("تحلیل")
}

@Composable
private fun TradingDashboard() {
    var symbol by rememberSaveable { mutableStateOf("XAUUSD") }
    var timeframe by rememberSaveable { mutableStateOf("5m") }
    var balanceText by rememberSaveable { mutableStateOf("50") }
    var selectedTab by rememberSaveable { mutableStateOf(DashboardTab.SYMBOLS) }
    var refresh by remember { mutableIntStateOf(0) }
    var state by remember { mutableStateOf(ScreenState()) }

    val balance = balanceText.trim().replace(',', '.').toDoubleOrNull()
    val validBalance = balance != null && balance.isFinite() && balance > 0.0

    LaunchedEffect(symbol, timeframe, refresh, balanceText) {
        while (isActive) {
            if (!validBalance) {
                state = state.copy(
                    loading = false,
                    analysis = JSONObject()
                        .put("signal", "NO TRADE")
                        .put("signal_status", "INVALID_ACCOUNT_BALANCE")
                        .put("signal_reason", "موجودی باید عددی بزرگ‌تر از صفر باشد.")
                )
            } else {
                try {
                    state = state.copy(loading = state.quote == null, error = null)
                    val newState = withContext(Dispatchers.IO) {
                        loadMarket(symbol, timeframe, balance!!)
                    }
                    state = newState
                } catch (e: CancellationException) {
                    throw e
                } catch (e: Exception) {
                    state = state.copy(
                        loading = false,
                        error = e.message ?: "خطای دریافت اطلاعات"
                    )
                }
            }
            delay(5000)
        }
    }

    Scaffold(
        bottomBar = {
            NavigationBar {
                NavigationBarItem(
                    selected = selectedTab == DashboardTab.SYMBOLS,
                    onClick = { selectedTab = DashboardTab.SYMBOLS },
                    icon = { Text("01", style = MaterialTheme.typography.labelLarge) },
                    label = { Text("نمادها") }
                )
                NavigationBarItem(
                    selected = selectedTab == DashboardTab.CHART,
                    onClick = { selectedTab = DashboardTab.CHART },
                    icon = { Text("02", style = MaterialTheme.typography.labelLarge) },
                    label = { Text("نمودار") }
                )
                NavigationBarItem(
                    selected = selectedTab == DashboardTab.ANALYSIS,
                    onClick = { selectedTab = DashboardTab.ANALYSIS },
                    icon = { Text("03", style = MaterialTheme.typography.labelLarge) },
                    label = { Text("تحلیل") }
                )
            }
        }
    ) { padding ->
        Column(
            Modifier.fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(12.dp)
        ) {
            Row(verticalAlignment = Alignment.CenterVertically) {
                Column(Modifier.weight(1f)) {
                    Text("fxizadi", style = MaterialTheme.typography.headlineMedium)
                    Text("SMART MARKET ANALYSIS")
                }
                Button(onClick = { refresh++ }) { Text("بروزرسانی") }
            }
            HorizontalDivider()

            when (selectedTab) {
                DashboardTab.SYMBOLS -> SymbolsScreen(
                    symbol = symbol,
                    onSymbolChange = { symbol = it },
                    balanceText = balanceText,
                    onBalanceChange = { balanceText = it },
                    validBalance = validBalance,
                    balance = balance,
                    state = state
                )
                DashboardTab.CHART -> ChartScreen(
                    symbol = symbol,
                    timeframe = timeframe,
                    onTimeframeChange = { timeframe = it },
                    state = state
                )
                DashboardTab.ANALYSIS -> AnalysisScreen(
                    symbol = symbol,
                    balanceText = balanceText,
                    balance = balance,
                    state = state
                )
            }

            state.error?.let {
                Text("خطا: $it", color = MaterialTheme.colorScheme.error)
            }
            Text(
                "به‌روزرسانی خودکار هر ۵ ثانیه • سفارش خودکار غیرفعال است",
                style = MaterialTheme.typography.bodySmall
            )
        }
    }
}

@Composable
private fun SymbolsScreen(
    symbol: String,
    onSymbolChange: (String) -> Unit,
    balanceText: String,
    onBalanceChange: (String) -> Unit,
    validBalance: Boolean,
    balance: Double?,
    state: ScreenState
) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("انتخاب نماد", style = MaterialTheme.typography.titleLarge)
                Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                    listOf("XAUUSD", "EURUSD", "XAGUSD").forEach {
                        FilterChip(
                            selected = symbol == it,
                            onClick = { onSymbolChange(it) },
                            label = { Text(it) }
                        )
                    }
                }
            }
        }

        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("مدیریت سرمایه", style = MaterialTheme.typography.titleLarge)
                Text("موجودی حساب (دلار آمریکا)")
                OutlinedTextField(
                    value = balanceText,
                    onValueChange = onBalanceChange,
                    modifier = Modifier.fillMaxWidth(),
                    singleLine = true,
                    keyboardOptions = KeyboardOptions(keyboardType = KeyboardType.Decimal),
                    isError = !validBalance,
                    suffix = { Text("USD") },
                    supportingText = {
                        Text(
                            if (validBalance) {
                                "ریسک هر معامله: ۱٪ • بودجه ریسک: $${
                                    String.format(
                                        Locale.US, "%.2f",
                                        balance!! * ACCOUNT_RISK_PERCENT / 100.0
                                    )
                                }"
                            } else {
                                "موجودی معتبر وارد کنید؛ تحلیل تا آن زمان انجام نمی‌شود."
                            }
                        )
                    }
                )
                Text(
                    "با تغییر موجودی، تحلیل و محاسبات ریسک با مقدار جدید تکرار می‌شود.",
                    style = MaterialTheme.typography.bodySmall
                )
            }
        }

        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("قیمت بازار", style = MaterialTheme.typography.titleLarge)
                if (state.loading && state.quote == null) CircularProgressIndicator()
                state.quote?.let { q ->
                    Text(symbol, style = MaterialTheme.typography.titleMedium)
                    Text(price(symbol, q.mid), style = MaterialTheme.typography.headlineLarge)
                    RowValue("قیمت فروش (Bid)", price(symbol, q.bid), Color(0xFFC62828))
                    RowValue("قیمت خرید (Ask)", price(symbol, q.ask), Color(0xFF16834A))
                    RowValue("Spread", price(symbol, q.spread))
                    RowValue("وضعیت بازار", q.marketState)
                    RowValue("منبع", q.provider)
                    RowValue("سن قیمت (ثانیه)", q.age)
                    Text(
                        if (q.stale) "هشدار: قیمت کهنه است."
                        else "قیمت تازه دریافت شده",
                        color = if (q.stale) MaterialTheme.colorScheme.error
                        else MaterialTheme.colorScheme.primary
                    )
                    Text("زمان: ${q.timestamp}", style = MaterialTheme.typography.bodySmall)
                } ?: Text("قیمت لحظه‌ای در دسترس نیست.")
            }
        }
    }
}

@Composable
private fun ChartScreen(
    symbol: String,
    timeframe: String,
    onTimeframeChange: (String) -> Unit,
    state: ScreenState
) {
    Column(verticalArrangement = Arrangement.spacedBy(12.dp)) {
        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("تایم‌فریم", style = MaterialTheme.typography.titleLarge)
                listOf("1m", "5m", "15m", "30m", "1h", "4h", "1d")
                    .chunked(4).forEach { group ->
                        Row(horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                            group.forEach {
                                FilterChip(
                                    selected = timeframe == it,
                                    onClick = { onTimeframeChange(it) },
                                    label = { Text(it) }
                                )
                            }
                        }
                    }
            }
        }

        Card(Modifier.fillMaxWidth()) {
            Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                Text("نمودار کندل‌استیک", style = MaterialTheme.typography.titleLarge)
                Text("نماد $symbol • تایم‌فریم $timeframe • تعداد کندل: ${state.candles.size}")
                if (state.candles.isNotEmpty()) {
                    CandleChart(
                        state.candles.takeLast(80),
                        Modifier.fillMaxWidth().height(280.dp),
                        symbol
                    )
                    state.candles.last().let {
                        RowValue("Open", price(symbol, it.open))
                        RowValue("High", price(symbol, it.high))
                        RowValue("Low", price(symbol, it.low))
                        RowValue("Close", price(symbol, it.close))
                    }
                } else {
                    Text("کندلی برای رسم نمودار دریافت نشده است.")
                    if (state.loading) CircularProgressIndicator()
                }
            }
        }
    }
}

@Composable
private fun AnalysisScreen(
    symbol: String,
    balanceText: String,
    balance: Double?,
    state: ScreenState
) {
    Card(Modifier.fillMaxWidth()) {
        Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
            Text("تحلیل و سیگنال", style = MaterialTheme.typography.titleLarge)
            Text("نماد: $symbol")
            if (state.loading && state.analysis == null) {
                CircularProgressIndicator()
                Text("در انتظار دریافت سیگنال…")
            } else {
                val a = state.analysis
                if (a == null) {
                    Text("هنوز پاسخی از موتور تحلیل دریافت نشده است.")
                } else {
                    val signal = a.optString("signal", "NO TRADE").uppercase(Locale.US)
                    val plan = a.optJSONObject("trade_plan")
                    val validPlan = plan != null &&
                        plan.optString("status") == "ACCEPT_FOR_REVIEW" &&
                        signal in listOf("BUY", "SELL")

                    if (!validPlan) {
                        Text(
                            "NO TRADE",
                            style = MaterialTheme.typography.headlineMedium,
                            color = MaterialTheme.colorScheme.onSurface
                        )
                    } else {
                        val direction = if (signal == "BUY") "خرید (BUY)" else "فروش (SELL)"
                        val signalColor =
                            if (signal == "BUY") Color(0xFF16834A) else Color(0xFFC62828)
                        val entry = plan!!.optDouble("entry_price", Double.NaN)
                        val stop = plan.optDouble("stop_loss", Double.NaN)
                        val target = plan.optDouble("take_profit", Double.NaN)
                        val lots = plan.opt("lots")?.toString() ?: "—"
                        val risk = a.optJSONObject("account_risk_profile")
                            ?.optString("risk_percent") ?: "—"
                        val ratio = if (
                            entry.isFinite() && stop.isFinite() && target.isFinite() &&
                            kotlin.math.abs(entry - stop) > 0.0
                        ) {
                            String.format(
                                Locale.US,
                                "%.2f : 1",
                                kotlin.math.abs(target - entry) / kotlin.math.abs(entry - stop)
                            )
                        } else "—"
                        val validity = a.optString(
                            "validity_duration",
                            a.optString("valid_for", a.optString("signal_validity", "—"))
                        )

                        Text(
                            direction,
                            style = MaterialTheme.typography.headlineMedium,
                            color = signalColor
                        )
                        HorizontalDivider()
                        RowValue("قیمت ورود", price(symbol, entry))
                        RowValue("حد سود (TP)", price(symbol, target))
                        RowValue("حد ضرر (SL)", price(symbol, stop))
                        RowValue("مدت اعتبار سیگنال", validity)
                        RowValue("حجم معامله", lots)
                        RowValue("درصد ریسک", if (risk == "—") risk else "$risk%")
                        RowValue("نسبت ریسک به بازده", ratio)
                    }
                }
            }
        }
    }
}

@Composable
private fun CandleChart(candles: List<Candle>, modifier: Modifier, symbol: String) {
    if (candles.isEmpty()) return
    Canvas(modifier) {
        val left = 8f
        val right = size.width - 8f
        val top = 18f
        val bottom = size.height - 22f
        val minValue = candles.minOf { it.low }
        val maxValue = candles.maxOf { it.high }
        val range = (maxValue - minValue).takeIf { it > 0.0 } ?: 1.0
        fun y(v: Double) = bottom - ((v - minValue) / range).toFloat() * (bottom - top)
        val slot = (right - left) / candles.size
        val bodyWidth = (slot * 0.62f).coerceAtLeast(2f)

        drawLine(Color.LightGray, Offset(left, bottom), Offset(right, bottom), 1f)
        candles.forEachIndexed { index, candle ->
            val x = left + slot * (index + 0.5f)
            val color = if (candle.close >= candle.open) Color(0xFF159957)
            else Color(0xFFD64545)
            drawLine(color, Offset(x, y(candle.high)), Offset(x, y(candle.low)), 1.5f)
            val yOpen = y(candle.open)
            val yClose = y(candle.close)
            drawRect(
                color,
                Offset(x - bodyWidth / 2f, minOf(yOpen, yClose)),
                androidx.compose.ui.geometry.Size(
                    bodyWidth,
                    maxOf(kotlin.math.abs(yClose - yOpen), 2f)
                )
            )
        }
        val paint = Paint().apply {
            color = android.graphics.Color.GRAY
            textSize = 10f
            isAntiAlias = true
        }
        drawContext.canvas.nativeCanvas.drawText(price(symbol, maxValue), left, 12f, paint)
        drawContext.canvas.nativeCanvas.drawText(
            price(symbol, minValue), left, size.height - 3f, paint
        )
    }
}

@Composable
private fun RowValue(
    label: String,
    value: String,
    valueColor: Color = MaterialTheme.colorScheme.onSurface
) {
    Row(
        Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(label)
        Text(value, color = valueColor)
    }
}

private fun price(symbol: String, value: Double): String {
    if (!value.isFinite()) return "—"
    val decimals = when (symbol) {
        "XAUUSD" -> 2
        "XAGUSD" -> 3
        else -> 5
    }
    return String.format(Locale.US, "%.${decimals}f", value)
}

private fun timeframeCode(interval: String) = when (interval) {
    "1m" -> "M1"
    "5m" -> "M5"
    "15m" -> "M15"
    "30m" -> "M30"
    "1h" -> "H1"
    "4h" -> "H4"
    "1d" -> "D1"
    else -> "M5"
}

private fun loadMarket(
    symbol: String,
    timeframe: String,
    accountBalance: Double
): ScreenState {
    var quote: Quote? = null
    var candles: List<Candle> = emptyList()
    var analysis: JSONObject? = null
    val errors = mutableListOf<String>()

    try {
        val tick = getJson("$API_BASE/api/v1/market/$symbol/tick")
        val bid = tick.optDouble("bid", Double.NaN)
        val ask = tick.optDouble("ask", Double.NaN)
        val mid = tick.optDouble("mid", Double.NaN)
        val spread = tick.optDouble("spread", Double.NaN)
        if (bid.isFinite() && ask.isFinite() && mid.isFinite() && spread.isFinite()) {
            quote = Quote(
                bid, ask, mid, spread,
                tick.optString("timestamp", "—"),
                tick.optString("provider", tick.optString("source", "—")),
                tick.optString("market_state", "—"),
                tick.optBoolean("stale", true),
                tick.opt("quote_age_seconds")?.toString() ?: "—"
            )
        } else errors.add("پاسخ قیمت ناقص است.")
    } catch (e: Exception) {
        errors.add("قیمت: ${e.message ?: "خطای دریافت"}")
    }

    val requestCandles = JSONArray()
    try {
        val response = getJson(
            "$API_BASE/api/v1/market/$symbol/ohlc?interval=$timeframe&limit=100"
        )
        val bars = response.optJSONArray("bars")
            ?: response.optJSONArray("candles")
            ?: response.optJSONArray("data")
            ?: JSONArray()
        val parsed = mutableListOf<Candle>()

        for (i in 0 until bars.length()) {
            val bar = bars.optJSONObject(i) ?: continue
            if (bar.optBoolean("isOpen", bar.optBoolean("is_open", false))) continue
            val o = bar.optDouble("open", Double.NaN)
            val h = bar.optDouble("high", Double.NaN)
            val l = bar.optDouble("low", Double.NaN)
            val c = bar.optDouble("close", Double.NaN)
            if (!o.isFinite() || !h.isFinite() || !l.isFinite() || !c.isFinite()) continue
            if (h < maxOf(o, c) || l > minOf(o, c) || h < l) continue

            parsed.add(
                Candle(
                    o, h, l, c,
                    bar.optString("time", bar.optString("timestamp", "—"))
                )
            )
            requestCandles.put(
                JSONObject()
                    .put("open", o)
                    .put("high", h)
                    .put("low", l)
                    .put("close", c)
            )
        }
        candles = parsed
        if (candles.isEmpty()) errors.add("کندل معتبر در پاسخ سرور پیدا نشد.")
    } catch (e: Exception) {
        errors.add("کندل: ${e.message ?: "خطای دریافت"}")
    }

    if (requestCandles.length() > 0) {
        try {
            val payload = JSONObject()
                .put("symbol", symbol)
                .put("timeframe", timeframeCode(timeframe))
                .put("candles", requestCandles)
                .put("balance", accountBalance)
                .put("risk_percent", ACCOUNT_RISK_PERCENT)
            analysis = postJson("$API_BASE/api/v1/analysis", payload)
        } catch (e: Exception) {
            errors.add("تحلیل: ${e.message ?: "خطای تحلیل"}")
            analysis = JSONObject()
                .put("signal", "NO TRADE")
                .put("signal_status", "ANALYSIS_REQUEST_FAILED")
                .put("signal_reason", e.message ?: "ارتباط با موتور تحلیل برقرار نشد.")
        }
    } else {
        analysis = JSONObject()
            .put("signal", "NO TRADE")
            .put("signal_status", "NO_VALID_CANDLES")
            .put("signal_reason", "هیچ کندل معتبر بسته‌شده‌ای برای تحلیل دریافت نشد.")
    }

    return ScreenState(
        quote = quote,
        candles = candles,
        analysis = analysis,
        loading = false,
        error = errors.takeIf { it.isNotEmpty() }?.joinToString(" | ")
    )
}

private fun getJson(url: String) = requestJson(url, "GET", null)
private fun postJson(url: String, body: JSONObject) = requestJson(url, "POST", body)

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
            connection.outputStream.use {
                it.write(body.toString().toByteArray(Charsets.UTF_8))
            }
        }
        val code = connection.responseCode
        val stream = if (code in 200..299) connection.inputStream else connection.errorStream
        val response = stream?.bufferedReader(Charsets.UTF_8)?.use { it.readText() } ?: ""
        if (code !in 200..299) throw IllegalStateException("HTTP $code: $response")
        return JSONObject(response)
    } finally {
        connection.disconnect()
    }
}
