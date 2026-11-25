from technical_analysis.levels import support_resistance,pullback_zone
def test_sr_requires_sufficient_candles(): assert support_resistance([])["status"]=="INSUFFICIENT_DATA"
def test_pullback_requires_data(): assert pullback_zone([])["status"]=="INSUFFICIENT_DATA"
