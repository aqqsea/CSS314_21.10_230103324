import os
import platform
import threading
import time
from queue import Queue, Empty

STUDENT_ID = "230103324"
ITEM_COUNT = 1000
WORKERS = 4
DELAY = 0.0001


def process_item(i):
    """Simulate an irregular workload."""
    time.sleep(DELAY * (i % 20))


def summarize(name, start_time, finish_times, counts, wall_time):
    completion_offsets = [
        (timestamp - start_time) * 1000
        for timestamp in finish_times.values()
    ]

    first_finish = min(completion_offsets)
    last_finish = max(completion_offsets)
    completion_delta = last_finish - first_finish

    return {
        "name": name,
        "wall_ms": wall_time * 1000,
        "first_ms": first_finish,
        "last_ms": last_finish,
        "delta_ms": completion_delta,
        "items": sum(counts.values()),
        "counts": counts,
    }


def run_static():
    finish_times = {}
    counts = {}
    barrier = threading.Barrier(WORKERS)

    def worker(worker_id, start_index, end_index):
        barrier.wait()

        for i in range(start_index, end_index):
            process_item(i)

        finish_times[worker_id] = time.perf_counter()
        counts[worker_id] = end_index - start_index

    threads = []

    for worker_id in range(WORKERS):
        start_index = worker_id * (ITEM_COUNT // WORKERS)
        end_index = (worker_id + 1) * (ITEM_COUNT // WORKERS)

        threads.append(threading.Thread(
            target=worker,
            args=(worker_id, start_index, end_index)
        ))

    start_time = time.perf_counter()

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    wall_time = time.perf_counter() - start_time

    return summarize(
        "Static (250 items/worker)",
        start_time, finish_times, counts, wall_time
    )


def run_dynamic(chunk_size):
    work_queue = Queue()

    for start_index in range(0, ITEM_COUNT, chunk_size):
        end_index = min(start_index + chunk_size, ITEM_COUNT)
        work_queue.put(list(range(start_index, end_index)))

    finish_times = {}
    counts = {}
    barrier = threading.Barrier(WORKERS)

    def worker(worker_id):
        processed = 0
        barrier.wait()

        while True:
            try:
                chunk = work_queue.get_nowait()
            except Empty:
                break

            try:
                for i in chunk:
                    process_item(i)
                    processed += 1
            finally:
                work_queue.task_done()

        finish_times[worker_id] = time.perf_counter()
        counts[worker_id] = processed

    threads = [
        threading.Thread(target=worker, args=(worker_id,))
        for worker_id in range(WORKERS)
    ]

    start_time = time.perf_counter()

    for thread in threads:
        thread.start()

    for thread in threads:
        thread.join()

    wall_time = time.perf_counter() - start_time

    return summarize(
        f"Dynamic (chunk={chunk_size})",
        start_time, finish_times, counts, wall_time
    )


def print_result(result):
    print(f"\nStrategy: {result['name']}")
    print(f"Items processed: {result['items']}/{ITEM_COUNT}")
    print(f"Total wall time: {result['wall_ms']:.3f} ms")
    print(f"First thread finished: {result['first_ms']:.3f} ms")
    print(f"Last thread finished:  {result['last_ms']:.3f} ms")
    print(f"Thread completion delta: {result['delta_ms']:.3f} ms")
    print(f"Items per worker: {result['counts']}")


def main():
    print("=== TASK 4: Work Stealing & Scheduling Under Skew ===")
    print(f"Student ID: {STUDENT_ID}")
    print(f"Operating System: {platform.platform()}")
    print(f"Logical CPU count: {os.cpu_count()}")
    print(f"Items: {ITEM_COUNT}")
    print(f"Workers: {WORKERS}")
    print(f"Simulated workload: sleep({DELAY} * (i % 20))")

    results = [
        run_static(),
        run_dynamic(chunk_size=1),
        run_dynamic(chunk_size=5),
    ]

    print("\n=== BENCHMARK RESULTS ===")
    print(
        f"{'Strategy':<30} {'Wall Time (ms)':>15} "
        f"{'Completion Delta (ms)':>22}"
    )
    print("-" * 70)

    for result in results:
        print(
            f"{result['name']:<30} "
            f"{result['wall_ms']:>15.3f} "
            f"{result['delta_ms']:>22.3f}"
        )

    if all(result["items"] == ITEM_COUNT for result in results):
        print("\nValidation: All 1000 items processed in each strategy.")
    else:
        print("\nValidation: ERROR - item count mismatch.")

    print("Note: Timings vary by system load and Python scheduling.")
    print("Dynamic scheduling uses a shared queue.")
    print("Status: Completed successfully")


if __name__ == "__main__":
    main()
