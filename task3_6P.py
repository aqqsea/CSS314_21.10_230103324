
import random
import time
import math
import os
import sys
from concurrent.futures import ThreadPoolExecutor

STUDENT_ID = 230103324
SEED = STUDENT_ID
N = 2_000_000
WORKERS = 4


def serial_scan(data):
    """Serial inclusive prefix sum."""
    output = [0] * len(data)
    running_sum = 0

    for i, value in enumerate(data):
        running_sum += value
        output[i] = running_sum

    return output


def process_chunk(args):
    """Calculate a local inclusive prefix sum for one chunk."""
    data, start, end = args
    local_output = []
    running_sum = 0

    for i in range(start, end):
        running_sum += data[i]
        local_output.append(running_sum)

    return local_output, running_sum


def parallel_scan(data):
    """Parallel chunked scan: local sums, offsets, then apply offsets."""
    n = len(data)
    chunk_size = math.ceil(n / WORKERS)

    chunks = [
        (data, start, min(start + chunk_size, n))
        for start in range(0, n, chunk_size)
    ]

    # Pass 1: calculate each chunk's local prefix sums and total.
    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        results = list(executor.map(process_chunk, chunks))

    local_outputs = [result[0] for result in results]
    chunk_sums = [result[1] for result in results]

    # Offset reduction: calculate the total of all preceding chunks.
    offsets = []
    running_sum = 0

    for chunk_sum in chunk_sums:
        offsets.append(running_sum)
        running_sum += chunk_sum

    # Pass 2: apply each chunk's offset.
    def apply_offset(args):
        local_output, offset = args
        if offset:
            for i in range(len(local_output)):
                local_output[i] += offset
        return local_output

    with ThreadPoolExecutor(max_workers=WORKERS) as executor:
        adjusted_chunks = list(
            executor.map(apply_offset, zip(local_outputs, offsets))
        )

    output = []
    for chunk in adjusted_chunks:
        output.extend(chunk)

    return output


def main():
    print("=== TASK 3: Parallel Prefix Scan ===")
    print(f"Student ID: {STUDENT_ID}")
    print(f"Array size: {N:,}")
    print(f"Random seed: {SEED}")
    print(f"Workers: {WORKERS}")

    rng = random.Random(SEED)
    data = [rng.randint(1, 10) for _ in range(N)]

    start = time.perf_counter()
    serial_output = serial_scan(data)
    serial_ms = (time.perf_counter() - start) * 1000

    start = time.perf_counter()
    parallel_output = parallel_scan(data)
    parallel_ms = (time.perf_counter() - start) * 1000

    try:
        assert parallel_output[-1] == serial_output[-1], (
            f"Mismatch: parallel={parallel_output[-1]}, "
            f"serial={serial_output[-1]}"
        )
    except AssertionError as error:
        print("\nVerification Status: FAIL")
        print(error)
        sys.exit(1)

    speedup = serial_ms / parallel_ms if parallel_ms > 0 else 0

    print("\n=== RESULTS ===")
    print(f"Serial Time: {serial_ms:.3f} ms")
    print(f"Parallel Time: {parallel_ms:.3f} ms")
    print(f"Speedup: {speedup:.3f}x")
    print("Verification Status: PASS")
    print(f"Final prefix sum: {serial_output[-1]}")
    print("Status: Completed successfully")


if __name__ == "__main__":
    main()

