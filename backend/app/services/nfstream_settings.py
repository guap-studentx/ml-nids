NFSTREAM_OFFLINE_SETTINGS = {
    "decode_tunnels": False,
    "bpf_filter": r"ip and (ip proto \tcp or \udp)",
    "promiscuous_mode": True,
    "snapshot_length": 1536,
    "idle_timeout": 60,
    "active_timeout": 120,
    "accounting_mode": 0,
    "udps": None,
    "n_dissections": 0,
    "statistical_analysis": True,
    "splt_analysis": 0,
    "n_meters": 1,
    "performance_report": 0,
}


NFSTREAM_LIVE_SETTINGS = {
    **NFSTREAM_OFFLINE_SETTINGS,
    "idle_timeout": 30,
    "active_timeout": 30,
}
