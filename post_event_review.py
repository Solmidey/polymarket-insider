"""
Post-Event Review - Verify if alerts actually predict outcomes
"""
import time
from datetime import datetime, timedelta
from db import cur, conn

def record_alert(market, wallet, fired_timestamp, fired_price, signals):
    """Record an alert when it fires"""
    signals_str = "|".join(signals)
    
    cur.execute("""
        INSERT INTO alerts 
        (market, wallet, fired_timestamp, fired_price, signals, status)
        VALUES (?, ?, ?, ?, ?, 'pending')
    """, (market, wallet, fired_timestamp, fired_price, signals_str))
    
    conn.commit()
    return cur.lastrowid

def update_peak_price(alert_id, peak_price, peak_timestamp):
    """Update the peak price reached before resolution"""
    cur.execute("""
        UPDATE alerts
        SET peak_price = ?, peak_timestamp = ?
        WHERE alert_id = ?
    """, (peak_price, peak_timestamp, alert_id))
    conn.commit()

def resolve_alert(alert_id, outcome, outcome_timestamp, resolution_price):
    """
    Resolve an alert when market closes
    
    Args:
        alert_id: Alert ID
        outcome: "YES" or "NO"
        outcome_timestamp: When market resolved
        resolution_price: Final price (1.0 for YES, 0.0 for NO)
    """
    # Get alert details
    cur.execute("""
        SELECT fired_timestamp, fired_price, peak_price
        FROM alerts
        WHERE alert_id = ?
    """, (alert_id,))
    
    result = cur.fetchone()
    if not result:
        return None
    
    fired_timestamp, fired_price, peak_price = result
    
    # Calculate metrics
    hours_to_outcome = (outcome_timestamp - fired_timestamp) / 3600
    
    # Price changes
    price_change = resolution_price - fired_price  # Final change
    peak_price_change = (peak_price - fired_price) if peak_price else 0  # Peak change
    
    # Calculate profit/loss (assuming $100 bet)
    # If betting YES at fired_price, profit = (resolution_price - fired_price) * 100
    # If betting NO at fired_price, profit = ((1 - resolution_price) - (1 - fired_price)) * 100
    # Simplified: profit = (resolution_price - fired_price) * 100 for YES bets
    # For this analysis, we'll assume YES bets (most common for insider trading)
    profit_loss = (resolution_price - fired_price) * 100
    
    # Determine if alert was correct
    # Alert is "correct" if price moved significantly in profitable direction
    is_correct = profit_loss > 0 or abs(peak_price_change) > 0.15
    
    # Update alert
    cur.execute("""
        UPDATE alerts
        SET outcome = ?,
            outcome_timestamp = ?,
            hours_to_outcome = ?,
            price_change = ?,
            peak_price_change = ?,
            profit_loss = ?,
            is_correct = ?,
            status = 'resolved'
        WHERE alert_id = ?
    """, (outcome, outcome_timestamp, hours_to_outcome, price_change, peak_price_change, profit_loss, is_correct, alert_id))
    
    conn.commit()
    
    return {
        "alert_id": alert_id,
        "hours_to_outcome": hours_to_outcome,
        "price_change": price_change,
        "peak_price_change": peak_price_change,
        "profit_loss": profit_loss,
        "is_correct": is_correct
    }

def get_alert_performance_stats():
    """Get performance statistics for all resolved alerts"""
    cur.execute("""
        SELECT 
            COUNT(*) as total_alerts,
            SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct_alerts,
            AVG(hours_to_outcome) as avg_hours_to_outcome,
            AVG(price_change) as avg_price_change,
            AVG(CASE WHEN peak_price IS NOT NULL THEN peak_price - fired_price ELSE 0 END) as avg_peak_gain
        FROM alerts
        WHERE status = 'resolved'
    """)
    
    result = cur.fetchone()
    if not result or not result[0]:
        return None
    
    total, correct, avg_hours, avg_change, avg_peak = result
    
    accuracy = (correct / total * 100) if total > 0 else 0
    
    return {
        "total_alerts": total,
        "correct_alerts": correct,
        "accuracy_percent": round(accuracy, 2),
        "avg_hours_to_outcome": round(avg_hours or 0, 2),
        "avg_price_change": round(avg_change or 0, 4),
        "avg_peak_gain": round(avg_peak or 0, 4)
    }

