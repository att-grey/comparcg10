import argparse
import math
import os
import sys
import re
from collections import OrderedDict

TEAM = "10"
COST_PER_KB = 0.07
PAGE_SIZE = 4096
NUM_PTE = 512 * 1024

VALID_CACHE_KB = [8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, 8192]
VALID_BLOCK = [4, 8, 16, 32, 64]
VALID_ASSOC = [1, 2, 4, 8, 16]
VALID_PHYS_MB = [128, 256, 512, 1024, 2048, 4096]

def parse_args():
    p = argparse.ArgumentParser(description="CS 3853 VM & Cache Simulator")
    p.add_argument("-s", type=int, required=True, help="cache size in KB")
    p.add_argument("-b", type=int, required=True, help="block size in bytes")
    p.add_argument("-a", type=int, required=True, help="associativity")
    p.add_argument("-r", type=str, required=True, help="RR or RND")
    p.add_argument("-p", type=int, required=True, help="physical memory in MB")
    p.add_argument("-u", type=float, required=True, help="percent memory used by OS")
    p.add_argument("-n", type=int, required=True, help="instructions per time slice")
    p.add_argument("-f", action="append", required=True, help="trace file")
    return p.parse_args()

def validate(args):
    errors = []

    if args.a not in VALID_ASSOC:
        errors.append("associativity must be 1, 2, 4, 8, or 16")

    if args.b not in VALID_BLOCK:
        errors.append("block size must be 4, 8, 16, 32, or 64")

    if args.p not in VALID_PHYS_MB:
        errors.append("physical memory must be 128, 256, 512, 1024, 2048, or 4096")

    if args.s not in VALID_CACHE_KB:
        errors.append("cache size must be 8, 16, 32, 64, 128, 256, 512, 1024, 2048, 4096, or 8192")

    args.r = args.r.upper()
    if args.r not in ("RR", "RND"):
        errors.append("replacement policy must be RR or RND")
    
    if not 0 <= args.u <= 100:
        errors.append("percent used by OS must be between 0 and 100")
   
    if args.n == 0 or args.n < -1:
        errors.append("instructions per time slice must be 1 or more, or -1 for max")
#file reading errors
    if not 1 <= len(args.f) <= 3:
        errors.append("you must give 1 to 3 trace files")
    for f in args.f:
        if not os.path.isfile(f):
            errors.append(f"trace file not found: {f}")
    #converts cache and memory to bytes and compares size
    if args.s * 1024 >= args.p * 1024 * 1024:
        errors.append("cache must be smaller than physical memory")

    if errors:
            for e in errors:
                print("Error:", e, file=sys.stderr)
            sys.exit(1)


def cache_calc(args):
    cache_bytes = args.s * 1024
    phys_bytes = args.p * 1024 * 1024

    total_blocks = cache_bytes // args.b
    rows = total_blocks // args.a
    offset_bits = int(math.log2(args.b))
    index_bits = int(math.log2(rows))
    phys_addr_bits = int(math.log2(phys_bytes))
    tag_bits = phys_addr_bits - index_bits - offset_bits

    # each block stores its tag plus 1 valid bit
    overhead_bytes = total_blocks * (tag_bits + 1) // 8
    impl_bytes = cache_bytes + overhead_bytes
    impl_kb = impl_bytes / 1024
    cost = impl_kb * COST_PER_KB

    return {
        "total_blocks": total_blocks,
        "tag_bits": tag_bits,
        "index_bits": index_bits,
        "offset_bits": offset_bits,
        "rows": rows,
        "overhead_bytes": overhead_bytes,
        "impl_bytes": impl_bytes,
        "impl_kb": impl_kb,
        "cost": cost,
    }

def memory_calc(args):
    memory_bytes = args.p * 1024 * 1024
    total_pages = memory_bytes // PAGE_SIZE
    system_pages = int(total_pages * (args.u / 100))
    page_number_bits = int(math.log2(total_pages))
    pte_bits = page_number_bits + 1
    pt_ram_bytes = (NUM_PTE * len(args.f) * pte_bits) // 8

    return {
        "num_pages": total_pages,
        "sys_pages": system_pages,
        "pte_bits": pte_bits,
        "pt_ram_bytes": pt_ram_bytes
    }

