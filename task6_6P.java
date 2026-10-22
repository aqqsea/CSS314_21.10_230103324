
import java.util.Locale;
import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicInteger;
import java.util.concurrent.locks.ReentrantLock;

public class task6_6P {
    static final int THREADS = 8;
    static final int INCREMENTS_PER_THREAD = 1_000_000;
    static final int TOTAL_OPERATIONS = THREADS * INCREMENTS_PER_THREAD;
    static final int WARMUP_ITERATIONS = 100_000;

    static class Result {
        final double timeMs;
        final double throughput;
        final int finalCounter;

        Result(double timeMs, double throughput, int finalCounter) {
            this.timeMs = timeMs;
            this.throughput = throughput;
            this.finalCounter = finalCounter;
        }
    }

    static Result benchmarkMutex(int iterations) throws InterruptedException {
        int[] counter = {0};
        ReentrantLock mutex = new ReentrantLock();

        CountDownLatch ready = new CountDownLatch(THREADS);
        CountDownLatch start = new CountDownLatch(1);
        Thread[] threads = new Thread[THREADS];

        for (int t = 0; t < THREADS; t++) {
            threads[t] = new Thread(() -> {
                ready.countDown();

                try {
                    start.await();
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    return;
                }

                for (int i = 0; i < iterations; i++) {
                    mutex.lock();
                    try {
                        counter[0]++;
                    } finally {
                        mutex.unlock();
                    }
                }
            });
            threads[t].start();
        }

        ready.await();
        long begin = System.nanoTime();
        start.countDown();

        for (Thread thread : threads) {
            thread.join();
        }

        long elapsed = System.nanoTime() - begin;
        double timeMs = elapsed / 1_000_000.0;
        double throughput = iterations * (double) THREADS
                / (elapsed / 1_000_000_000.0);

        if (counter[0] != iterations * THREADS) {
            throw new IllegalStateException("Mutex counter verification failed");
        }

        return new Result(timeMs, throughput, counter[0]);
    }

    static Result benchmarkCAS(int iterations) throws InterruptedException {
        AtomicInteger counter = new AtomicInteger(0);

        CountDownLatch ready = new CountDownLatch(THREADS);
        CountDownLatch start = new CountDownLatch(1);
        Thread[] threads = new Thread[THREADS];

        for (int t = 0; t < THREADS; t++) {
            threads[t] = new Thread(() -> {
                ready.countDown();

                try {
                    start.await();
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                    return;
                }

                for (int i = 0; i < iterations; i++) {
                    int current;
                    do {
                        current = counter.get();
                    } while (!counter.compareAndSet(current, current + 1));
                }
            });
            threads[t] = threads[t];
            threads[t].start();
        }

        ready.await();
        long begin = System.nanoTime();
        start.countDown();

        for (Thread thread : threads) {
            thread.join();
        }

        long elapsed = System.nanoTime() - begin;
        double timeMs = elapsed / 1_000_000.0;
        double throughput = iterations * (double) THREADS
                / (elapsed / 1_000_000_000.0);

        if (counter.get() != iterations * THREADS) {
            throw new IllegalStateException("CAS counter verification failed");
        }

        return new Result(timeMs, throughput, counter.get());
    }

    public static void main(String[] args) throws InterruptedException {
        System.out.println("=== TASK 6: Atomic CAS vs. OS Mutex ===");
        System.out.println("Threads: " + THREADS);
        System.out.println("Increments per thread: "
                + String.format(Locale.US, "%,d", INCREMENTS_PER_THREAD));
        System.out.println("Total operations per test: "
                + String.format(Locale.US, "%,d", TOTAL_OPERATIONS));

        // Small unmeasured warm-up to reduce first-run JVM effects.
        benchmarkMutex(WARMUP_ITERATIONS);
        benchmarkCAS(WARMUP_ITERATIONS);

        System.out.println("\nRunning mutex benchmark...");
        Result mutex = benchmarkMutex(INCREMENTS_PER_THREAD);

        System.out.println("Running CAS benchmark...");
        Result cas = benchmarkCAS(INCREMENTS_PER_THREAD);

        double ratio = cas.throughput / mutex.throughput;

        System.out.println("\n=== RESULTS ===");
        System.out.printf(Locale.US,
                "Mutex Execution Time: %.3f ms%n", mutex.timeMs);
        System.out.printf(Locale.US,
                "Mutex Throughput: %.0f ops/sec%n", mutex.throughput);

        System.out.printf(Locale.US,
                "Atomic CAS Execution Time: %.3f ms%n", cas.timeMs);
        System.out.printf(Locale.US,
                "Atomic CAS Throughput: %.0f ops/sec%n", cas.throughput);

        System.out.printf(Locale.US,
                "Throughput Ratio (CAS / Mutex): %.3fx%n", ratio);

        System.out.println("Verification: PASS");
        System.out.println("Mutex final counter: " + mutex.finalCounter);
        System.out.println("CAS final counter: " + cas.finalCounter);
        System.out.println("Status: Completed successfully");
    }
}

