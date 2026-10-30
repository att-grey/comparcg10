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
    #add

def memory_calc(args):
    #hayli will add
    #testing this lol

def print_output(args, cache, mem):
    #add

def main():
    args = parse_args()
    validate(args)
    cache = cache_calc(args)
    mem = memory_calc(args)
    print_output(args, cache, mem)

if __name__ == "__main__":
    main()