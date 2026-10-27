import argparse
import math
import os
import sys

TEAM = "XX"
COST_PER_KB = 0.07
PAGE_SIZE = 4096
NUM_PTE = 512 * 1024

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

def main():
    args = parse_args()
    print(args)

if __name__ == "__main__":
    main()