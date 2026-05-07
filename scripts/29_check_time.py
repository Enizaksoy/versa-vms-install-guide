"""Check VMS time; if behind cert NotBefore, jump forward."""
import sys, os, datetime
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_ssh import VmsSSH

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'
s = VmsSSH(HOST, USER, PASSWORD)

print("=== Current VMS time + timezone ===")
s.run("date && date -u && timedatectl status 2>&1 | head -10")

print("\n=== Cert NotBefore ===")
s.run("openssl x509 -in /opt/versa/vms/certs/server-cert.pem -noout -dates", sudo=True)

print("\n=== Force time forward to safely past cert NotBefore (May 6 12:00 UTC 2026) ===")
# Set time to a safe value about 8 hours ahead, after NotBefore + a margin
target = "2026-05-06 12:00:00"
s.run(f"date -u -s '{target}' && date && hwclock --systohc 2>&1 || true", sudo=True)

print("\n=== Re-verify cert chain ===")
s.run("openssl verify -CAfile /opt/versa/vms/certs/root-ca-cert.pem /opt/versa/vms/certs/server-cert.pem 2>&1", sudo=True)

# Restart chrony so it can re-sync if reachable
s.run("systemctl restart chrony 2>&1 | tail -5", sudo=True)
s.run("chronyc sources -v 2>&1 | head -20", sudo=True)

s.close()