def get_signal_performance():
    """Analyze which signals actually predict outcomes - DETAILED SCORING"""
    cur.execute("""
        SELECT signals, 
               COUNT(*) as count,
               SUM(CASE WHEN is_correct = 1 THEN 1 ELSE 0 END) as correct,
               AVG(price_change) as avg_price_change,
               AVG(peak_price_change) as avg_peak_change,
               SUM(profit_loss) as total_profit_loss,
               AVG(profit_loss) as avg_profit_loss,
               AVG(hours_to_outcome) as avg_hours,
               MIN(profit_loss) as worst_loss,
               MAX(profit_loss) as best_gain
        FROM alerts
        WHERE status = 'resolved'
        GROUP BY signals
    """)
    
    results = cur.fetchall()
    
    signal_stats = []
    for row in results:
        signals_str, count, correct, avg_change, avg_peak, total_pl, avg_pl, avg_hours, worst, best = row
        
        accuracy = (correct / count * 100) if count > 0 else 0
        signal_list = signals_str.split("|")
        
        # Win rate is the same as accuracy (correct predictions)
        win_rate = accuracy
        
        # Content value score (based on peak movement - good for content even if loses)
        content_score = abs(avg_peak or 0) * 100  # How dramatic the move was
        
        # Trading value score (actual profit/loss)
        trading_score = avg_pl or 0
        
        signal_stats.append({
            "signals": signal_list,
            "signal_combo": " + ".join(signal_list),
            "count": count,
            "wins": correct,
            "losses": count - correct,
            "win_rate": round(win_rate, 2),
            "accuracy_percent": round(accuracy, 2),
            "avg_price_change": round(avg_change or 0, 4),
            "avg_peak_change": round(avg_peak or 0, 4),
            "total_profit_loss": round(total_pl or 0, 2),
            "avg_profit_loss": round(avg_pl or 0, 2),
            "avg_hours_to_outcome": round(avg_hours or 0, 2),
            "worst_loss": round(worst or 0, 2),
            "best_gain": round(best or 0, 2),
            "content_score": round(content_score, 2),
            "trading_score": round(trading_score, 2),
            "roi_percent": round((avg_pl / 100 * 100) if avg_pl else 0, 2)  # Assuming $100 bets
        })
    
    return signal_stats

def score_signals_detailed():
    """
    Comprehensive signal scoring - answers the key questions:
    1. Which signal combo wins most?
    2. Which loses money?
    3. Which creates great content but bad trades?
    """
    stats = get_signal_performance()
    
    if not stats:
        return None
    
    # Sort by different metrics
    by_win_rate = sorted(stats, key=lambda x: x["win_rate"], reverse=True)
    by_profit = sorted(stats, key=lambda x: x["avg_profit_loss"], reverse=True)
    by_content = sorted(stats, key=lambda x: x["content_score"], reverse=True)
    by_roi = sorted(stats, key=lambda x: x["roi_percent"], reverse=True)
    
    # Find winners and losers
    winners = [s for s in stats if s["avg_profit_loss"] > 0]
    losers = [s for s in stats if s["avg_profit_loss"] < 0]
    
    # Find content creators (high content score, low trading score)
    content_creators = [
        s for s in stats 
        if s["content_score"] > 10 and s["trading_score"] < 0
    ]
    
    return {
        "by_win_rate": by_win_rate[:10],
        "by_profit": by_profit[:10],
        "by_content": by_content[:10],
        "by_roi": by_roi[:10],
        "winners": winners,
        "losers": losers,
        "content_creators": content_creators,
        "all_stats": stats
    }

