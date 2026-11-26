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
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.geometry.Offset
import androidx.compose.ui.graphics.Color
import androidx.compose.ui.graphics.nativeCanvas
import androidx.compose.ui.unit.dp
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

@Composable
private fun TradingDashboard() {
    var symbol by remember { mutableStateOf("XAUUSD") }
    var timeframe by remember { mutableStateOf("5m") }
    var refresh by remember { mutableIntStateOf(0) }
    var state by remember { mutableStateOf(ScreenState()) }

    LaunchedEffect(symbol, timeframe, refresh) {
        while (isActive) {
            try {
                state = state.copy(loading = state.quote == null, error = null)
                state = withContext(Dispatchers.IO) { loadMarket(symbol, timeframe) }
            } catch (e: Exception) {
                state = state.copy(loading = false, error = e.message ?: "خطای دریافت اطلاعات")
            }
            delay(5000)
        }
    }

    Scaffold { padding ->
        Column(
            Modifier.fillMaxSize().padding(padding).verticalScroll(rememberScrollState()).padding(16.dp),
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
            Text("نماد")
            Row(horizontalArrangement = Arrangement.spacedBy(6.dp)) {
                listOf("XAUUSD", "EURUSD", "XAGUSD").forEach {
                    FilterChip(symbol == it, { symbol = it }, label = { Text(it) })
                }
            }
            Text("تایم‌فریم")
            Column(verticalArrangement = Arrangement.spacedBy(5.dp)) {
                listOf("1m", "5m", "15m", "30m", "1h", "4h", "1d").chunked(4).forEach { group ->
                    Row(horizontalArrangement = Arrangement.spacedBy(5.dp)) {
                        group.forEach {
                            FilterChip(timeframe == it, { timeframe = it }, label = { Text(it) })
                        }
                    }
                }
            }

            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("قیمت بازار", style = MaterialTheme.typography.titleLarge)
                    if (state.loading && state.quote == null) CircularProgressIndicator()
                    state.quote?.let { q ->
                        Text(symbol, style = MaterialTheme.typography.titleMedium)
                        Text(price(symbol, q.mid), style = MaterialTheme.typography.headlineLarge)
                        RowValue("Bid", price(symbol, q.bid))
                        RowValue("Ask", price(symbol, q.ask))
                        RowValue("Spread", price(symbol, q.spread))
                        RowValue("وضعیت بازار", q.marketState)
                        RowValue("منبع", q.provider)
                        RowValue("سن قیمت (ثانیه)", q.age)
                        Text(if (q.stale) "هشدار: قیمت کهنه است؛ تحلیل معتبر نیست." else "قیمت تازه دریافت شده")
                        Text("زمان: ${q.timestamp}", style = MaterialTheme.typography.bodySmall)
                    }
                }
            }

            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(12.dp), verticalArrangement = Arrangement.spacedBy(8.dp)) {
                    Text("نمودار کندل‌استیک", style = MaterialTheme.typography.titleLarge)
                    Text("تایم‌فریم $timeframe • تعداد کندل: ${state.candles.size}")
                    if (state.candles.isNotEmpty()) {
                        CandleChart(state.candles.takeLast(80), Modifier.fillMaxWidth().height(260.dp), symbol)
                        state.candles.last().let {
                            RowValue("Open", price(symbol, it.open))
                            RowValue("High", price(symbol, it.high))
                            RowValue("Low", price(symbol, it.low))
                            RowValue("Close", price(symbol, it.close))
                        }
                    } else Text("کندلی برای رسم نمودار دریافت نشده است.")
                }
            }

            Card(Modifier.fillMaxWidth()) {
                Column(Modifier.padding(14.dp), verticalArrangement = Arrangement.spacedBy(6.dp)) {
                    Text("تحلیل و سیگنال", style = MaterialTheme.typography.titleLarge)
                    val a = state.analysis
                    if (a == null) Text("در انتظار تحلیل کندل‌ها…")
                    else {
                        val signal = a.optString("signal", "NO TRADE")
                        Text(
                            signal, style = MaterialTheme.typography.headlineMedium,
                            color = when (signal) {
                                "BUY" -> Color(0xFF16834A)
                                "SELL" -> Color(0xFFC62828)
                                else -> MaterialTheme.colorScheme.onSurface
                            }
                        )
                        RowValue("وضعیت", a.optString("signal_status", a.optString("status", "نامشخص")))
                        Text("دلیل: ${a.optString("signal_reason", "—")}")
                        RowValue("روند", a.optString("trend", "نامشخص"))
                        a.optJSONObject("indicators")?.let { indicators ->
                            indicators.optJSONObject("rsi")?.let { RowValue("RSI", it.optString("value", "—")) }
                            indicators.optJSONObject("atr")?.let { RowValue("ATR", it.optString("value", "—")) }
                            indicators.optJSONObject("ema")?.let {
                                RowValue("EMA سریع", it.optString("fast", "—"))
                                RowValue("EMA کند", it.optString("slow", "—"))
                            }
                        }
                        a.optJSONObject("support_resistance")?.let { Text("حمایت و مقاومت: $it") }
                        a.optJSONObject("pullback")?.let { Text("محدوده اصلاح: $it") }
                        a.optJSONObject("trade_plan")?.let { Text("برنامه ریسک: $it") }
                    }
                    Text("این برنامه سفارش به بروکر ارسال نمی‌کند. سیگنال تضمین سود نیست.",
                        style = MaterialTheme.typography.bodySmall)
                }
            }
            state.error?.let { Text("خطا: $it", color = MaterialTheme.colorScheme.error) }
            Text("به‌روزرسانی خودکار هر ۵ ثانیه", style = MaterialTheme.typography.bodySmall)
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
        val min = candles.minOf { it.low }
        val max = candles.maxOf { it.high }
        val range = (max - min).takeIf { it > 0.0 } ?: 1.0
        fun y(v: Double) = bottom - ((v - min) / range).toFloat() * (bottom - top)
        val slot = (right - left) / candles.size
        val bodyWidth = (slot * 0.62f).coerceAtLeast(2f)

        drawLine(Color.LightGray, Offset(left, bottom), Offset(right, bottom), 1f)
        candles.forEachIndexed { index, candle ->
            val x = left + slot * (index + 0.5f)
            val up = candle.close >= candle.open
            val color = if (up) Color(0xFF159957) else Color(0xFFD64545)
            drawLine(color, Offset(x, y(candle.high)), Offset(x, y(candle.low)), 1.5f)
            val yOpen = y(candle.open)
            val yClose = y(candle.close)
            drawRect(
                color,
                Offset(x - bodyWidth / 2f, minOf(yOpen, yClose)),
                androidx.compose.ui.geometry.Size(bodyWidth, maxOf(kotlin.math.abs(yClose - yOpen), 2f))
            )
        }
        val paint = Paint().apply { color = android.graphics.Color.GRAY; textSize = 10f; isAntiAlias = true }
        drawContext.canvas.nativeCanvas.drawText(price(symbol, max), left, 12f, paint)
        drawContext.canvas.nativeCanvas.drawText(price(symbol, min), left, size.height - 3f, paint)
    }
}

