"""
Standalone script to review pending alerts and update their status
Run this periodically to check market resolutions and update alert performance
"""
from db import init_db
from post_event_review import review_pending_alerts, display_performance_report, export_performance_data

def main():
    init_db()
    
    print("Reviewing pending alerts...")
    
    # Review and resolve pending alerts
    resolved = review_pending_alerts()
    print(f"Resolved {resolved} alerts")
    
    # Display performance report
    print("\n")
    display_performance_report()
    
    # Export performance data
    export_performance_data("alert_performance.json")
    
    print("\nReview complete!")

if __name__ == "__main__":
    main()
