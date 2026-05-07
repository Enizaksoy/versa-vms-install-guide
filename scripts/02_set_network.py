"""
Phase 1 step 1: Push static network config + hostname + /etc/hosts, then reboot.
After reboot, VM should come up at 192.168.30.15.

Plan:
  - eth0: static 192.168.30.15/24 gw 192.168.30.4, DNS 192.168.20.254
  - eth1: static 192.168.20.15/24 (no gw, MTU 1500)
  - eth2: skip
  - hostname: vms-1
  - FQDN: vms-1.mylab.com
  - /etc/hosts: vms-1, vms-1-elastic, vms-vos
  - Reboot via 'shutdown -r +1' so SSH session can disconnect cleanly
"""
import sys, time
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import paramiko

OLD_HOST = '192.168.30.59'
NEW_HOST = '192.168.30.15'
USER = 'admin'
PASSWORD = '<default-ova-pass>'

NEW_INTERFACES = """\
# interfaces(5) file used by ifup(8) and ifdown(8)
# Managed by VMS install (C:\\Claude\\vms_install)
source-directory /etc/network/interfaces.d

auto lo
iface lo inet loopback

auto eth0
iface eth0 inet static
    address 192.168.30.15
    netmask 255.255.255.0
    gateway 192.168.30.4
    dns-nameservers 192.168.20.254 8.8.8.8
    dns-search mylab.com

auto eth1
iface eth1 inet static
    address 192.168.20.15
    netmask 255.255.255.0
    mtu 1500
"""

NEW_HOSTS = """\
127.0.0.1\tlocalhost
127.0.1.1\tvms-1

# VMS FQDNs
192.168.30.15\tvms-1.mylab.com vms-1
192.168.30.16\tvms-1-elastic.mylab.com vms-1-elastic
192.168.20.15\tvms-vos.mylab.com vms-vos

# IPv6
::1     localhost ip6-localhost ip6-loopback
ff02::1 ip6-allnodes
ff02::2 ip6-allrouters
"""

NEW_HOSTNAME = "vms-1\n"

def run(c, cmd, sudo=False, label=None):
    full = f"echo '{PASSWORD}' | sudo -S -p '' bash -c \"{cmd}\"" if sudo else cmd
    if label:
        print(f"[{label}] $ {cmd}")
    _, o, e = c.exec_command(full, timeout=60)
    rc = o.channel.recv_exit_status()
    out = o.read().decode(errors='replace')
    err = e.read().decode(errors='replace')
    if out.strip(): print(out.rstrip())
    if err.strip() and 'password for admin' not in err and 'No passwd entry' not in err:
        print(f"[err] {err.rstrip()}")
    print(f"[rc={rc}]\n")
    return rc, out, err

def put_file_via_sudo(c, content, dest_path, label):
    """Write content to dest_path using sudo tee (avoids needing root SFTP)."""
    print(f"[{label}] writing {dest_path}")
    # Escape single quotes for here-doc inside double-quoted bash -c
    # Use base64 to avoid all escaping issues
    import base64
    b64 = base64.b64encode(content.encode()).decode()
    cmd = f"echo {b64} | base64 -d > {dest_path}"
    return run(c, cmd, sudo=True, label=label)

def main():
    print(f"=== Connecting to {OLD_HOST} ===")
    c = paramiko.SSHClient()
    c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
    c.connect(OLD_HOST, username=USER, password=PASSWORD, timeout=15,
              allow_agent=False, look_for_keys=False)
    print("Connected.\n")

    # 1. Backup originals
    run(c, "cp /etc/network/interfaces /etc/network/interfaces.bak.$(date +%s)", sudo=True, label="backup-interfaces")
    run(c, "cp /etc/hosts /etc/hosts.bak.$(date +%s)", sudo=True, label="backup-hosts")
    run(c, "cp /etc/hostname /etc/hostname.bak.$(date +%s)", sudo=True, label="backup-hostname")

    # 2. Write new files
    put_file_via_sudo(c, NEW_INTERFACES, "/etc/network/interfaces", "write-interfaces")
    put_file_via_sudo(c, NEW_HOSTS,      "/etc/hosts",              "write-hosts")
    put_file_via_sudo(c, NEW_HOSTNAME,   "/etc/hostname",           "write-hostname")

    # 3. Show what we wrote (for the log)
    print("=== Verification ===")
    run(c, "cat /etc/network/interfaces", sudo=True, label="verify-interfaces")
    run(c, "cat /etc/hosts",              sudo=False, label="verify-hosts")
    run(c, "cat /etc/hostname",           sudo=False, label="verify-hostname")

    # 4. Schedule reboot in 1 minute so this SSH can exit cleanly
    print("=== Scheduling reboot in 1 minute ===")
    run(c, "shutdown -r +1 'VMS install: applying static network config'", sudo=True, label="reboot")

    c.close()
    print(f"\nReboot scheduled. Waiting 90s before reconnect attempt to {NEW_HOST}...")

    # 5. Wait + try to reconnect at new IP
    time.sleep(90)

    print(f"\n=== Polling new IP {NEW_HOST} ===")
    for attempt in range(1, 21):
        print(f"[{attempt}/20] connecting to {NEW_HOST}...", end=' ')
        try:
            c2 = paramiko.SSHClient()
            c2.set_missing_host_key_policy(paramiko.AutoAddPolicy())
            c2.connect(NEW_HOST, username=USER, password=PASSWORD, timeout=8,
                       allow_agent=False, look_for_keys=False, banner_timeout=10)
            print("CONNECTED")
            run(c2, "hostname", label="post-reboot-hostname")
            run(c2, "ip -br addr", label="post-reboot-ip")
            run(c2, "ip route", label="post-reboot-route")
            c2.close()
            print(f"\n=== SUCCESS: VMS reachable at {NEW_HOST} ===")
            return 0
        except Exception as e:
            print(f"fail ({type(e).__name__})")
            time.sleep(15)

    print(f"\nFAILED to reach {NEW_HOST} after polling. Check ESXi console.")
    return 1

if __name__ == '__main__':
    sys.exit(main())
