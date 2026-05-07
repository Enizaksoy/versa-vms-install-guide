"""
Sample CPU/RAM/disk/IO/network every 30s during vsh configure.
Writes CSV + a markdown summary table for the install notes.
"""
import sys, os, time, datetime, csv, re
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from lib_ssh import VmsSSH

if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

HOST, USER, PASSWORD = '192.168.30.15', 'admin', '<vms-admin-pass>'
INTERVAL_SEC = 30
DURATION_MIN = 60  # cap at 60 min, exit early if user kills

LOG_DIR = r'C:\Claude\vms_install\logs'
os.makedirs(LOG_DIR, exist_ok=True)
ts = datetime.datetime.now().strftime('%Y%m%d_%H%M%S')
csv_path = os.path.join(LOG_DIR, f'telemetry_{ts}.csv')
md_path  = os.path.join(LOG_DIR, f'telemetry_{ts}.md')

s = VmsSSH(HOST, USER, PASSWORD)

samples = []
end = time.time() + DURATION_MIN * 60

print(f"=== Telemetry sampling every {INTERVAL_SEC}s, max {DURATION_MIN} min ===")
print(f"CSV: {csv_path}")
print(f"MD : {md_path}\n")
print(f"{'time':<19} {'load':<5} {'cpu_used':<9} {'mem_used_GB':<11} {'mem_buff_GB':<11} {'disk_used_GB':<12} {'rkBps':<7} {'wkBps':<7} {'top_proc':<25} {'phase':<40}")

iteration = 0
while time.time() < end:
    iteration += 1
    t0 = time.time()
    try:
        # Combined info in one shot
        rc, out, _ = s.run(
            "echo '###CPU'; top -bn1 | head -3; "
            "echo '###MEM'; free -m | head -2; "
            "echo '###DISK'; df -BM / | tail -1; "
            "echo '###IOSTAT'; iostat -dx 2 2 | grep -A1 'sda' | tail -2 || true; "
            "echo '###PROC'; ps -eo user,pcpu,pmem,rss,comm --sort=-pcpu --no-headers | head -3; "
            "echo '###PHASE'; ls -t /var/log/versa/vms/*.log 2>/dev/null | head -1 | xargs -I{} tail -1 {} 2>/dev/null || true",
            sudo=True, timeout=15, quiet=True
        )

        # Parse
        ts_str = datetime.datetime.now().strftime('%H:%M:%S')

        # Load + CPU usage from top
        load = '?'
        cpu_used = '?'
        m = re.search(r'load average:\s*([\d.]+)', out)
        if m: load = m.group(1)
        m = re.search(r'%Cpu.*?([\d.]+)\s+id', out)
        if m: cpu_used = f"{100 - float(m.group(1)):.1f}%"

        # Memory
        mem_used_gb = '?'
        mem_buff_gb = '?'
        m = re.search(r'^Mem:\s+(\d+)\s+(\d+)\s+\d+\s+\d+\s+(\d+)', out, re.MULTILINE)
        if m:
            mem_used_gb = f"{int(m.group(2))/1024:.1f}"
            mem_buff_gb = f"{int(m.group(3))/1024:.1f}"

        # Disk
        disk_used_gb = '?'
        m = re.search(r'^/dev/\S+\s+\d+M\s+(\d+)M', out, re.MULTILINE)
        if m: disk_used_gb = f"{int(m.group(1))/1024:.1f}"

        # IO from iostat (sda last sample)
        rkbps = '?'; wkbps = '?'
        # iostat output: name r/s w/s rkB/s wkB/s ...
        for line in out.split('\n'):
            if line.strip().startswith('sda'):
                parts = line.split()
                if len(parts) >= 5:
                    rkbps = parts[3]
                    wkbps = parts[4]

        # Top process
        top_proc = '?'
        m = re.search(r'###PROC\s*\n(\S+\s+\S+\s+\S+\s+\S+\s+\S+)', out)
        if m:
            cols = m.group(1).split()
            if len(cols) >= 5:
                top_proc = f"{cols[4]}({cols[1]}%cpu)"

        # Phase / current log line
        phase = '?'
        m = re.search(r'###PHASE\s*\n(.{0,80})', out)
        if m:
            phase = m.group(1).strip()[:38]

        sample = {
            'time': ts_str,
            'load': load,
            'cpu_used': cpu_used,
            'mem_used_GB': mem_used_gb,
            'mem_buff_GB': mem_buff_gb,
            'disk_used_GB': disk_used_gb,
            'rkBps': rkbps,
            'wkBps': wkbps,
            'top_proc': top_proc,
            'phase': phase,
        }
        samples.append(sample)
        print(f"{ts_str:<19} {load:<5} {cpu_used:<9} {mem_used_gb:<11} {mem_buff_gb:<11} {disk_used_gb:<12} {rkbps:<7} {wkbps:<7} {top_proc:<25} {phase:<40}")

        # Write CSV incrementally
        with open(csv_path, 'w', newline='', encoding='utf-8') as f:
            w = csv.DictWriter(f, fieldnames=list(samples[0].keys()))
            w.writeheader()
            w.writerows(samples)

    except Exception as e:
        print(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] sample error: {e}")
        time.sleep(5)

    # Sleep until next interval
    elapsed = time.time() - t0
    sleep_for = max(1, INTERVAL_SEC - elapsed)
    time.sleep(sleep_for)

s.close()

# Write markdown summary
with open(md_path, 'w', encoding='utf-8') as f:
    f.write(f"# VMS Install Telemetry — {ts}\n\n")
    f.write(f"Sample interval: {INTERVAL_SEC}s | Total samples: {len(samples)}\n\n")
    f.write("| Time | Load | CPU% | Mem GB | Buff GB | Disk GB | r kB/s | w kB/s | Top proc | Phase |\n")
    f.write("|------|------|------|--------|---------|---------|--------|--------|----------|-------|\n")
    for s in samples:
        f.write(f"| {s['time']} | {s['load']} | {s['cpu_used']} | {s['mem_used_GB']} | {s['mem_buff_GB']} | {s['disk_used_GB']} | {s['rkBps']} | {s['wkBps']} | {s['top_proc']} | {s['phase']} |\n")

print(f"\n=== Done. {len(samples)} samples logged. ===")
print(f"CSV: {csv_path}")
print(f"MD : {md_path}")
