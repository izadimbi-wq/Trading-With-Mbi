
package com.tradingai.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.layout.*
import androidx.compose.foundation.rememberScrollState
import androidx.compose.foundation.verticalScroll
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.unit.dp
import kotlinx.coroutines.Dispatchers
import kotlinx.coroutines.delay
import kotlinx.coroutines.isActive
import kotlinx.coroutines.withContext
import org.json.JSONObject
import java.net.HttpURLConnection
import java.net.URL
import java.util.Locale

private const val API_BASE =
    "https://trading-with-mbi-3.onrender.com"

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)

        setContent {
            MaterialTheme {
                TradingDashboard()
            }
        }
    }
}

data class MarketQuote(
    val bid: Double,
    val ask: Double,
    val mid: Double,
    val spread: Double,
    val timestamp: String,
    val source: String,
    val provider: String,
    val marketState: String,
    val stale: Boolean,
    val quoteAge: String
)

data class CandleSummary(
    val open: Double,
    val high: Double,
    val low: Double,
    val close: Double,
    val time: String
)

data class MarketScreenState(
    val quote: MarketQuote? = null,
    val candle: CandleSummary? = null,
    val candleCount: Int = 0,
    val loading: Boolean = true,
    val error: String? = null,
    val lastUpdate: String = ""
)

@Composable
fun TradingDashboard() {
    var symbol by remember { mutableStateOf("XAUUSD") }
    var timeframe by remember { mutableStateOf("5m") }

    var state by remember {
        mutableStateOf(MarketScreenState())
    }

    var refreshKey by remember {
        mutableIntStateOf(0)
    }

    LaunchedEffect(symbol, timeframe, refreshKey) {
        while (isActive) {
            try {
                state = state.copy(
                    loading = state.quote == null,
                    error = null
                )

                val result = withContext(Dispatchers.IO) {
                    fetchMarketData(symbol, timeframe)
                }

                state = result
            } catch (e: Exception) {
                state = state.copy(
                    loading = false,
                    error = e.message ?: "خطا در دریافت اطلاعات بازار"
                )
            }

            delay(5000)
        }
    }

    Scaffold { padding ->
        Column(
            modifier = Modifier
                .fillMaxSize()
                .padding(padding)
                .verticalScroll(rememberScrollState())
                .padding(16.dp),
            verticalArrangement = Arrangement.spacedBy(14.dp)
        ) {

            Row(
                verticalAlignment = Alignment.CenterVertically,
                horizontalArrangement = Arrangement.spacedBy(12.dp)
            ) {
                Column(modifier = Modifier.weight(1f)) {
                    Text(
                        "fxizadi",
                        style = MaterialTheme.typography.headlineMedium
                    )
                    Text("SMART MARKET ANALYSIS")
                }

                Button(
                    onClick = { refreshKey++ }
                ) {
                    Text("بروزرسانی")
                }
            }

            HorizontalDivider()

            Text(
                "انتخاب نماد",
                style = MaterialTheme.typography.titleMedium
            )

            Row(
                horizontalArrangement = Arrangement.spacedBy(8.dp)
            ) {
                listOf("XAUUSD", "EURUSD", "XAGUSD").forEach {
                    FilterChip(
                        selected = symbol == it,
                        onClick = { symbol = it },
                        label = { Text(it) }
                    )
                }
            }

            Text(
                "تایم‌فریم",
                style = MaterialTheme.typography.titleMedium
            )

            val timeframes = listOf(
                "1m", "5m", "15m", "30m",
                "1h", "4h", "1d"
            )

            Column(
                verticalArrangement = Arrangement.spacedBy(6.dp)
            ) {
                timeframes.chunked(4).forEach { group ->
                    Row(
                        horizontalArrangement = Arrangement.spacedBy(6.dp)
                    ) {
                        group.forEach { tf ->
                            FilterChip(
                                selected = timeframe == tf,
                                onClick = { timeframe = tf },
                                label = { Text(tf) }
                            )
                        }
                    }
                }
            }

            Card(
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(10.dp)
                ) {
                    Text(
                        "قیمت بازار",
                        style = MaterialTheme.typography.titleLarge
                    )

                    if (state.loading && state.quote == null) {
                        CircularProgressIndicator()
                    }

                    state.quote?.let { quote ->

                        Text(
                            symbol,
                            style = MaterialTheme.typography.titleMedium
                        )

                        Text(
                            formatPrice(symbol, quote.mid),
                            style = MaterialTheme.typography.headlineLarge
                        )

                        HorizontalDivider()

                        PriceRow("Bid", formatPrice(symbol, quote.bid))
                        PriceRow("Ask", formatPrice(symbol, quote.ask))
                        PriceRow("Mid", formatPrice(symbol, quote.mid))
                        PriceRow("Spread", formatPrice(symbol, quote.spread))

                        PriceRow("وضعیت بازار", quote.marketState)
                        PriceRow("منبع داده", quote.provider)
                        PriceRow("منبع قیمت", quote.source)
                        PriceRow("سن قیمت", quote.quoteAge)

                        if (quote.stale) {
                            Text(
                                "هشدار: داده بازار قدیمی است؛ از آن برای تصمیم معاملاتی استفاده نکن.",
                                color = MaterialTheme.colorScheme.error
                            )
                        } else {
                            Text(
                                "داده دریافتی به‌عنوان قیمت غیرقدیمی گزارش شده است.",
                                color = MaterialTheme.colorScheme.primary
                            )
                        }

                        Text(
                            "زمان داده: ${quote.timestamp}",
                            style = MaterialTheme.typography.bodySmall
                        )
                    }

                    state.error?.let {
                        Text(
                            "خطا: $it",
                            color = MaterialTheme.colorScheme.error
                        )
                    }

                    Text(
                        "بروزرسانی خودکار هر ۵ ثانیه",
                        style = MaterialTheme.typography.bodySmall
                    )
                }
            }

            Card(
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(
                        "اطلاعات کندل",
                        style = MaterialTheme.typography.titleLarge
                    )

                    Text("تایم‌فریم: $timeframe")
                    Text("تعداد کندل‌های دریافتی: ${state.candleCount}")

                    state.candle?.let { candle ->
                        HorizontalDivider()

                        PriceRow("Open", formatPrice(symbol, candle.open))
                        PriceRow("High", formatPrice(symbol, candle.high))
                        PriceRow("Low", formatPrice(symbol, candle.low))
                        PriceRow("Close", formatPrice(symbol, candle.close))

                        Text(
                            "زمان کندل: ${candle.time}",
                            style = MaterialTheme.typography.bodySmall
                        )
                    } ?: Text(
                        "اطلاعات کندل هنوز دریافت نشده است."
                    )
                }
            }

            Card(
                modifier = Modifier.fillMaxWidth()
            ) {
                Column(
                    modifier = Modifier.padding(16.dp),
                    verticalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    Text(
                        "AI Signal",
                        style = MaterialTheme.typography.titleLarge
                    )

                    Text(
                        "NO TRADE",
                        style = MaterialTheme.typography.headlineMedium
                    )

                    Text(
                        "این نسخه فقط قیمت زنده و اطلاعات کندل را نمایش می‌دهد. " +
                            "هنوز سیگنال معاملاتی تأییدشده تولید نمی‌کند."
                    )
                }
            }

            Text(
                "مدیریت ریسک: اگر حداقل حجم بروکر از ریسک مجاز بیشتر باشد، " +
                    "معامله باید رد شود و حجم نباید به اجبار افزایش یابد.",
                style = MaterialTheme.typography.bodySmall
            )
        }
    }
}

