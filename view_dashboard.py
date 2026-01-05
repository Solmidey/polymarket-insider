"""
Standalone script to view risk scoring dashboard
"""
from db import init_db
from risk_dashboard import display_dashboard, export_dashboard_json

def main():
    init_db()
    
    # Display dashboard
    data = display_dashboard(hours_window=24)
    
    # Export to JSON
    export_dashboard_json("risk_dashboard.json", hours_window=24)
    
    print("\nDashboard data exported to risk_dashboard.json")

if __name__ == "__main__":
    main()
