"""
Grow sda1 partition + LVM PV + LV + ext4 to fill 1 TB.
Sequence:
  growpart /dev/sda 1   -> partition to 1T
  pvresize /dev/sda1    -> LVM PV picks up new size
  lvextend +100%FREE    -> root LV consumes free PE
  resize2fs             -> ext4 fills LV
"""
import sys
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
import paramiko

HOST = '192.168.30.15'
USER = 'admin'
PASSWORD = '<default-ova-pass>'

def run(c, cmd, sudo=True, timeout=120):
    full = f"echo '{PASSWORD}' | sudo -S -p '' bash -c \"{cmd}\"" if sudo else cmd
    print(f"$ {cmd}")
    _, o, e = c.exec_command(full, timeout=timeout)
    rc = o.channel.recv_exit_status()
    out = o.read().decode(errors='replace')
    err = e.read().decode(errors='replace')
    if out.strip(): print(out.rstrip())
    if err.strip() and 'password for' not in err:
        print(f"[err] {err.rstrip()}")
    print(f"[rc={rc}]\n")
    return rc

c = paramiko.SSHClient()
c.set_missing_host_key_policy(paramiko.AutoAddPolicy())
c.connect(HOST, username=USER, password=PASSWORD, timeout=15,
          allow_agent=False, look_for_keys=False)

print("=== BEFORE ===")
run(c, "df -h /")
run(c, "lsblk")

print("=== Grow partition ===")
# growpart is in cloud-utils. Verify it exists, fallback to parted if not.
rc = run(c, "which growpart || apt-get install -y cloud-guest-utils 2>&1 | tail -5")
run(c, "growpart /dev/sda 1")

print("=== Re-read partition table ===")
run(c, "partprobe /dev/sda || true")
run(c, "lsblk")

print("=== Resize LVM PV ===")
run(c, "pvresize /dev/sda1")
run(c, "pvs")

print("=== Extend LV root ===")
run(c, "lvextend -l +100%FREE /dev/mapper/system-root")
run(c, "lvs")

print("=== Resize ext4 ===")
run(c, "resize2fs /dev/mapper/system-root")

print("=== AFTER ===")
run(c, "df -h /")
run(c, "lsblk")

c.close()