@Composable
private fun PriceRow(
    title: String,
    value: String
) {
    Row(
        modifier = Modifier.fillMaxWidth(),
        horizontalArrangement = Arrangement.SpaceBetween,
        verticalAlignment = Alignment.CenterVertically
    ) {
        Text(title)
        Text(value)
    }
}

private fun formatPrice(
    symbol: String,
    value: Double
): String {
    val decimals = when (symbol) {
        "XAUUSD" -> 2
        "XAGUSD" -> 3
        else -> 5
    }

    return String.format(
        Locale.US,
        "%.${decimals}f",
        value
    )
}

private fun fetchMarketData(
    symbol: String,
    timeframe: String
): MarketScreenState {

    val tickJson = getJson(
        "$API_BASE/api/v1/market/$symbol/tick"
    )

    val quote = MarketQuote(
        bid = tickJson.getDouble("bid"),
        ask = tickJson.getDouble("ask"),
        mid = tickJson.getDouble("mid"),
        spread = tickJson.getDouble("spread"),
        timestamp = tickJson.optString("timestamp", "نامشخص"),
        source = tickJson.optString("source", "نامشخص"),
        provider = tickJson.optString("provider", "نامشخص"),
        marketState = tickJson.optString("market_state", "نامشخص"),
        stale = tickJson.optBoolean("stale", true),
        quoteAge = tickJson.opt("quote_age_seconds")
            ?.toString() ?: "نامشخص"
    )

    val ohlcJson = getJson(
        "$API_BASE/api/v1/market/$symbol/ohlc" +
            "?interval=$timeframe&limit=100"
    )

    val bars = ohlcJson.optJSONArray("bars")

    var candle: CandleSummary? = null
    var candleCount = 0

    if (bars != null) {
        candleCount = bars.length()

        if (candleCount > 0) {
            val last = bars.getJSONObject(candleCount - 1)

            candle = CandleSummary(
                open = last.getDouble("open"),
                high = last.getDouble("high"),
                low = last.getDouble("low"),
                close = last.getDouble("close"),
                time = last.optString(
                    "time",
                    last.optString("timestamp", "نامشخص")
                )
            )
        }
    }

    return MarketScreenState(
        quote = quote,
        candle = candle,
        candleCount = candleCount,
        loading = false,
        error = null,
        lastUpdate = System.currentTimeMillis().toString()
    )
}

private fun getJson(endpoint: String): JSONObject {
    val connection = URL(endpoint).openConnection()
        as HttpURLConnection

    try {
        connection.requestMethod = "GET"
        connection.connectTimeout = 15000
        connection.readTimeout = 15000
        connection.setRequestProperty(
            "Accept",
            "application/json"
        )

        val responseCode = connection.responseCode

        val stream = if (responseCode in 200..299) {
            connection.inputStream
        } else {
            connection.errorStream
        }

        val response = stream?.bufferedReader()?.use {
            it.readText()
        } ?: throw Exception("پاسخ خالی از سرور")

        if (responseCode !in 200..299) {
            throw Exception(
                "خطای سرور ($responseCode): $response"
            )
        }

        return JSONObject(response)

    } finally {
        connection.disconnect()
    }
}
