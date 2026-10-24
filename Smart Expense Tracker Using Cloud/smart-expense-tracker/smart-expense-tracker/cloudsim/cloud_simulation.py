"""
CloudSim-style simulation (pure Python, runs directly in VS Code - no Java needed).

Models the Smart Expense Tracker backend on a cloud data centre:
  * Hosts -> VMs (like AWS EC2 instances) -> Cloudlets (user requests)
  * Compares a fixed 1-VM deployment with an auto-scaled deployment
  * Prints response time, VM utilisation and an estimated cost

Run:  python cloudsim/cloud_simulation.py
"""
import random
from dataclasses import dataclass, field

random.seed(42)

VM_MIPS = 1000           # processing speed of one VM (like a t3.small)
VM_COST_PER_HOUR = 0.02  # USD, illustrative
REQUEST_LENGTH = (200, 800)  # million instructions per request (add expense, summary, export...)


@dataclass
class Vm:
    vm_id: int
    free_at: float = 0.0
    busy_time: float = 0.0
    started_at: float = 0.0


@dataclass
class Datacenter:
    max_vms: int
    vms: list = field(default_factory=list)

    def add_vm(self, now):
        if len(self.vms) < self.max_vms:
            self.vms.append(Vm(len(self.vms), free_at=now, started_at=now))

    def schedule(self, now, length):
        vm = min(self.vms, key=lambda v: max(v.free_at, now))   # least-loaded VM
        start = max(vm.free_at, now)
        run = length / VM_MIPS
        vm.free_at = start + run
        vm.busy_time += run
        return start + run - now  # response time


def make_workload(duration=600):
    """Requests per second: quiet, then a salary-day / month-end spike, then quiet."""
    requests = []
    for t in range(duration):
        rate = 2 if t < 200 else 9 if t < 400 else 2
        for _ in range(random.randint(max(rate - 1, 0), rate + 1)):
            requests.append((t + random.random(), random.randint(*REQUEST_LENGTH)))
    return sorted(requests)


def run(name, workload, autoscale, duration=600):
    dc = Datacenter(max_vms=6)
    dc.add_vm(0)
    responses, window = [], []
    for arrival, length in workload:
        if autoscale:
            backlog = max(v.free_at for v in dc.vms) - arrival
            if backlog > 2.0:       # scale out when queue wait is high
                dc.add_vm(arrival)
        rt = dc.schedule(arrival, length)
        responses.append(rt)
        window.append(rt)
    end = max(duration, max(v.free_at for v in dc.vms))
    vm_hours = sum(end - v.started_at for v in dc.vms) / 3600
    util = sum(v.busy_time for v in dc.vms) / sum(end - v.started_at for v in dc.vms) * 100
    responses.sort()
    print(f"\n=== {name} ===")
    print(f"Requests served      : {len(responses)}")
    print(f"VMs used             : {len(dc.vms)}")
    print(f"Avg response time    : {sum(responses) / len(responses):.2f} s")
    print(f"95th pct response    : {responses[int(len(responses) * 0.95)]:.2f} s")
    print(f"Max response time    : {responses[-1]:.2f} s")
    print(f"Avg VM utilisation   : {util:.1f} %")
    print(f"Estimated cost       : ${vm_hours * VM_COST_PER_HOUR:.4f} for this run")


if __name__ == "__main__":
    load = make_workload()
    print("Smart Expense Tracker - cloud scaling simulation")
    run("Fixed deployment (1 VM)", load, autoscale=False)
    run("Auto-scaled deployment (up to 6 VMs)", load, autoscale=True)
    print("\nConclusion: auto-scaling keeps response time low during spikes by adding VMs on demand.")
