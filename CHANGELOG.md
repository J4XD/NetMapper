# Changelog

## v3.0.0

### Fixed
- The banner used `\` escapes in a normal string, which raised `SyntaxWarning`s on Python 3.12+. It is now a raw string.
- Requests had no timeout, so the tool could hang forever on a bad connection. They now time out after 10s.
- The tool crashed with a `KeyError` when the API left out a field, and with a traceback on an invalid JSON response.
- Terminal colours were never reset after output.
- Domains were only resolved to IPv4. IPv6 targets are now supported.
- `Ctrl+C` outside the request printed a Python traceback.

### Added
- Multiple targets: `python netmapper.py 8.8.8.8 github.com ...`
- Target lists from a file (`-f targets.txt`, `#` comments allowed) or from stdin (`-`).
- Batch lookups of up to 100 IPs per request, with automatic rate-limit handling.
- `--me` looks up your own public IP.
- `-a` / `--all-ips` looks up every IP a domain resolves to.
- More fields: continent, country code, district, currency, ASN / AS name and reverse DNS.
- **Proxy/VPN/Tor**, **Hosting/Datacenter** and **Mobile network** detection.
- A Google Maps link for the coordinates.
- Export to **JSON, CSV or TXT**, chosen by the `-o` file extension.
- `--json` prints raw JSON, which can be piped into `jq`.
- `--no-color`, `--no-banner` and `--version` options.
- `requirements.txt`.

### Changed
- `-v` still works as before, but the target can now also be given directly.
