
package com.tradingai.app

import android.os.Bundle
import androidx.activity.ComponentActivity
import androidx.activity.compose.setContent
import androidx.compose.foundation.Image
import androidx.compose.foundation.layout.*
import androidx.compose.material3.*
import androidx.compose.runtime.*
import androidx.compose.ui.Alignment
import androidx.compose.ui.Modifier
import androidx.compose.ui.res.painterResource
import androidx.compose.ui.unit.dp

class MainActivity : ComponentActivity() {
    override fun onCreate(savedInstanceState: Bundle?) {
        super.onCreate(savedInstanceState)
        setContent {
            TradingDashboard()
        }
    }
}

@Composable
fun TradingDashboard() {
    var symbol by remember { mutableStateOf("XAUUSD") }
    var timeframe by remember { mutableStateOf("M5") }

    MaterialTheme {
        Scaffold { padding ->

            Column(
                modifier = Modifier
                    .padding(padding)
                    .padding(20.dp),
                verticalArrangement = Arrangement.spacedBy(16.dp)
            ) {

                // fxizadi Brand Header
                Row(
                    verticalAlignment = Alignment.CenterVertically,
                    horizontalArrangement = Arrangement.spacedBy(14.dp)
                ) {
                    Image(
                        painter = painterResource(
                            id = R.mipmap.ic_launcher
                        ),
                        contentDescription = "fxizadi logo",
                        modifier = Modifier.size(64.dp)
                    )

                    Column {
                        Text(
                            "fxizadi",
                            style = MaterialTheme.typography.headlineMedium
                        )

                        Text("SMART MARKET ANALYSIS")
                    }
                }

                Row(
                    horizontalArrangement = Arrangement.spacedBy(8.dp)
                ) {
                    listOf("XAUUSD", "EURUSD").forEach {
                        FilterChip(
                            selected = symbol == it,
                            onClick = { symbol = it },
                            label = { Text(it) }
                        )
                    }
                }

                Text(
                    "Selected: $symbol",
                    style = MaterialTheme.typography.titleLarge
                )

                Row(
                    horizontalArrangement = Arrangement.spacedBy(6.dp)
                ) {
                    listOf(
                        "M1", "M5", "M15", "M30",
                        "H1", "H4", "D1"
                    ).forEach {
                        FilterChip(
                            selected = timeframe == it,
                            onClick = { timeframe = it },
                            label = { Text(it) }
                        )
                    }
                }

                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp)) {
                        Text(
                            "Market chart",
                            style = MaterialTheme.typography.titleMedium
                        )
                        Text(
                            "Live feed not connected. No prices or candles are fabricated."
                        )
                    }
                }

                Card(Modifier.fillMaxWidth()) {
                    Column(Modifier.padding(16.dp)) {
                        Text("AI Signal")
                        Text(
                            "NO TRADE",
                            style = MaterialTheme.typography.headlineSmall
                        )
                        Text(
                            "Waiting for a validated market-data feed and tested strategy."
                        )
                    }
                }

                Text(
                    "Risk control: minimum-lot validation required before any trade."
                )
            }
        }
    }
}
