#!/usr/bin/env python3
"""
NetMapper - IP / domain intelligence lookup tool.
By J4XD (Fearless Hacker)

For educational and authorised use only.
"""

import argparse
import csv
import ipaddress
import json
import os
import socket
import sys
import time

try:
    import requests
except ImportError:  # pragma: no cover
    print("[!] Missing dependency: requests  ->  pip install requests")
    sys.exit(1)

__version__ = "3.0.0"

API_SINGLE = "http://ip-api.com/json/{target}"
API_BATCH = "http://ip-api.com/batch"
BATCH_SIZE = 100  # ip-api batch limit
TIMEOUT = 10

FIELDS = (
    "status,message,query,continent,country,countryCode,regionName,city,"
    "district,zip,lat,lon,timezone,currency,isp,org,as,asname,reverse,"
    "mobile,proxy,hosting"
)

# (label, key) pairs, printed in this order
DISPLAY = [
    ("Target IP", "query"),
    ("Input", "input"),
    ("Reverse DNS", "reverse"),
    ("ISP", "isp"),
    ("Organisation", "org"),
    ("ASN", "as"),
    ("AS Name", "asname"),
    ("Continent", "continent"),
    ("Country", "country"),
    ("Country Code", "countryCode"),
    ("Region", "regionName"),
    ("City", "city"),
    ("District", "district"),
    ("Zip code", "zip"),
    ("Latitude", "lat"),
    ("Longitude", "lon"),
    ("Time zone", "timezone"),
    ("Currency", "currency"),
    ("Mobile network", "mobile"),
    ("Proxy / VPN / Tor", "proxy"),
    ("Hosting / DC", "hosting"),
    ("Google Maps", "maps"),
]


class C:
    """ANSI colours (blanked out with --no-color or when not a TTY)."""
    red = "\033[31m"
    yellow = "\033[93m"
    green = "\033[92m"
    cyan = "\033[96m"
    bold = "\033[1m"
    reset = "\033[0m"

    @classmethod
    def disable(cls):
        for name in ("red", "yellow", "green", "cyan", "bold", "reset"):
            setattr(cls, name, "")


BANNER = r"""
   _  __    __  __  ___
  / |/ /__ / /_/  |/  /__ ____  ___  ___ ____
 /    / -_) __/ /|_/ / _ `/ _ \/ _ \/ -_) __/
/_/|_/\__/\__/_/  /_/\_,_/ .__/ .__/\__/_/
                        /_/  /_/
"""


def banner():
    print(C.red + C.bold + BANNER + C.reset)
    print(C.green + C.bold + f"      <===[[ NetMapper v{__version__} | coded by J4XD ]]===>\n" + C.reset)


def info(msg):
    print(C.cyan + "[*] " + msg + C.reset, file=sys.stderr)


def warn(msg):
    print(C.yellow + "[!] " + msg + C.reset, file=sys.stderr)


def error(msg):
    print(C.red + "[x] " + msg + C.reset, file=sys.stderr)


# --------------------------------------------------------------------------- #
# Target handling
# --------------------------------------------------------------------------- #
def resolve(target):
    """Return a sorted list of unique IPs (IPv4 first) for an IP or hostname."""
    target = target.strip()
    try:
        return [str(ipaddress.ip_address(target))]
    except ValueError:
        pass
    try:
        infos = socket.getaddrinfo(target, None)
    except (socket.gaierror, UnicodeError):
        return []
    ips = {i[4][0].split("%")[0] for i in infos}
    return sorted(ips, key=lambda x: (ipaddress.ip_address(x).version, x))


def is_public(ip):
    obj = ipaddress.ip_address(ip)
    return obj.is_global and not obj.is_multicast


