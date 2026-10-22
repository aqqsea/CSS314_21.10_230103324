import math
import os
import platform
import random
import threading
import time

STUDENT_ID = 230103324
THREADS = 4
TOTAL_POINTS = 40_000_000
POINTS_PER_THREAD = TOTAL_POINTS // THREADS

shared_rng = random.Random(STUDENT_ID * 10)
rng_lock = threading.Lock()


def shared_worker(results, thread_index):
    inside = 0

    for _ in range(POINTS_PER_THREAD):
        # Both coordinates use the same shared PRNG,
        # protected by one lock.
        with rng_lock:
            x = shared_rng.random()
            y = shared_rng.random()

        if x * x + y * y <= 1.0:
            inside += 1

    results[thread_index] = inside


def independent_worker(results, thread_index):
    seed = STUDENT_ID * 10 + thread_index
    rng = random.Random(seed)
    inside = 0

    for _ in range(POINTS_PER_THREAD):
        x = rng.random()
        y = rng.random()

        if x * x + y * y <= 1.0:
            inside += 1

    results[thread_index] = inside


def run_test(worker_function):
    results = [0] * THREADS
    threads = [
        threading.Thread(
            target=worker_function,
            args=(results, i)
        )
        for i in range(THREADS)
    ]

    start = time.perf_counter()

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    elapsed = time.perf_counter() - start
    pi_estimate = 4.0 * sum(results) / TOTAL_POINTS

    return pi_estimate, elapsed * 1000


def main():
    print("=== TASK 2: PRNG State Bottleneck ===")
    print(f"Student ID: {STUDENT_ID}")
    print(f"Operating System: {platform.platform()}")
    print(f"Logical CPU cores: {os.cpu_count()}")
    print(f"Threads: {THREADS}")
    print(f"Total sample points: {TOTAL_POINTS:,}")
    print(f"Points per thread: {POINTS_PER_THREAD:,}")

    print("\nRunning shared PRNG with lock...")
    shared_pi, shared_ms = run_test(shared_worker)

    print("Running independent PRNG states...")
    independent_pi, independent_ms = run_test(independent_worker)

    shared_error = abs(shared_pi - math.pi)
    independent_error = abs(independent_pi - math.pi)

    print("\n=== RESULTS ===")
    print("Shared PRNG:")
    print(f"  Computed pi: {shared_pi:.10f}")
    print(f"  Absolute error: {shared_error:.10f}")
    print(f"  Wall time: {shared_ms:.3f} ms")

    print("\nIndependent PRNG:")
    print(f"  Computed pi: {independent_pi:.10f}")
    print(f"  Absolute error: {independent_error:.10f}")
    print(f"  Wall time: {independent_ms:.3f} ms")

    print("\n=== PERFORMANCE COMPARISON ===")
    if independent_ms > 0:
        print(
            "Speedup factor (shared / independent): "
            f"{shared_ms / independent_ms:.3f}x"
        )

    print(
        "\nNote: CPython's GIL limits CPU-bound thread parallelism. "
        "This test compares shared-state locking with independent "
        "PRNG state, but does not guarantee multi-core speedup."
    )
    print("Status: Completed successfully")


if __name__ == "__main__":
    main()
