import multiprocessing as mp
from multiprocessing import shared_memory
from array import array
import time
import os
import sys

SIZES = [100_000, 1_000_000, 10_000_000]


def ipc_receiver(queue, result_queue):
    data = queue.get()
    result_queue.put((len(data), data[0], data[-1]))


def shared_memory_receiver(queue, result_queue):
    name, size = queue.get()
    shm = shared_memory.SharedMemory(name=name)
    try:
        buffer = shm.buf
        view = buffer.cast("d")
        try:
            result = (size, view[0], view[size - 1])
        finally:
            view.release()
            buffer.release()
        result_queue.put(result)
    finally:
        shm.close()


def benchmark_ipc(source):
    ctx = mp.get_context("spawn")
    queue = ctx.Queue()
    result_queue = ctx.Queue()
    process = ctx.Process(
        target=ipc_receiver, args=(queue, result_queue)
    )
    process.start()

    try:
        start = time.perf_counter()
        queue.put(source)
        received = result_queue.get()
        elapsed = (time.perf_counter() - start) * 1000
        process.join()

        if process.exitcode != 0 or received[0] != len(source):
            raise RuntimeError("IPC transfer verification failed")

        return elapsed
    finally:
        if process.is_alive():
            process.terminate()
        process.join()
        queue.close()
        result_queue.close()


def benchmark_shared_memory(source):
    ctx = mp.get_context("spawn")
    queue = ctx.Queue()
    result_queue = ctx.Queue()
    shm = None
    process = ctx.Process(
        target=shared_memory_receiver, args=(queue, result_queue)
    )
    process.start()

    try:
        start = time.perf_counter()
        shm = shared_memory.SharedMemory(
            create=True, size=len(source) * source.itemsize
        )

        buffer = shm.buf
        destination = buffer.cast("d")
        try:
            destination[:] = source
        finally:
            destination.release()
            buffer.release()

        queue.put((shm.name, len(source)))
        received = result_queue.get()
        elapsed = (time.perf_counter() - start) * 1000
        process.join()

        if process.exitcode != 0 or received[0] != len(source):
            raise RuntimeError("Shared-memory verification failed")

        return elapsed
    finally:
        if process.is_alive():
            process.terminate()
        process.join()

        if shm is not None:
            shm.close()
            shm.unlink()

        queue.close()
        result_queue.close()


def main():
    print("=== TASK 4: Memory Transfer Profile ===")
    print("Student ID: 230103324")
    print(f"CPU cores: {os.cpu_count()}")
    print("Path A: Multiprocessing Queue (Pickle)")
    print("Path B: Shared Memory (allocation + copy + attach)")
    print("\nArray Size | IPC Queue (ms) | Shared Memory (ms)")

    for n in SIZES:
        print(f"\nPreparing array with {n:,} elements...", flush=True)
        source = array("d", [1.0]) * n
        ipc_ms = benchmark_ipc(source)
        shm_ms = benchmark_shared_memory(source)

        print(
            f"{n:>10,} | {ipc_ms:>14.3f} | {shm_ms:>18.3f}",
            flush=True,
        )
        del source

    print("\nStatus: Completed successfully")


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"ERROR: {error}", file=sys.stderr)
        sys.exit(1)
