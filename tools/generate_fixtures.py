import sys
from pathlib import Path
from typing import Any

# Ensure workspace root is in sys.path
root_dir = Path(__file__).resolve().parent.parent
if str(root_dir) not in sys.path:
    sys.path.insert(0, str(root_dir))

import numpy as np  # noqa: E402
import polars as pl  # noqa: E402

from packages.contracts.feature_spec import get_research_feature_spec  # noqa: E402


def generate_synthetic_fixtures(output_dir: Path | str = "data/synthetic-fixtures") -> None:
    """Generate reproducible test fixtures for unit, integration, and security testing."""
    out = Path(output_dir)
    out.mkdir(parents=True, exist_ok=True)
    rng = np.random.default_rng(42)

    research_spec = get_research_feature_spec()
    all_feature_names = research_spec.feature_names()

    # Define attack classes and distributions
    classes = [
        "Benign",
        "DDoS",
        "DoS",
        "Reconnaissance",
        "Scanning",
        "Botnet",
        "Brute Force",
        "Injection",
        "Exploits",
    ]
    parent_sources = [
        "NF-UNSW-NB15-v2",
        "NF-CSE-CIC-IDS2018-v2",
        "NF-BoT-IoT-v2",
        "NF-ToN-IoT-v2",
    ]

    n_samples = 1400

    # 1. Base clean dataset
    records: dict[str, list[Any]] = {name: [] for name in all_feature_names}
    records["Attack"] = []
    records["Label"] = []
    records["dataset_source"] = []

    source_subnets = {
        "NF-UNSW-NB15-v2": [f"10.101.{i}.{j}" for i in range(1, 8) for j in range(1, 15)],
        "NF-CSE-CIC-IDS2018-v2": [f"10.102.{i}.{j}" for i in range(1, 8) for j in range(1, 15)],
        "NF-BoT-IoT-v2": [f"10.103.{i}.{j}" for i in range(1, 8) for j in range(1, 15)],
        "NF-ToN-IoT-v2": [f"10.104.{i}.{j}" for i in range(1, 8) for j in range(1, 15)],
    }

    for i in range(n_samples):
        # Class selection
        c = classes[i % len(classes)]
        src = parent_sources[i % len(parent_sources)]
        is_attack = 0 if c == "Benign" else 1

        records["Attack"].append(c)
        records["Label"].append(is_attack)
        records["dataset_source"].append(src)

        # 43 Features
        records["IPV4_SRC_ADDR"].append(rng.choice(source_subnets[src]))
        records["IPV4_DST_ADDR"].append(f"192.168.1.{rng.integers(1, 50)}")
        records["L4_SRC_PORT"].append(int(rng.integers(1024, 65535)))
        # Realistic destination ports based on attack
        if c == "DDoS":
            dst_port = int(rng.choice([80, 443, 53, 8080]))
            in_bytes = int(rng.integers(50000, 500000))
            in_pkts = int(rng.integers(500, 5000))
            flow_dur = int(rng.integers(100, 2000))
            tcp_flags = 2  # SYN
        elif c == "Scanning":
            dst_port = int(rng.integers(1, 1024))
            in_bytes = int(rng.integers(40, 200))
            in_pkts = int(rng.integers(1, 5))
            flow_dur = int(rng.integers(10, 500))
            tcp_flags = 2  # SYN scan
        elif c == "Brute Force":
            dst_port = int(rng.choice([22, 21, 3389]))
            in_bytes = int(rng.integers(1000, 10000))
            in_pkts = int(rng.integers(20, 100))
            flow_dur = int(rng.integers(500, 10000))
            tcp_flags = 24  # PSH-ACK
        else:
            dst_port = int(rng.choice([80, 443, 53, 22, 8080]))
            in_bytes = int(rng.integers(100, 50000))
            in_pkts = int(rng.integers(2, 500))
            flow_dur = int(rng.integers(50, 5000))
            tcp_flags = int(rng.choice([2, 16, 18, 24]))

        records["L4_DST_PORT"].append(int(dst_port))
        records["PROTOCOL"].append(6 if tcp_flags != 0 else 17)
        records["L7_PROTO"].append(float(rng.integers(0, 150)))
        records["IN_BYTES"].append(in_bytes)
        records["OUT_BYTES"].append(int(in_bytes * rng.uniform(0.1, 2.0)))
        records["IN_PKTS"].append(in_pkts)
        records["OUT_PKTS"].append(int(in_pkts * rng.uniform(0.1, 2.0)))
        records["FLOW_DURATION_MILLISECONDS"].append(flow_dur)
        records["TCP_FLAGS"].append(int(tcp_flags))
        records["CLIENT_TCP_FLAGS"].append(int(tcp_flags))
        records["SERVER_TCP_FLAGS"].append(int(tcp_flags))
        records["DURATION_IN"].append(int(flow_dur * 0.6))
        records["DURATION_OUT"].append(int(flow_dur * 0.4))
        records["MIN_TTL"].append(int(rng.integers(30, 64)))
        records["MAX_TTL"].append(int(rng.integers(64, 128)))
        records["LONGEST_FLOW_PKT"].append(int(rng.integers(64, 1500)))
        records["SHORTEST_FLOW_PKT"].append(int(rng.integers(40, 64)))
        records["MIN_IP_PKT_LEN"].append(40)
        records["MAX_IP_PKT_LEN"].append(1500)

        dur_sec = max(0.001, flow_dur / 1000.0)
        records["SRC_TO_DST_SECOND_BYTES"].append(float(in_bytes / dur_sec))
        records["DST_TO_SRC_SECOND_BYTES"].append(float((in_bytes * 0.5) / dur_sec))
        records["RETRANSMITTED_IN_BYTES"].append(int(rng.integers(0, 200)))
        records["RETRANSMITTED_IN_PKTS"].append(int(rng.integers(0, 5)))
        records["RETRANSMITTED_OUT_BYTES"].append(int(rng.integers(0, 200)))
        records["RETRANSMITTED_OUT_PKTS"].append(int(rng.integers(0, 5)))
        records["SRC_TO_DST_AVG_THROUGHPUT"].append(float((in_bytes * 8) / dur_sec))
        records["DST_TO_SRC_AVG_THROUGHPUT"].append(float((in_bytes * 4) / dur_sec))
        records["NUM_PKTS_UP_TO_128_BYTES"].append(int(in_pkts * 0.7))
        records["NUM_PKTS_128_TO_256_BYTES"].append(int(in_pkts * 0.1))
        records["NUM_PKTS_256_TO_512_BYTES"].append(int(in_pkts * 0.1))
        records["NUM_PKTS_512_TO_1024_BYTES"].append(int(in_pkts * 0.05))
        records["NUM_PKTS_1024_TO_1514_BYTES"].append(int(in_pkts * 0.05))
        records["TCP_WIN_MAX_IN"].append(int(rng.integers(1024, 65535)))
        records["TCP_WIN_MAX_OUT"].append(int(rng.integers(1024, 65535)))
        records["ICMP_TYPE"].append(0)
        records["ICMP_IPV4_TYPE"].append(0)
        records["DNS_QUERY_ID"].append(int(rng.integers(0, 65535)))
        records["DNS_QUERY_TYPE"].append(1)
        records["DNS_TTL_ANSWER"].append(int(rng.integers(60, 3600)))
        records["FTP_COMMAND_RET_CODE"].append(0.0)

    clean_df = pl.DataFrame(records)
    clean_parquet_path = out / "sample_netflow_v2.parquet"
    clean_df.write_parquet(clean_parquet_path)
    clean_df.write_csv(out / "sample_netflow_v2.csv")

    # 2. Corrupt dataset for quality tests
    corrupt_records = records.copy()
    # Inject faults into first 20 records
    for i in range(20):
        corrupt_records["IN_BYTES"][i] = -500  # Negative byte count
        corrupt_records["L4_SRC_PORT"][i] = 75000  # Port > 65535
        corrupt_records["PROTOCOL"][i] = 300  # Protocol > 255
    corrupt_df = pl.DataFrame(corrupt_records)
    corrupt_df.write_parquet(out / "corrupt_quality_test.parquet")

    # 3. Duplicate dataset
    dup_df = pl.concat([clean_df[:100], clean_df[:100], clean_df], how="vertical_relaxed")
    dup_df.write_parquet(out / "duplicate_test.parquet")

    # 4. NetFlow v3 dataset (53 features)
    v3_df = clean_df.with_columns(
        pl.lit(0).alias("SRC_FRAGMENTS"),
        pl.lit(0).alias("DST_FRAGMENTS"),
        pl.lit(10.5).alias("SRC_TO_DST_IAT_MIN"),
        pl.lit(12.3).alias("DST_TO_SRC_IAT_MIN"),
        pl.lit(100.0).alias("SRC_TO_DST_IAT_MAX"),
        pl.lit(150.0).alias("DST_TO_SRC_IAT_MAX"),
        pl.lit(45.0).alias("SRC_TO_DST_IAT_AVG"),
        pl.lit(55.0).alias("DST_TO_SRC_IAT_AVG"),
        pl.lit(15.0).alias("SRC_TO_DST_IAT_STDDEV"),
        pl.lit(18.0).alias("DST_TO_SRC_IAT_STDDEV"),
    )
    v3_df.write_parquet(out / "netflow_v3_test.parquet")

    print(f"Generated synthetic fixtures in {out}:")
    print(f"  • sample_netflow_v2.parquet ({len(clean_df):,} rows)")
    print(f"  • sample_netflow_v2.csv ({len(clean_df):,} rows)")
    print(f"  • corrupt_quality_test.parquet ({len(corrupt_df):,} rows)")
    print(f"  • duplicate_test.parquet ({len(dup_df):,} rows)")
    print(f"  • netflow_v3_test.parquet ({len(v3_df):,} rows, {len(v3_df.columns)} columns)")


if __name__ == "__main__":
    generate_synthetic_fixtures()