def print_output(args, cache, mem):
    policy = "Round Robin" if args.r == "RR" else "Random"
    time_slice = "max" if args.n == -1 else args.n

    def line(label, value):
        print(f"{label:<40}{value}")

    print(f"Cache Simulator - CS 3853 - Team #{TEAM}")
    print()
    print("Trace File(s):")
    for f in args.f:
        print(f"\t{f}")

    print()
    print("***** Cache Input Parameters *****")
    print()
    line("Cache Size:", f"{args.s} KB")
    line("Block Size:", f"{args.b} bytes")
    line("Associativity:", args.a)
    line("Replacement Policy:", policy)
    line("Physical Memory:", f"{args.p} MB")
    line("Percent Memory Used by System:", f"{args.u:.1f}%")
    line("Instructions / Time Slice:", time_slice)

    print()
    print("***** Cache Calculated Values *****")
    print()
    line("Total # Blocks:", cache["total_blocks"])
    line("Tag Size:", f"{cache['tag_bits']} bits")
    line("Index Size:", f"{cache['index_bits']} bits")
    line("Total # Rows:", cache["rows"])
    line("Overhead Size:", f"{cache['overhead_bytes']} bytes")
    line("Implementation Memory Size:", f"{cache['impl_kb']:.2f} KB ({cache['impl_bytes']} bytes)")
    line("Cost:", f"${cache['cost']:.2f} @ ${COST_PER_KB:.2f} per KB")

    print()
    print("***** Physical Memory Calculated Values *****")
    print()
    line("Number of Physical Pages:", mem["num_pages"])
    line("Number of Pages for System:", mem["sys_pages"])
    line("Size of Page Table Entry:", f"{mem['pte_bits']} bits")
    line("Total RAM for Page Table(s):", f"{mem['pt_ram_bytes']} bytes")

def parse_trace(filename):
    instructions = []

    eip_pattern = re.compile(
        r"^EIP\s*\(\s*(\d+)\s*\):\s*([0-9a-fA-F]{8})",
        re.IGNORECASE
    )

    data_pattern = re.compile(
        r"dstM:\s*([0-9a-fA-F]{8})\s+(\S+)\s+"
        r"srcM:\s*([0-9a-fA-F]{8})\s+(\S+)",
        re.IGNORECASE
    )

    with open(filename, "r") as trace_file:
        #to ignore blank lines
        lines = [line.strip() for line in trace_file if line.strip()]

    if len(lines) % 2 != 0:
        raise ValueError("Trace file has incomplete instruction.")

    for i in range(0, len(lines), 2):
        eip_line = lines[i]
        data_line = lines[i + 1]

        #extract instruction length and address
        eip_match = eip_pattern.match(eip_line)

        if not eip_match:
            raise ValueError(
                f"Invalid EIP format near line {i + 1}"
            )

        #instruction length is decimal
        instruction_length = int(eip_match.group(1))

        #address is hexadecimal
        instruction_address = int(eip_match.group(2), 16)

        if instruction_length <= 0:
            raise ValueError("Instruction length must be positive.")

        accesses = [
            (instruction_address, instruction_length)
        ]

        data_match = data_pattern.search(data_line)

        if not data_match:
            raise ValueError(
                f"Invalid memory access format near line {i + 2}"
            )

        dst_address = int(data_match.group(1), 16)
        dst_data = data_match.group(2)

        src_address = int(data_match.group(3), 16)
        src_data = data_match.group(4)

        #destination memory access
        if dst_address != 0 and dst_data != "--------":
            accesses.append((dst_address, 4))

        #source memory access
        if src_address != 0 and src_data != "--------":
            accesses.append((src_address, 4))

        instructions.append(accesses)

    return instructions

PAGE_BITS = 12

vm = {}

def vm_setup(mem, num_procs):
    total_pages = mem["num_pages"]
    system_pages = mem["sys_pages"]

#table entry = valif bit + phy page num
    vm["valid"] = [[0] * NUM_PTE for _ in range(num_procs)]
    vm["ppn"] = [[0] * NUM_PTE for _ in range(num_procs)]

# pages the os isn't using 
    vm["free_pages"] = list(range(system_pages, total_pages))

#phys page
    vm["owner"] = {}

#pages in use, least recent user first
    vm["lru"] = OrderedDict()

#page table entries each process has used
    vm["used"] = [set() for _ in range(num_procs)]

    vm["hits"] = 0
    vm["from_free"] = 0
    vm["faults"] = 0

def invalidate_cache(phys_page):
    #hold for m3
    pass

def map_page(pid, vpage, page):
    #point process' page table entry at phy page

    vm["valid"][pid][vpage] = 1
    vm["ppn"][pid][vpage] = page
    vm["owner"][page] = (pid, vpage)

    # newest = most recently used
    vm["lru"][page] = True
    vm["used"][pid].add(vpage)

