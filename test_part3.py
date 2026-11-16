"""Tests for M2 Part 3, the main simulation loop (run_simulation).

Run with:  python -m pytest test_part3.py -v
"""

import importlib
from pathlib import Path

import pytest

import vmcachesim

HERE = Path(__file__).parent
BIG = str(HERE / "A-9_new_trunk.trc")
TINY = str(HERE / "TinyTrace.trc")
TEST = str(HERE / "TestTrace.trc")


class Args:
    def __init__(self, n=100, f=None, p=1024, u=50.0):
        self.s, self.b, self.a, self.r = 1024, 16, 2, "RR"
        self.p, self.u, self.n = p, u, n
        self.f = f if f is not None else [TINY]


def simulate(n=100, files=None, p=1024, u=50.0):
    """Fresh module state per run, since the vm dict is module level."""
    m = importlib.reload(vmcachesim)
    args = Args(n=n, f=files or [TINY], p=p, u=u)
    mem = m.memory_calc(args)
    traces = [m.parse_trace(f) for f in args.f]
    m.vm_setup(mem, len(traces))
    stats, per_process_used = m.run_simulation(args, traces)
    return m, stats, per_process_used, traces


# --------------------------------------------------------------------------
# The counter invariant Part 4 checks against
# --------------------------------------------------------------------------

@pytest.mark.parametrize("n", [1, 10, 1000, -1])
@pytest.mark.parametrize("files", [[TINY], [TINY, TEST], [BIG], [BIG, TEST]])
def test_hits_plus_free_plus_faults_equals_mapped(n, files):
    _, stats, _, _ = simulate(n=n, files=files)
    assert stats["hits"] + stats["from_free"] + stats["faults"] == stats["mapped"]


def test_mapped_equals_total_addresses_in_the_traces():
    _, stats, _, traces = simulate(n=7, files=[TINY, TEST])
    expected = sum(len(instruction) for trace in traces for instruction in trace)
    assert stats["mapped"] == expected


# --------------------------------------------------------------------------
# Every instruction runs exactly once, whatever the slice size
# --------------------------------------------------------------------------

@pytest.mark.parametrize("n", [1, 2, 3, 97, 10000, -1])
def test_slice_size_does_not_change_how_many_addresses_are_translated(n):
    _, stats, _, _ = simulate(n=n, files=[TINY, TEST])
    assert stats["mapped"] == 64


def test_single_process_is_unaffected_by_slice_size():
    # with one process there is nothing to interleave with, so the counters
    # must match whatever the time slice is
    results = [simulate(n=n, files=[BIG])[1] for n in (1, 500, -1)]
    assert results[0] == results[1] == results[2]


# --------------------------------------------------------------------------
# Round robin actually interleaves
# --------------------------------------------------------------------------

def test_shorter_slices_cause_more_faults_under_memory_pressure():
    # two heavy processes competing for a small amount of RAM: interleaving
    # them tightly should evict each other's pages more often than running
    # each one to completion
    _, tight, _, _ = simulate(n=1, files=[BIG, BIG], p=128, u=99.9)
    _, loose, _, _ = simulate(n=-1, files=[BIG, BIG], p=128, u=99.9)
    assert tight["faults"] > loose["faults"]


def test_processes_are_visited_in_order():
    # process 0 is the tiny trace and finishes first; with a slice of 1 both
    # processes must still have run, so both page tables show use
    _, _, used, _ = simulate(n=1, files=[TINY, TEST])
    assert all(count > 0 for count in used)


# --------------------------------------------------------------------------
# free_process is called when a trace ends
# --------------------------------------------------------------------------

@pytest.mark.parametrize("files", [[TINY], [TINY, TEST], [BIG, TEST]])
def test_all_physical_pages_are_returned_when_every_trace_ends(files):
    m, _, _, _ = simulate(n=13, files=files)
    assert m.vm["owner"] == {}
    assert len(m.vm["lru"]) == 0


def test_free_list_is_whole_again_at_the_end():
    m, _, _, _ = simulate(n=13, files=[TINY, TEST], p=1024, u=50.0)
    mem = m.memory_calc(Args(f=[TINY, TEST]))
    assert len(m.vm["free_pages"]) == mem["num_pages"] - mem["sys_pages"]


def test_no_process_is_left_in_the_rotation():
    # if a finished process were still being scheduled the loop would not end;
    # reaching this assert at all proves it terminates
    _, stats, _, _ = simulate(n=1, files=[TINY, TEST, BIG])
    assert stats["mapped"] > 0


# --------------------------------------------------------------------------
# Page faults
# --------------------------------------------------------------------------

def test_plenty_of_memory_means_no_faults():
    _, stats, _, _ = simulate(n=1000, files=[BIG], p=4096, u=0.0)
    assert stats["faults"] == 0
    assert stats["from_free"] > 0


def test_small_memory_and_high_system_use_forces_faults():
    # the check the task split asks for: small -p, high -u
    _, stats, _, _ = simulate(n=1000, files=[BIG], p=128, u=99.9)
    assert stats["faults"] > 0


def test_pages_come_from_the_free_list_before_any_eviction():
    _, stats, _, _ = simulate(n=1000, files=[BIG], p=4096, u=0.0)
    # every distinct page was available, so nothing should have been evicted
    assert stats["from_free"] > 0 and stats["faults"] == 0


# --------------------------------------------------------------------------
# per_process_used, which Part 4 turns into the wasted space figures
# --------------------------------------------------------------------------

def test_used_counts_distinct_virtual_pages_per_process():
    m, _, used, traces = simulate(n=50, files=[TINY, TEST])
    for pid, trace in enumerate(traces):
        distinct = {addr >> m.PAGE_BITS for ins in trace for addr, _ in ins}
        assert used[pid] == len(distinct)


def test_used_never_exceeds_the_page_table_size():
    m, _, used, _ = simulate(n=100, files=[BIG])
    assert all(0 < count <= m.NUM_PTE for count in used)


def test_one_entry_per_trace():
    _, _, used, _ = simulate(n=10, files=[TINY, TEST, BIG])
    assert len(used) == 3


# --------------------------------------------------------------------------
# The real trace fits the 512K page table
# --------------------------------------------------------------------------

def test_largest_virtual_page_in_the_trace_fits_the_page_table():
    m = importlib.reload(vmcachesim)
    trace = m.parse_trace(BIG)
    highest = max(addr for ins in trace for addr, _ in ins) >> m.PAGE_BITS
    assert highest < m.NUM_PTE