def get_pending_alerts():
    """Get all pending alerts that need resolution"""
    cur.execute("""
        SELECT alert_id, market, fired_timestamp, fired_price, signals
        FROM alerts
        WHERE status = 'pending'
        ORDER BY fired_timestamp
    """)
    
    return cur.fetchall()

def check_market_resolution(market_id):
    """
    Check if a market has been resolved
    """
    from market_resolution import check_market_resolution as check_resolution
    return check_resolution(market_id)

def update_peak_prices():
    """Update peak prices for all pending alerts"""
    from market_resolution import get_market_prices
    
    pending = get_pending_alerts()
    
    updated = 0
    for alert_id, market, fired_timestamp, fired_price, signals_str in pending:
        prices = get_market_prices(market)
        if prices:
            # Use the higher of YES or NO price as peak
            peak_price = max(prices.get("yes_price", 0), prices.get("no_price", 0))
            peak_timestamp = prices.get("timestamp") or int(time.time())
            
            # Check if this is a new peak
            cur.execute("SELECT peak_price FROM alerts WHERE alert_id = ?", (alert_id,))
            result = cur.fetchone()
            current_peak = result[0] if result else None
            
            if not current_peak or peak_price > current_peak:
                update_peak_price(alert_id, peak_price, peak_timestamp)
                updated += 1
    
    return updated

def review_pending_alerts():
    """
    Review all pending alerts and check if markets have resolved
    This should be run periodically to update alert statuses
    """
    # First update peak prices
    update_peak_prices()
    
    # Then check for resolutions
    pending = get_pending_alerts()
    
    resolved_count = 0
    for alert_id, market, fired_timestamp, fired_price, signals_str in pending:
        # Check if market is resolved
        resolution = check_market_resolution(market)
        
        if resolution:
            outcome = resolution.get("outcome")
            outcome_timestamp = resolution.get("timestamp") or int(time.time())
            resolution_price = resolution.get("resolution_price", 0.5)
            
            resolve_alert(alert_id, outcome, outcome_timestamp, resolution_price)
            resolved_count += 1
    
    return resolved_count

