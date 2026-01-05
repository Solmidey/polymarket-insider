"""
Wallet Graph Analysis - Detect shared funding sources and wallet relationships
"""
from collections import defaultdict
from db import cur, conn

def init_wallet_graph_tables():
    """Initialize tables for wallet graph analysis"""
    cur.execute("""
        CREATE TABLE IF NOT EXISTS wallet_funding (
            wallet TEXT,
            funding_source TEXT,
            amount REAL,
            timestamp INTEGER,
            PRIMARY KEY (wallet, funding_source)
        )
    """)
    
    cur.execute("""
        CREATE TABLE IF NOT EXISTS wallet_clusters (
            cluster_id TEXT PRIMARY KEY,
            wallets TEXT,
            shared_sources INTEGER,
            first_detected INTEGER
        )
    """)
    
    conn.commit()

def add_funding_source(wallet, funding_source, amount=0, timestamp=0):
    """Record a funding source for a wallet"""
    cur.execute("""
        INSERT OR REPLACE INTO wallet_funding 
        (wallet, funding_source, amount, timestamp)
        VALUES (?, ?, ?, ?)
    """, (wallet, funding_source, amount, timestamp))
    conn.commit()

def get_wallet_funding_sources(wallet):
    """Get all funding sources for a wallet"""
    cur.execute("""
        SELECT funding_source, amount, timestamp
        FROM wallet_funding
        WHERE wallet = ?
    """, (wallet,))
    return cur.fetchall()

def find_shared_funding_clusters(min_shared=2):
    """
    Find wallets that share funding sources (potential coordinated group)
    
    Args:
        min_shared: Minimum number of shared funding sources to form a cluster
    
    Returns:
        List of clusters, each containing wallet addresses
    """
    # Get all wallet-funding relationships
    cur.execute("""
        SELECT wallet, funding_source
        FROM wallet_funding
    """)
    all_funding = cur.fetchall()
    
    # Build reverse index: funding_source -> [wallets]
    source_to_wallets = defaultdict(set)
    for wallet, source in all_funding:
        source_to_wallets[source].add(wallet)
    
    # Find wallets that share funding sources
    wallet_connections = defaultdict(set)
    for source, wallets in source_to_wallets.items():
        if len(wallets) >= 2:  # At least 2 wallets share this source
            wallet_list = list(wallets)
            for i, wallet1 in enumerate(wallet_list):
                for wallet2 in wallet_list[i+1:]:
                    wallet_connections[wallet1].add(wallet2)
                    wallet_connections[wallet2].add(wallet1)
    
    # Find clusters using simple connected components
    visited = set()
    clusters = []
    
    def dfs(wallet, cluster):
        if wallet in visited:
            return
        visited.add(wallet)
        cluster.add(wallet)
        for connected_wallet in wallet_connections[wallet]:
            dfs(connected_wallet, cluster)
    
    for wallet in wallet_connections:
        if wallet not in visited:
            cluster = set()
            dfs(wallet, cluster)
            if len(cluster) >= 2:  # At least 2 wallets in cluster
                clusters.append(cluster)
    
    return clusters

def are_wallets_related(wallet1, wallet2):
    """Check if two wallets share funding sources"""
    cur.execute("""
        SELECT COUNT(DISTINCT wf1.funding_source)
        FROM wallet_funding wf1
        JOIN wallet_funding wf2 ON wf1.funding_source = wf2.funding_source
        WHERE wf1.wallet = ? AND wf2.wallet = ?
    """, (wallet1, wallet2))
    result = cur.fetchone()
    shared_count = result[0] if result else 0
    return shared_count >= 1

def get_wallet_cluster(wallet):
    """Get the cluster ID that a wallet belongs to"""
    clusters = find_shared_funding_clusters()
    for i, cluster in enumerate(clusters):
        if wallet in cluster:
            return f"cluster_{i}", cluster
    return None, set()

def detect_coordinated_group(wallets):
    """
    Detect if a group of wallets are coordinated (share funding sources)
    
    Args:
        wallets: List of wallet addresses
    
    Returns:
        Tuple of (is_coordinated, shared_sources_count, cluster_info)
    """
    if len(wallets) < 2:
        return False, 0, {}
    
    # Count shared funding sources
    shared_sources = None
    for wallet in wallets:
        sources = set(s[0] for s in get_wallet_funding_sources(wallet))
        if shared_sources is None:
            shared_sources = sources
        else:
            shared_sources = shared_sources.intersection(sources)
    
    shared_count = len(shared_sources) if shared_sources else 0
    is_coordinated = shared_count >= 1
    
    return is_coordinated, shared_count, {
        "shared_sources": list(shared_sources) if shared_sources else [],
        "wallet_count": len(wallets)
    }

def get_recent_wallets_for_analysis(all_trades, current_trade, window_minutes=120):
    """Get list of recent wallet addresses for wallet graph analysis"""
    cutoff = current_trade["timestamp"] - (window_minutes * 60)
    recent_wallets = []
    for t in all_trades:
        if t.get("timestamp", 0) >= cutoff:
            wallet = t.get("wallet") or t.get("trader")
            if wallet:
                recent_wallets.append(wallet)
    return recent_wallets
