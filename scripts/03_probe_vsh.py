"""Probe vsh commands to see interactive prompts before scripting."""
import sys, time
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import paramiko

HOST = '192.168.30.15'
USER = 'admin'
PASSWORD = '<default-ova-pass>'

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PASSWORD, timeout=15,
          allow_agent=False, look_for_keys=False)

# Check DNS state
def run(cmd, sudo=False):
    full = f"echo '{PASSWORD}' | sudo -S -p '' bash -lc \"{cmd}\"" if sudo else f"bash -lc \"{cmd}\""
    print(f"$ {cmd}")
    _, o, e = c.exec_command(full, timeout=20)
    rc = o.channel.recv_exit_status()
    print(o.read().decode(errors='replace').rstrip())
    err = e.read().decode(errors='replace')
    if err.strip() and 'password for' not in err:
        print(f"[err] {err.rstrip()}")
    print(f"[rc={rc}]\n")

run("which vsh")
run("cat /etc/resolv.conf")
run("ping -c 2 -W 2 192.168.20.254")
run("ping -c 2 -W 2 8.8.8.8")
run("nslookup pool.ntp.org 2>&1 | head -10")
run("vsh help 2>&1 | head -40")
run("vsh status 2>&1 | head -30")

# Probe add-name-servers help
run("vsh add-name-servers --help 2>&1 | head -20")
run("vsh update-network-time --help 2>&1 | head -20")
run("vsh modify-system-password --help 2>&1 | head -20")

c.close()