def display_performance_report():
    """Display a comprehensive performance report with signal scoring"""
    stats = get_alert_performance_stats()
    
    if not stats:
        print("No resolved alerts yet. Need more data.")
        print("Need at least 30-50 resolved alerts for meaningful analysis.")
        return
    
    print("=" * 100)
    print("ALERT PERFORMANCE REPORT - REALITY CHECK")
    print("=" * 100)
    print(f"\nTotal Alerts Resolved: {stats['total_alerts']}")
    print(f"Correct Predictions: {stats['correct_alerts']}")
    print(f"Accuracy: {stats['accuracy_percent']}%")
    print(f"Average Time to Outcome: {stats['avg_hours_to_outcome']:.1f} hours")
    print(f"Average Price Change: {stats['avg_price_change']*100:.2f}%")
    print(f"Average Peak Gain: {stats['avg_peak_gain']*100:.2f}%")
    
    # Detailed signal scoring
    signal_scores = score_signals_detailed()
    
    if not signal_scores:
        print("\nNot enough data for signal scoring yet.")
        return stats
    
    print("\n" + "=" * 100)
    print("🔥 TOP SIGNAL COMBOS BY WIN RATE")
    print("=" * 100)
    for i, stat in enumerate(signal_scores["by_win_rate"][:5], 1):
        print(f"\n{i}. {stat['signal_combo']}")
        print(f"   Win Rate: {stat['win_rate']}% ({stat['wins']}W-{stat['losses']}L)")
        print(f"   Avg Profit/Loss: ${stat['avg_profit_loss']:.2f} per $100 bet")
        print(f"   Total P/L: ${stat['total_profit_loss']:.2f}")
        print(f"   Count: {stat['count']} alerts")
    
    print("\n" + "=" * 100)
    print("💰 TOP SIGNAL COMBOS BY PROFIT")
    print("=" * 100)
    for i, stat in enumerate(signal_scores["by_profit"][:5], 1):
        print(f"\n{i}. {stat['signal_combo']}")
        print(f"   Avg Profit: ${stat['avg_profit_loss']:.2f} per $100 bet")
        print(f"   ROI: {stat['roi_percent']:.2f}%")
        print(f"   Win Rate: {stat['win_rate']}%")
        print(f"   Best Gain: ${stat['best_gain']:.2f} | Worst Loss: ${stat['worst_loss']:.2f}")
    
    print("\n" + "=" * 100)
    print("❌ LOSING SIGNAL COMBOS (CUT THESE)")
    print("=" * 100)
    losers = sorted(signal_scores["losers"], key=lambda x: x["avg_profit_loss"])[:5]
    for i, stat in enumerate(losers, 1):
        print(f"\n{i}. {stat['signal_combo']}")
        print(f"   Avg Loss: ${stat['avg_profit_loss']:.2f} per $100 bet")
        print(f"   Total Loss: ${stat['total_profit_loss']:.2f}")
        print(f"   Win Rate: {stat['win_rate']}% ({stat['wins']}W-{stat['losses']}L)")
        print(f"   ⚠️  This combo loses money - consider removing")
    
    print("\n" + "=" * 100)
    print("📹 CONTENT CREATORS (Great Content, Bad Trades)")
    print("=" * 100)
    if signal_scores["content_creators"]:
        for i, stat in enumerate(signal_scores["content_creators"][:5], 1):
            print(f"\n{i}. {stat['signal_combo']}")
            print(f"   Content Score: {stat['content_score']:.2f} (high drama)")
            print(f"   Trading Score: ${stat['trading_score']:.2f} (loses money)")
            print(f"   Avg Peak Move: {stat['avg_peak_change']*100:.2f}%")
            print(f"   ⚠️  Good for content but bad for trading")
    else:
        print("No signal combos found that are good for content but bad for trading.")
    
    print("\n" + "=" * 100)
    print("📊 ALL SIGNAL COMBOS (Full Breakdown)")
    print("=" * 100)
    for stat in signal_scores["all_stats"]:
        print(f"\n{stat['signal_combo']}")
        print(f"  Count: {stat['count']} | Win Rate: {stat['win_rate']}% | "
              f"Avg P/L: ${stat['avg_profit_loss']:.2f} | ROI: {stat['roi_percent']:.2f}%")
        print(f"  Content Score: {stat['content_score']:.2f} | "
              f"Peak Move: {stat['avg_peak_change']*100:.2f}%")
    
    print("\n" + "=" * 100)
    print("💡 KEY INSIGHTS")
    print("=" * 100)
    
    # Find the best combo
    best_combo = signal_scores["by_profit"][0] if signal_scores["by_profit"] else None
    if best_combo:
        print(f"\n🏆 BEST COMBO: {best_combo['signal_combo']}")
        print(f"   This is your real edge - focus on this!")
    
    # Find the worst combo
    worst_combo = signal_scores["losers"][0] if signal_scores["losers"] else None
    if worst_combo:
        print(f"\n⚠️  WORST COMBO: {worst_combo['signal_combo']}")
        print(f"   Cut this ruthlessly - it's noise, not signal")
    
    print("\n" + "=" * 100)
    
    return stats

def export_performance_data(filename="alert_performance.json"):
    """Export performance data to JSON with detailed signal scoring"""
    import json
    
    stats = get_alert_performance_stats()
    signal_scores = score_signals_detailed()
    
    data = {
        "timestamp": int(time.time()),
        "overall_stats": stats,
        "signal_scoring": signal_scores
    }
    
    with open(filename, 'w') as f:
        json.dump(data, f, indent=2)
    
    print(f"Performance data exported to {filename}")
    return filename