@Composable
private fun RowValue(label: String, value: String) {
    Row(Modifier.fillMaxWidth(), horizontalArrangement = Arrangement.SpaceBetween, verticalAlignment = Alignment.CenterVertically) {
        Text(label)
        Text(value)
    }
}

private fun price(symbol: String, value: Double): String {
    val decimals = when (symbol) { "XAUUSD" -> 2; "XAGUSD" -> 3; else -> 5 }
    return String.format(Locale.US, "%.${decimals}f", value)
}

private fun timeframeCode(interval: String) = when (interval) {
    "1m" -> "M1"; "5m" -> "M5"; "15m" -> "M15"; "30m" -> "M30"
    "1h" -> "H1"; "4h" -> "H4"; "1d" -> "D1"; else -> "M5"
}

private fun loadMarket(symbol: String, timeframe: String): ScreenState {
    val tick = getJson("$API_BASE/api/v1/market/$symbol/tick")
    val quote = Quote(
        tick.getDouble("bid"), tick.getDouble("ask"), tick.getDouble("mid"), tick.getDouble("spread"),
        tick.optString("timestamp", "—"), tick.optString("provider", "—"),
        tick.optString("market_state", "—"), tick.optBoolean("stale", true),
        tick.opt("quote_age_seconds")?.toString() ?: "—"
    )
    val response = getJson("$API_BASE/api/v1/market/$symbol/ohlc?interval=$timeframe&limit=100")
    val bars = response.optJSONArray("bars") ?: JSONArray()
    val candles = mutableListOf<Candle>()
    val requestCandles = JSONArray()

    for (i in 0 until bars.length()) {
        val bar = bars.optJSONObject(i) ?: continue
        if (bar.optBoolean("isOpen", false)) continue
        val o = bar.optDouble("open", Double.NaN)
        val h = bar.optDouble("high", Double.NaN)
        val l = bar.optDouble("low", Double.NaN)
        val c = bar.optDouble("close", Double.NaN)
        if (!o.isFinite() || !h.isFinite() || !l.isFinite() || !c.isFinite()) continue
        if (h < maxOf(o, c) || l > minOf(o, c) || h < l) continue
        candles.add(Candle(o, h, l, c, bar.optString("time", bar.optString("timestamp", "—"))))
        requestCandles.put(JSONObject().put("open", o).put("high", h).put("low", l).put("close", c))
    }

    val analysis = if (!quote.stale && requestCandles.length() > 0) {
        postJson("$API_BASE/api/v1/analysis", JSONObject()
            .put("symbol", symbol)
            .put("timeframe", timeframeCode(timeframe))
            .put("candles", requestCandles))
    } else {
        JSONObject().put("signal", "NO TRADE")
            .put("signal_status", "STALE_OR_MISSING_DATA")
            .put("signal_reason", "قیمت کهنه است یا کندل معتبر دریافت نشده است.")
    }
    return ScreenState(quote, candles, analysis, false, null)
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
            connection.outputStream.use { it.write(body.toString().toByteArray(Charsets.UTF_8)) }
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
