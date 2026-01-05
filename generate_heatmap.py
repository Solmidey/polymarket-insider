"""
Standalone script to generate cluster heatmap
"""
from db import init_db
from heatmap import generate_cluster_heatmap_data, export_heatmap_json, get_top_clustered_markets

def main():
    init_db()
    
    print("Generating cluster heatmap...")
    
    # Generate heatmap data
    heatmap_data = generate_cluster_heatmap_data(hours_window=24)
    
    print(f"\nFound {heatmap_data['total_markets']} active markets")
    print("\nTop 10 Most Clustered Markets:")
    print("-" * 80)
    
    top_markets = get_top_clustered_markets(limit=10)
    for i, market in enumerate(top_markets, 1):
        print(f"{i}. Market: {market['market'][:20]}...")
        print(f"   Cluster Score: {market['cluster_score']}")
        print(f"   Wallets: {market['wallet_count']} | Trades: {market['trade_count']}")
        print(f"   Volume: ${market['total_volume']:,.2f}")
        print()
    
    # Export to JSON
    export_heatmap_json("heatmap_data.json", hours_window=24)
    print("\nHeatmap data exported to heatmap_data.json")

if __name__ == "__main__":
    main()
