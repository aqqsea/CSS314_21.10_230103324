import os
import platform
import random
import statistics
import time
import sys

STUDENT_ID = "230103324"
ARRAY_SIZE = 20_000_000


def main():
    print("=== TASK 1: Hardware Probe & Serial Baseline ===")
    print(f"Student ID: {STUDENT_ID}")
    print(f"Operating System: {platform.platform()}")
    print(f"CPU: {platform.processor() or platform.machine()}")
    print(f"Logical CPU Cores: {os.cpu_count()}")
    print(f"Python Version: {sys.version.split()[0]}")
    print(f"Array Size: {ARRAY_SIZE:,}")
    print("Data Type: float64")

    rng = random.Random(STUDENT_ID)
    print("\nGenerating array...")
    data = [rng.random() for _ in range(ARRAY_SIZE)]

    print("\nStarting serial calculations...")
    start = time.perf_counter()

    total_sum = sum(data)
    mean = total_sum / ARRAY_SIZE
    variance = sum((x - mean) ** 2 for x in data) / ARRAY_SIZE
    std_dev = variance ** 0.5

    elapsed_ms = (time.perf_counter() - start) * 1000

    print("\n=== RESULTS ===")
    print(f"Mathematical Sum: {total_sum:.10f}")
    print(f"Mean: {mean:.10f}")
    print(f"Standard Deviation: {std_dev:.10f}")
    print(f"Serial Execution Time: {elapsed_ms:.3f} ms")
    print("Execution Mode: Serial (single thread)")
    print("Status: Completed successfully")


if __name__ == "__main__":
    main()
