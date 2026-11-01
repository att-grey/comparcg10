import argparse
import math
import os
import sys

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
    #add

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

    # TODO once memory_calc is done
    if mem is not None:
        print()
        print("***** Physical Memory Calculated Values *****")
        print()
        line("Number of Physical Pages:", mem["num_pages"])
        line("Number of Pages for System:", mem["sys_pages"])
        line("Size of Page Table Entry:", f"{mem['pte_bits']} bits")
        line("Total RAM for Page Table(s):", f"{mem['pt_ram_bytes']} bytes")

def main():
    args = parse_args()
    validate(args)
    cache = cache_calc(args)
    mem = memory_calc(args)
    print_output(args, cache, mem)

if __name__ == "__main__":
    main()