def load_targets(args):
    targets = [t for t in (args.targets or []) if t != "-"]
    if "-" in (args.targets or []):  # read targets from stdin
        targets.extend(l.strip() for l in sys.stdin if l.strip())
    if args.target:
        targets.append(args.target)
    if args.file:
        try:
            with open(args.file, encoding="utf-8") as fh:
                for line in fh:
                    line = line.split("#", 1)[0].strip()
                    if line:
                        targets.append(line)
        except OSError as exc:
            error(f"Cannot read {args.file}: {exc}")
            sys.exit(1)
    # de-duplicate, keep order
    seen, out = set(), []
    for t in targets:
        if t not in seen:
            seen.add(t)
            out.append(t)
    return out


# --------------------------------------------------------------------------- #
# API
# --------------------------------------------------------------------------- #
def _respect_rate_limit(resp):
    """ip-api sends X-Rl (requests left) and X-Ttl (seconds to reset)."""
    try:
        left = int(resp.headers.get("X-Rl", 1))
        ttl = int(resp.headers.get("X-Ttl", 0))
    except ValueError:
        return
    if left <= 0 and ttl > 0:
        warn(f"Rate limit reached, waiting {ttl}s ...")
        time.sleep(ttl + 1)


def query_one(session, ip=""):
    """Look up a single IP. Empty ip = your own public IP."""
    resp = session.get(API_SINGLE.format(target=ip), params={"fields": FIELDS}, timeout=TIMEOUT)
    _respect_rate_limit(resp)
    resp.raise_for_status()
    return resp.json()


def query_batch(session, ips):
    results = []
    for i in range(0, len(ips), BATCH_SIZE):
        chunk = ips[i:i + BATCH_SIZE]
        resp = session.post(API_BATCH, params={"fields": FIELDS}, json=chunk, timeout=TIMEOUT)
        _respect_rate_limit(resp)
        resp.raise_for_status()
        results.extend(resp.json())
    return results


def enrich(rec):
    if rec.get("lat") is not None and rec.get("lon") is not None:
        rec["maps"] = f"https://www.google.com/maps?q={rec['lat']},{rec['lon']}"
    return rec


# --------------------------------------------------------------------------- #
# Output
# --------------------------------------------------------------------------- #
def fmt(value):
    if isinstance(value, bool):
        return (C.red + "YES" + C.reset) if value else "no"
    if value in (None, ""):
        return C.yellow + "N/A" + C.reset
    return str(value)


def print_record(rec):
    sep = C.red + "<" + "-" * 40 + ">" + C.reset
    print(sep)
    for idx, (label, key) in enumerate(DISPLAY):
        if key not in rec:
            continue
        if key == "input" and rec.get("input") == rec.get("query"):
            continue
        tag = (C.green if idx % 2 == 0 else C.cyan) + C.bold + "[$]" + C.reset
        print(f"{tag} {label:<18}: {fmt(rec[key])}")
    print(sep + "\n")


def save(records, path):
    ext = os.path.splitext(path)[1].lower()
    keys = [k for _, k in DISPLAY]
    with open(path, "w", newline="", encoding="utf-8") as fh:
        if ext == ".csv":
            writer = csv.DictWriter(fh, fieldnames=keys, extrasaction="ignore")
            writer.writeheader()
            writer.writerows(records)
        elif ext == ".txt":
            for rec in records:
                for label, key in DISPLAY:
                    if key in rec:
                        fh.write(f"{label:<18}: {rec[key]}\n")
                fh.write("-" * 42 + "\n")
        else:
            json.dump(records if len(records) != 1 else records[0], fh, indent=4)
    print(C.yellow + f"[+] Output saved to {path}" + C.reset, file=sys.stderr)


