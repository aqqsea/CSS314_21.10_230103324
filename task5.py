import os
import platform
import statistics
import time
import multiprocessing
from concurrent.futures import ProcessPoolExecutor
from multiprocessing import shared_memory

STUDENT_ID = "230103324"

SIZES = [
    100,
    1_000,
    10_000,
    100_000,
    1_000_000,
    10_000_000,
]

A = 1.25
B = 0.75
REPEATS = 3

_X = None
_Y = None
_X_SHM = None
_Y_SHM = None


def init_worker(x_name, y_name):
    global _X, _Y, _X_SHM, _Y_SHM

    _X_SHM = shared_memory.SharedMemory(name=x_name)
    _Y_SHM = shared_memory.SharedMemory(name=y_name)

    _X = _X_SHM.buf.cast("d")
    _Y = _Y_SHM.buf.cast("d")


def process_chunk(bounds):
    start, end = bounds

    for i in range(start, end):
        _Y[i] = A * _X[i] + B

    return end - start


def serial_operation(x, y, n):
    for i in range(n):
        y[i] = A * x[i] + B


def make_chunks(n, workers):
    base, remainder = divmod(n, workers)
    chunks = []
    start = 0

    for worker_id in range(workers):
        length = base + (1 if worker_id < remainder else 0)
        chunks.append((start, start + length))
        start += length

    return chunks


def find_crossovers(results, parallel_time, title):
    print(f"\n{title}")

    crossings = []

    for previous, current in zip(results, results[1:]):
        previous_slower = (
            parallel_time(previous) >= previous["serial_ms"]
        )
        current_faster = (
            parallel_time(current) < current["serial_ms"]
        )

        if previous_slower and current_faster:
            crossings.append((previous, current))

    if crossings:
        for slow, fast in crossings:
            print(
                f"  Crossover range: N > {slow['n']:,} "
                f"and N <= {fast['n']:,}"
            )
            print(
                f"  At N={slow['n']:,}: parallel is "
                f"{parallel_time(slow) / slow['serial_ms']:.3f}x "
                "the serial time."
            )
            print(
                f"  At N={fast['n']:,}: parallel is "
                f"{parallel_time(fast) / fast['serial_ms']:.3f}x "
                "the serial time."
            )
    else:
        values = [
            parallel_time(row) < row["serial_ms"]
            for row in results
        ]

        if all(values):
            print(
                "  Parallel execution was faster at every tested size. "
                "No slower-to-faster crossover was observed."
            )
        elif not any(values):
            print(
                "  Parallel execution was slower at every tested size. "
                "No crossover was observed up to N=10,000,000."
            )
        else:
            print(
                "  No adjacent slower-to-faster transition was detected. "
                "Inspect the measurements below for non-monotonic results."
            )


def main():
    workers = os.cpu_count() or 1
    max_n = max(SIZES)
    buffer_size = max_n * 8

    print("=== TASK 5: The Overhead Crossover Point ===")
    print(f"Student ID: {STUDENT_ID}")
    print(f"Operating System: {platform.platform()}")
    print(f"CPU Architecture: {platform.machine()}")
    print(f"CPU Description: {platform.processor() or 'Not reported'}")
    print(f"Logical CPU count / workers: {workers}")
    print(f"Vector operation: y[i] = {A} * x[i] + {B}")
    print(f"Array sizes: {SIZES}")
    print(f"Benchmark repetitions: {REPEATS}")

    x_shm = shared_memory.SharedMemory(
        create=True, size=buffer_size
    )
    y_shm = shared_memory.SharedMemory(
        create=True, size=buffer_size
    )

    x = x_shm.buf.cast("d")
    y = y_shm.buf.cast("d")

    try:
        print("\nPreparing shared float64 arrays...")
        for i in range(max_n):
            x[i] = (i % 1000) / 1000.0

        context = multiprocessing.get_context("spawn")
        results = []

        print("\nStarting process pool...")

        with ProcessPoolExecutor(
            max_workers=workers,
            mp_context=context,
            initializer=init_worker,
            initargs=(x_shm.name, y_shm.name),
        ) as pool:

            # Initialize workers before measuring individual operations.
            empty_chunks = [(0, 0)] * workers
            startup_start = time.perf_counter()
            list(pool.map(process_chunk, empty_chunks, chunksize=1))
            startup_ms = (
                time.perf_counter() - startup_start
            ) * 1000

            print(f"Pool startup and warm-up: {startup_ms:.3f} ms")
            print(
                "The startup cost is reported separately; each measured "
                "parallel operation includes task scheduling and waiting."
            )

            for n in SIZES:
                serial_samples = []
                parallel_samples = []
                chunks = make_chunks(n, workers)

                for _ in range(REPEATS):
                    start = time.perf_counter()
                    serial_operation(x, y, n)
                    serial_samples.append(
                        (time.perf_counter() - start) * 1000
                    )

                    start = time.perf_counter()
                    list(pool.map(
                        process_chunk, chunks, chunksize=1
                    ))
                    parallel_samples.append(
                        (time.perf_counter() - start) * 1000
                    )

                serial_ms = statistics.median(serial_samples)
                parallel_ms = statistics.median(parallel_samples)

                results.append({
                    "n": n,
                    "serial_ms": serial_ms,
                    "parallel_ms": parallel_ms,
                })

                expected = A * x[n - 1] + B
                valid = abs(y[n - 1] - expected) < 1e-12

                print(
                    f"Measured N={n:,}: "
                    f"serial={serial_ms:.3f} ms, "
                    f"parallel={parallel_ms:.3f} ms, "
                    f"valid={valid}"
                )

        print("\n=== BENCHMARK TABLE ===")
        print(
            f"{'N':>12} | {'Serial (ms)':>12} | "
            f"{'Pool (ms)':>12} | {'Pool/Serial':>12} | {'Result':>10}"
        )
        print("-" * 71)

        for row in results:
            ratio = row["parallel_ms"] / row["serial_ms"]
            verdict = (
                "FASTER" if ratio < 1.0 else "SLOWER"
            )

            print(
                f"{row['n']:12,} | "
                f"{row['serial_ms']:12.3f} | "
                f"{row['parallel_ms']:12.3f} | "
                f"{ratio:11.3f}x | "
                f"{verdict:>10}"
            )

        find_crossovers(
            results,
            lambda row: row["parallel_ms"],
            "=== REUSED-POOL CROSSOVER ===",
        )

        find_crossovers(
            results,
            lambda row: row["parallel_ms"] + startup_ms,
            "=== ONE-SHOT CROSSOVER (INCLUDING POOL STARTUP) ===",
        )

        print("\nInterpretation:")
        print("Pool/Serial < 1 means parallel execution was faster.")
        print("Pool/Serial > 1 means serial execution was faster.")
        print(
            "A crossover is reported as a range between adjacent "
            "tested array sizes, not an unmeasured exact integer."
        )
        print("Status: Completed successfully")

    finally:
        del x, y
        x_shm.close()
        x_shm.unlink()
        y_shm.close()
        y_shm.unlink()


if __name__ == "__main__":
    multiprocessing.freeze_support()
    main()