def translate(pid, vaddr):
    #map vitrual page add for a process, hit,free, fault
    vpage = vaddr >> PAGE_BITS

    #Hit
    if vm["valid"][pid][vpage]:
        page = vm["ppn"][pid][vpage]
        vm["lru"].move_to_end(page)   # slide 28 use bit: mark as just used
        vm["hits"] += 1
        return "hit"

    #Free
    if vm["free_pages"]:
        page = vm["free_pages"].pop()
        map_page(pid, vpage, page)
        vm["from_free"] += 1
        return "free"

    #Fault
    page, _ = vm["lru"].popitem(last=False)
    old_pid, old_vpage = vm["owner"][page]
    vm["valid"][old_pid][old_vpage] = 0   # unmap it from the old owner
    invalidate_cache(page)
    map_page(pid, vpage, page)
    vm["faults"] += 1
    return "fault"

def free_process(pid):
    #when a trace ends, give all phy pages back
    pages = [page for page, (owner_pid, _) in vm["owner"].items() if owner_pid == pid]
    for page in pages:
        _, vpage = vm["owner"][page]
        vm["valid"][pid][vpage] = 0
        del vm["owner"][page]
        del vm["lru"][page]
        invalidate_cache(page)
        vm["free_pages"].append(page)

def run_simulation(args, traces):
    #part 3: round robin the processes, n instructions each, until all traces end

    #instructions per slice, -1 means run the whole trace in one turn
    slice_size = args.n

    #next instruction each process still has to run
    pos = [0] * len(traces)

    #pids still in the rotation, in order
    active = list(range(len(traces)))

    #every address we hand to translate()
    vm["mapped"] = 0

    while active:
        finished = []

        for pid in active:
            start = pos[pid]
            if slice_size == -1:
                stop = len(traces[pid])
            else:
                stop = min(start + slice_size, len(traces[pid]))

            for instruction in traces[pid][start:stop]:
                for address, _length in instruction:
                    translate(pid, address)
                    vm["mapped"] += 1

            pos[pid] = stop

            #trace is done, give its pages back and drop it from the rotation
            if pos[pid] >= len(traces[pid]):
                free_process(pid)
                finished.append(pid)

        for pid in finished:
            active.remove(pid)

    stats = {
        "mapped": vm["mapped"],
        "hits": vm["hits"],
        "from_free": vm["from_free"],
        "faults": vm["faults"],
    }

    #page table entries each process touched, for the wasted space numbers
    per_process_used = [len(used) for used in vm["used"]]

    return stats, per_process_used

def print_m2_results(stats, per_process_used, trace_names, mem):
    #part 4: print the virtual memory results after the M1 output

    def line(label, value, indent=""):
        print(f"{indent}{label:<{40 - len(indent.expandtabs())}}{value}")

    tab = "\t"
    user_pages = mem["num_pages"] - mem["sys_pages"]

    #every translated address is a hit, a page from free, or a fault
    total = stats["hits"] + stats["from_free"] + stats["faults"]
    if total != stats["mapped"]:
        print(f"WARNING: hits + from free + faults = {total}, "
              f"but virtual pages mapped = {stats['mapped']}", file=sys.stderr)

    print()
    print("***** VIRTUAL MEMORY SIMULATION RESULTS *****")
    print()
    line("Physical Pages Used By SYSTEM:", mem["sys_pages"])
    line("Pages Available to User:", user_pages)
    print()
    line("Virtual Pages Mapped:", stats["mapped"])
    print(f"{tab}------------------------------")
    line("Page Table Hits:", stats["hits"], tab)
    print()
    line("Pages from Free:", stats["from_free"], tab)
    print()
    line("Total Page Faults:", stats["faults"], tab)
    print()
    print()
    print("Page Table Usage Per Process:")
    print("------------------------------")

    for pid, name in enumerate(trace_names):
        used = per_process_used[pid]
        percent = used / NUM_PTE * 100
        #unused entries * 19 bits each, in bytes, truncated
        wasted = (NUM_PTE - used) * mem["pte_bits"] // 8

        print(f"[{pid}] {name}:")
        line("Used Page Table Entries:", f"{used} ({percent:5.2f}%)", tab)
        line("Page Table Wasted:", f"{wasted} bytes", tab)
        print()

def main():
    args = parse_args()
    validate(args)
    cache = cache_calc(args)
    mem = memory_calc(args)
    print_output(args, cache, mem)

    traces = [parse_trace(f) for f in args.f]
    vm_setup(mem, len(traces))
    stats, per_process_used = run_simulation(args, traces)

    print_m2_results(stats, per_process_used, args.f, mem)

if __name__ == "__main__":
    main()