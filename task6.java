import java.util.concurrent.CountDownLatch;
import java.util.concurrent.atomic.AtomicInteger;

class task6 {
    static final int THREADS = 4;
    static final int INCREMENTS = 2_000_000;
    static final int EXPECTED = THREADS * INCREMENTS;

    // Volatile makes individual reads and writes visible,
    // but counter++ is still NOT an atomic operation.
    static volatile int sharedCounter = 0;

    static AtomicInteger atomicCounter = new AtomicInteger(0);

    static long runUnsynchronized(int increments)
            throws InterruptedException {

        sharedCounter = 0;

        CountDownLatch ready = new CountDownLatch(THREADS);
        CountDownLatch startGate = new CountDownLatch(1);
        Thread[] threads = new Thread[THREADS];

        for (int t = 0; t < THREADS; t++) {
            threads[t] = new Thread(() -> {
                try {
                    ready.countDown();
                    startGate.await();

                    for (int i = 0; i < increments; i++) {
                        sharedCounter++;
                    }
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            });
            threads[t].start();
        }

        ready.await();
        long start = System.nanoTime();
        startGate.countDown();

        for (Thread thread : threads) {
            thread.join();
        }

        return System.nanoTime() - start;
    }

    static long runAtomic(int increments)
            throws InterruptedException {

        atomicCounter.set(0);

        CountDownLatch ready = new CountDownLatch(THREADS);
        CountDownLatch startGate = new CountDownLatch(1);
        Thread[] threads = new Thread[THREADS];

        for (int t = 0; t < THREADS; t++) {
            threads[t] = new Thread(() -> {
                try {
                    ready.countDown();
                    startGate.await();

                    for (int i = 0; i < increments; i++) {
                        atomicCounter.incrementAndGet();
                    }
                } catch (InterruptedException e) {
                    Thread.currentThread().interrupt();
                }
            });
            threads[t].start();
        }

        ready.await();
        long start = System.nanoTime();
        startGate.countDown();

        for (Thread thread : threads) {
            thread.join();
        }

        return System.nanoTime() - start;
    }

    public static void main(String[] args) throws InterruptedException {
        System.out.println("=== TASK 6: Synchronization Cost & Data Loss ===");
        System.out.println("Student ID: 230103324");
        System.out.println("Threads: " + THREADS);
        System.out.println("Increments per thread: " + INCREMENTS);
        System.out.println("Expected final value: " + EXPECTED);

        // Warm up both implementations before measuring.
        runUnsynchronized(100_000);
        runAtomic(100_000);

        System.out.println("\nRunning without synchronization...");
        long unsafeTime = runUnsynchronized(INCREMENTS);
        int actual = sharedCounter;

        long lost = EXPECTED - actual;
        double lostPercent = lost * 100.0 / EXPECTED;

        System.out.println("\n=== UNSYNCHRONIZED RESULTS ===");
        System.out.println("Expected final value: " + EXPECTED);
        System.out.println("Actual final value: " + actual);
        System.out.println("Lost updates: " + lost);
        System.out.printf("Lost updates percentage: %.4f%%%n", lostPercent);
        System.out.printf("Wall time: %.3f ms%n", unsafeTime / 1_000_000.0);

        System.out.println("\nRunning with AtomicInteger...");
        long atomicTime = runAtomic(INCREMENTS);
        int correct = atomicCounter.get();

        System.out.println("\n=== ATOMIC RESULTS ===");
        System.out.println("Expected final value: " + EXPECTED);
        System.out.println("Actual final value: " + correct);
        System.out.printf("Wall time: %.3f ms%n", atomicTime / 1_000_000.0);
        System.out.println("Data correct: " + (correct == EXPECTED));

        double unsafeMs = unsafeTime / 1_000_000.0;
        double atomicMs = atomicTime / 1_000_000.0;
        double penaltyMs = atomicMs - unsafeMs;
        double penaltyPercent = penaltyMs * 100.0 / unsafeMs;

        System.out.println("\n=== SYNCHRONIZATION COST ===");
        System.out.printf("Time difference (atomic - unsynchronized): %.3f ms%n",
                penaltyMs);
        System.out.printf("Relative time penalty: %.2f%%%n", penaltyPercent);
        System.out.println(
                "Note: AtomicInteger uses atomic operations, not a mutex lock."
        );
        System.out.println("Status: Completed successfully");
    }
}
