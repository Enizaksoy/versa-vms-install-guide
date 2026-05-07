"""Test vsh status with PTY allocated."""
import sys, os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_ssh import VmsSSH

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'
s = VmsSSH(HOST, USER, PASSWORD)

# Re-test vsh status with PTY
rc, out, _ = s.vsh("status", timeout=60)

print("\n=== Result analysis ===")
print(f"rc = {rc}")
print(f"default password warning: {'default/expired passwords' in out}")
print(f"server requirements not met: {'Server requirements not met' in out}")
print(f"sudo no tty errors: {'no tty present' in out}")

s.close()
