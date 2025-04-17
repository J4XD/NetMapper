# IP Info Tracker - Pro Version by Fearless Hacker & J4XD

import argparse
import requests
import socket
import sys
import json
import ipaddress  # <--- for private/reserved IP detection

# Colors
red = '\033[31m'
yellow = '\033[93m'
lgreen = '\033[92m'
clear = '\033[0m'
bold = '\033[01m'
cyan = '\033[96m'

# Banner
print (red+"""   _            _                      
  / |/ / / /_  /  |/  / __  _  _ __
 /    / -_) / / /|_/ / _ `/ _ \/ _ \/ -_) /
/_/|_/\/\/ /_/  /_/\_,_/ ./ ./\__/_/   
                          /_/  /_/             ╝
                               v 2.0 | By J4XD
"""+clear)
print (lgreen+bold+"         <===[[ coded by J4XD ]]===> \n"+clear)

# Parse Arguments
parser = argparse.ArgumentParser()
parser.add_argument("-v", help="Target IP or domain", type=str, dest='target', required=True)
parser.add_argument("-o", help="Save output to file", type=str, dest='output', required=False)
args = parser.parse_args()

target_input = args.target

# Domain → IP if needed
try:
    ip = socket.gethostbyname(target_input)
except socket.gaierror:
    print(red + "[!] Invalid domain or IP." + clear)
    sys.exit(1)

# Check for private/reserved IP ranges
try:
    ip_obj = ipaddress.ip_address(ip)
    if ip_obj.is_private or ip_obj.is_loopback or ip_obj.is_reserved or ip_obj.is_multicast:
        print(red + f"[!] {ip} is a private/reserved IP address. Skipping API call." + clear)
        sys.exit(1)
except ValueError:
    print(red + "[!] Not a valid IP address format." + clear)
    sys.exit(1)

# Query IP
api = f"http://ip-api.com/json/{ip}"

try:
    data = requests.get(api).json()
    if data['status'] != 'success':
        print(red + "[!] API failed: " + data.get('message', 'Unknown error') + clear)
        sys.exit(1)

    a = lgreen+bold+"[$]"
    b = cyan+bold+"[$]"

    print (a, "[Target IP]:", data['query'])
    print(red+"<--------------->"+red)
    print (b, "[ISP]:", data['isp'])
    print(red+"<--------------->"+red)
    print (a, "[Organisation]:", data['org'])
    print(red+"<--------------->"+red)
    print (b, "[City]:", data['city'])
    print(red+"<--------------->"+red)
    print (a, "[Region]:", data['region'])
    print(red+"<--------------->"+red)
    print (b, "[Longitude]:", data['lon'])
    print(red+"<--------------->"+red)
    print (a, "[Latitude]:", data['lat'])
    print(red+"<--------------->"+red)
    print (b, "[Time zone]:", data['timezone'])
    print(red+"<--------------->"+red)
    print (a, "[Zip code]:", data['zip'])
    print (" "+yellow)

    if args.output:
        with open(args.output, "w") as f:
            json.dump(data, f, indent=4)
        print(yellow + f"[+] Output saved to {args.output}" + clear)

except KeyboardInterrupt:
    print ('\n[!] Terminated by user'+lgreen)
    sys.exit(0)

except requests.exceptions.RequestException:
    print(red + "[!] Internet connection error!" + clear)
    sys.exit(1)
