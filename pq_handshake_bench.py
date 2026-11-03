#!/usr/bin/env python3
"""Compare classic TLS (X25519) vs hybrid post-quantum TLS (X25519MLKEM768) handshakes to S3."""
import argparse, re, shutil, statistics, subprocess, time

OPENSSL = shutil.which("openssl35") or "openssl"  # OpenSSL >= 3.5 required for ML-KEM
GROUPS = {"classic (X25519)": "X25519", "hybrid PQ (X25519MLKEM768)": "X25519MLKEM768"}


def handshake(host, group):
    cmd = [OPENSSL, "s_client", "-connect", f"{host}:443", "-servername", host,
           "-groups", group, "-tls1_3"]
    t0 = time.perf_counter()
    try:
        r = subprocess.run(cmd, input=b"", capture_output=True, timeout=15)
    except subprocess.TimeoutExpired:
        return None, None
    ms = (time.perf_counter() - t0) * 1000
    txt = (r.stdout + r.stderr).decode(errors="ignore")
    m = re.search(r"(?:Negotiated TLS1\.3 group|Server Temp Key):\s*([^\s,]+)", txt)
    return (ms, m.group(1) if m else None) if r.returncode == 0 else (None, None)


def pctl(v, p):
    s = sorted(v)
    return s[min(len(s) - 1, round(p / 100 * (len(s) - 1)))]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--region", default="eu-west-3")
    ap.add_argument("--host")
    ap.add_argument("--runs", type=int, default=30)
    a = ap.parse_args()
    host = a.host or f"s3.{a.region}.amazonaws.com"
    print(subprocess.run([OPENSSL, "version"], capture_output=True, text=True).stdout.strip())
    print(f"Endpoint: {host} | {a.runs} handshakes per mode\n")
    res = []
    for label, g in GROUPS.items():
        handshake(host, g)  # warm-up
        times, neg = [], set()
        for _ in range(a.runs):
            ms, n = handshake(host, g)
            if ms is not None:
                times.append(ms)
                neg.add(n)
        res.append(times)
        if not times:
            print(f"{label:30s} FAILED (group not supported, or blocked on the network?)")
            continue
        print(f"{label:30s} median {statistics.median(times):7.1f} ms | p95 {pctl(times, 95):7.1f} ms"
              f" | min {min(times):7.1f} | max {max(times):7.1f}")
        print(f"{'':30s} negotiated group: {', '.join(map(str, neg))}")
    if all(res):
        print(f"\nMedian PQ-TLS overhead: {statistics.median(res[1]) - statistics.median(res[0]):+.1f} ms")
    print("(duration includes openssl process startup: only the gap between modes matters)")


if __name__ == "__main__":
    main()
