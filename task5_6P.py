
import hashlib
import os
import time
from concurrent.futures import ThreadPoolExecutor

TOTAL_TASKS = 10_000
HASHES_PER_TASK = 500
PAYLOAD = b"A" * 1024
CORES = os.cpu_count() or 1

POOL_SIZES = sorted(set([
    1,
    max(1, CORES // 2),
    CORES,
    CORES * 2,
    CORES * 4,
    CORES * 16,
    256,
]))


def cpu_task(task_id):
    """Hash a 1 KB payload 500 times."""
    digest = PAYLOAD
    for _ in range(HASHES_PER_TASK):
        digest = hashlib.sha256(PAYLOAD + digest[:0]).digest()
    return digest[0]


def run_benchmark(pool_size):
    start = time.perf_counter()

    with ThreadPoolExecutor(max_workers=pool_size) as executor:
        results = list(executor.map(cpu_task, range(TOTAL_TASKS)))

    elapsed_ms = (time.perf_counter() - start) * 1000
    # Consume results so every task's result is collected.
    checksum = sum(results)
    return elapsed_ms, checksum


def main():
    print("=== TASK 5: Thread Oversubscription Threshold ===")
    print(f"Logical CPU cores: {CORES}")
    print(f"CPU-bound tasks: {TOTAL_TASKS:,}")
    print(f"Hashes per task: {HASHES_PER_TASK}")
    print(f"Pool sizes: {POOL_SIZES}")
    print("\nBenchmark running; larger pools may take longer...", flush=True)

    measurements = []
    checksum_reference = None

    for pool_size in POOL_SIZES:
        elapsed_ms, checksum = run_benchmark(pool_size)

        if checksum_reference is None:
            checksum_reference = checksum
        elif checksum != checksum_reference:
            raise RuntimeError("Benchmark results did not match")

        measurements.append((pool_size, elapsed_ms))
        print(
            f"Completed pool size {pool_size}: {elapsed_ms:.2f} ms",
            flush=True,
        )

    baseline = measurements[0][1]
    first_worsening = None

    print("\n=== RESULTS ===")
    print(
        f"{'Pool Size':>10} | {'Execution Time (ms)':>19} | "
        f"{'Speedup vs 1 thread':>19} | Status"
    )
    print("-" * 77)

    previous_time = None

    for pool_size, elapsed_ms in measurements:
        speedup = baseline / elapsed_ms if elapsed_ms else 0

        if previous_time is not None and elapsed_ms > previous_time:
            if first_worsening is None:
                first_worsening = pool_size
                status = "FIRST WORSENING"
            else:
                status = "SLOWER"
        else:
            status = "OK"

        print(
            f"{pool_size:>10} | {elapsed_ms:>19.2f} | "
            f"{speedup:>19.3f}x | {status}"
        )
        previous_time = elapsed_ms

    print("\n=== SATURATION DIAGNOSIS ===")
    if first_worsening is None:
        print("No worsening between consecutive tested pool sizes.")
    else:
        print(
            f"First measured worsening: pool size {first_worsening} "
            "(slower than the preceding tested pool size)."
        )

    print(
        "Note: This identifies an observed performance regression, "
        "not proof of context switching as the sole cause. "
        "Python's GIL and thread-pool overhead can also affect results."
    )
    print(f"Verification checksum: {checksum_reference}")
    print("Status: Completed successfully")


if __name__ == "__main__":
    main()