# --------------------------------------------------------------------------- #
# Main
# --------------------------------------------------------------------------- #
def build_parser():
    p = argparse.ArgumentParser(
        prog="netmapper",
        description="NetMapper - IP / domain geolocation & network intel lookup.",
        epilog="Examples:\n"
               "  python netmapper.py 8.8.8.8\n"
               "  python netmapper.py -v github.com -o result.json\n"
               "  python netmapper.py 1.1.1.1 google.com -o out.csv\n"
               "  python netmapper.py -f targets.txt --json\n"
               "  python netmapper.py --me",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p.add_argument("targets", nargs="*", help="IP addresses or domains ('-' = read from stdin)")
    p.add_argument("-v", "--target", dest="target", help="single target IP or domain (v2 compatible)")
    p.add_argument("-f", "--file", help="file with one target per line (# comments allowed)")
    p.add_argument("-m", "--me", action="store_true", help="look up your own public IP")
    p.add_argument("-a", "--all-ips", action="store_true",
                   help="look up every IP a domain resolves to (default: first only)")
    p.add_argument("-o", "--output", help="save results (.json / .csv / .txt)")
    p.add_argument("-j", "--json", action="store_true", help="print raw JSON to stdout")
    p.add_argument("--no-color", action="store_true", help="disable coloured output")
    p.add_argument("--no-banner", action="store_true", help="hide the banner")
    p.add_argument("--version", action="version", version=f"NetMapper {__version__}")
    return p


def main(argv=None):
    args = build_parser().parse_args(argv)

    if args.no_color or args.json or not sys.stdout.isatty() or os.environ.get("NO_COLOR"):
        C.disable()
    if not (args.no_banner or args.json):
        banner()

    targets = load_targets(args)
    if not targets and not args.me:
        build_parser().print_usage()
        error("No target given. Try: python netmapper.py 8.8.8.8   (or --me)")
        return 1

    # Resolve domains -> IPs, skip private/reserved ranges
    lookups = []  # (input, ip)
    for t in targets:
        ips = resolve(t)
        if not ips:
            error(f"{t}: invalid IP or domain could not be resolved")
            continue
        if len(ips) > 1 and not args.all_ips and not args.json:
            info(f"{t} resolves to {len(ips)} IPs: {', '.join(ips)} (use -a to look up all)")
        for ip in (ips if args.all_ips else ips[:1]):
            if not is_public(ip):
                warn(f"{t} -> {ip} is a private/reserved address, skipping API lookup")
                continue
            lookups.append((t, ip))

    records = []
    try:
        with requests.Session() as session:
            session.headers["User-Agent"] = f"NetMapper/{__version__}"
            if args.me:
                rec = query_one(session)
                rec["input"] = "(your public IP)"
                records.append(rec)
            if len(lookups) == 1:
                rec = query_one(session, lookups[0][1])
                rec["input"] = lookups[0][0]
                records.append(rec)
            elif lookups:
                info(f"Batch lookup of {len(lookups)} IPs ...")
                for (inp, _), rec in zip(lookups, query_batch(session, [ip for _, ip in lookups])):
                    rec["input"] = inp
                    records.append(rec)
    except KeyboardInterrupt:
        error("Terminated by user")
        return 130
    except requests.exceptions.Timeout:
        error("Request timed out. Check your internet connection.")
        return 1
    except requests.exceptions.ConnectionError:
        error("Cannot reach ip-api.com. Check your internet connection.")
        return 1
    except requests.exceptions.RequestException as exc:
        error(f"Network error: {exc}")
        return 1
    except ValueError:
        error("API returned an invalid response.")
        return 1

    good = []
    for rec in records:
        if rec.get("status") != "success":
            error(f"{rec.get('input', rec.get('query'))}: API failed - {rec.get('message', 'unknown error')}")
            continue
        rec.pop("status", None)
        rec.pop("message", None)
        good.append(enrich(rec))

    if args.json:
        print(json.dumps(good if len(good) != 1 else good[0], indent=4))
    else:
        for rec in good:
            print_record(rec)

    if args.output and good:
        try:
            save(good, args.output)
        except OSError as exc:
            error(f"Cannot write {args.output}: {exc}")
            return 1

    return 0 if good else 1


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\n[!] Terminated by user")
        sys.exit(130)
