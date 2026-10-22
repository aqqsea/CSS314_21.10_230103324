import os
import platform
import random
import time
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import shared_memory

STUDENT_ID = "230103324"
ARRAY_SIZE = 20_000_000
P = 0.95

# Shared data attached by each worker process
_shared_memory = None
_data = None


def init_worker(shm_name, array_size):
    global _shared_memory, _data
    _shared_memory = shared_memory.SharedMemory(name=shm_name)
    _data = _shared_memory.buf.cast("d")[:array_size]


def sum_chunk(bounds):
    start, end = bounds
    total = 0.0
    for i in range(start, end):
        total += _data[i]
    return total


def amdahl_bound(workers):
    return 1.0 / ((1.0 - P) + P / workers)


def benchmark(shm_name, workers):
    chunk_size = (ARRAY_SIZE + workers - 1) // workers
    chunks = [
        (start, min(start + chunk_size, ARRAY_SIZE))
        for start in range(0, ARRAY_SIZE, chunk_size)
    ]

    start_time = time.perf_counter()

    with ProcessPoolExecutor(
        max_workers=workers,
        initializer=init_worker,
        initargs=(shm_name, ARRAY_SIZE)
    ) as executor:
        partial_sums = list(executor.map(sum_chunk, chunks))

    elapsed = time.perf_counter() - start_time
    total = sum(partial_sums)

    return elapsed, total


def main():
    max_cores = os.cpu_count() or 1
    worker_counts = list(dict.fromkeys(
        [1, 2, 4, max_cores, max_cores * 2]
    ))

    print("=== TASK 2: Multi-Core Scaling vs. Amdahl's Law ===")
    print(f"Student ID: {STUDENT_ID}")
    print(f"Operating System: {platform.platform()}")
    print(f"CPU Architecture: {platform.machine()}")
    print(f"Logical CPU Cores: {max_cores}")
    print(f"Array Size: {ARRAY_SIZE:,}")
    print(f"Parallelizable Fraction (P): {P}")
    print(f"Worker Counts: {worker_counts}")

    print("\nGenerating float64 array...")
    shm = shared_memory.SharedMemory(
        create=True, size=ARRAY_SIZE * 8
    )
    data = shm.buf.cast("d")[:ARRAY_SIZE]

    rng = random.Random(STUDENT_ID)
    for i in range(ARRAY_SIZE):
        data[i] = rng.random()

    del data
    print("Array generated successfully.")

    results = []
    reference_sum = None

    try:
        for workers in worker_counts:
            print(f"\nBenchmarking {workers} worker(s)...")
            elapsed, total = benchmark(shm.name, workers)

            if reference_sum is None:
                reference_sum = total

            results.append((workers, elapsed, total))
            print(f"Completed in {elapsed * 1000:.3f} ms")

    finally:
        shm.close()
        shm.unlink()

    baseline_time = results[0][1]

    print("\n=== BENCHMARK RESULTS ===")
    print(
        f"{'Cores':>8} | {'Wall Time (ms)':>15} | "
        f"{'Speedup':>10} | {'Amdahl Upper Bound':>19}"
    )
    print("-" * 65)

    for workers, elapsed, total in results:
        speedup = baseline_time / elapsed
        theoretical = amdahl_bound(workers)
        print(
            f"{workers:8d} | {elapsed * 1000:15.3f} | "
            f"{speedup:9.3f}x | {theoretical:18.3f}x"
        )

    print("\n=== VALIDATION ===")
    print(f"Reference Sum (1 worker): {reference_sum:.10f}")
    print("Note: Small floating-point differences may occur.")
    print("Timing includes process startup and task scheduling.")
    print("Status: Completed successfully")


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
