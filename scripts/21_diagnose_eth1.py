"""Diagnose why eth1 cannot reach 192.168.20.254 (CA + DNS server)."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_ssh import VmsSSH

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'
s = VmsSSH(HOST, USER, PASSWORD)

print("=== Interface state ===")
s.run("ip -br addr")
s.run("ethtool eth1 | grep -E 'Link|Speed|Duplex' 2>&1", sudo=True)

print("=== ARP for 192.168.20.254 ===")
s.run("arp -an | grep 192.168.20 || echo 'no arp entry'")
s.run("ip neigh show dev eth1")

print("=== Probe with arping ===")
s.run("arping -c 3 -I eth1 192.168.20.254 2>&1 || echo 'arping unavailable'", sudo=True)

print("=== ARP-level probe ===")
s.run("timeout 3 ping -c 2 -W 2 -I eth1 192.168.20.254 2>&1; echo rc=$?")
s.run("ip neigh show 192.168.20.254")

print("=== TCP connectivity tests via different paths ===")
# Try via eth0 (default route, would go to 192.168.30.4 gateway)
s.run("curl -m 5 --interface eth0 -s -o /dev/null -w 'HTTP via eth0: %{http_code} (rc=%{exitcode})\\n' http://192.168.20.254/ 2>&1")
# Try via eth1 explicitly
s.run("curl -m 5 --interface eth1 -s -o /dev/null -w 'HTTP via eth1: %{http_code}\\n' http://192.168.20.254/ 2>&1")

print("=== rp_filter / forwarding ===")
s.run("sysctl net.ipv4.conf.all.rp_filter net.ipv4.conf.eth1.rp_filter net.ipv4.ip_forward")

print("=== /proc/net/dev counters ===")
s.run("cat /proc/net/dev | grep -E 'eth0|eth1'")

print("=== DNS resolution test ===")
s.run("getent hosts mylab.com 2>&1 || true")
s.run("dig +short +timeout=3 +tries=1 @192.168.20.254 mylab.com 2>&1 || true")

# Try from eth0 to itself just to confirm Internet reachability
print("=== Internet reachability via eth0 ===")
s.run("curl -m 5 --interface eth0 -s -o /dev/null -w 'HTTP google: %{http_code}\\n' http://www.google.com/ 2>&1")
s.run("ping -c 2 -W 2 8.8.8.8 2>&1 | tail -3")

s.close()
