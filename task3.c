#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <pthread.h>
#include <time.h>
#include <unistd.h>
#include <sys/types.h>
#include <sys/sysctl.h>

#define ITERATIONS 50000000ULL
#define CACHE_LINE 64

typedef struct {
    int index;
    int mode;
    volatile uint64_t *shared_counts;
} ThreadArgs;

static double now_seconds(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return ts.tv_sec + ts.tv_nsec / 1e9;
}

static void *worker(void *arg) {
    ThreadArgs *a = (ThreadArgs *)arg;

    if (a->mode == 0) {
        // Unpadded: neighboring counters may share cache lines.
        for (uint64_t i = 0; i < ITERATIONS; i++) {
            a->shared_counts[a->index]++;
        }
    } else {
        // Local counter: write to shared memory only once at the end.
        volatile uint64_t local_count = 0;

        for (uint64_t i = 0; i < ITERATIONS; i++) {
            local_count++;
        }

        a->shared_counts[a->index] = local_count;
    }

    return NULL;
}

static int get_physical_cores(void) {
    int cores = 0;
    size_t size = sizeof(cores);

    if (sysctlbyname("hw.physicalcpu", &cores, &size, NULL, 0) == 0
        && cores > 0) {
        return cores;
    }

    long fallback = sysconf(_SC_NPROCESSORS_ONLN);
    return fallback > 0 ? (int)fallback : 1;
}

static double run_test(int n, int mode) {
    pthread_t *threads = malloc((size_t)n * sizeof(pthread_t));
    ThreadArgs *args = malloc((size_t)n * sizeof(ThreadArgs));
    volatile uint64_t *counts = NULL;

    if (!threads || !args ||
        posix_memalign((void **)&counts, CACHE_LINE,
                       (size_t)n * sizeof(uint64_t)) != 0) {
        fprintf(stderr, "Memory allocation failed.\n");
        free(threads);
        free(args);
        free((void *)counts);
        exit(EXIT_FAILURE);
    }

    for (int i = 0; i < n; i++) {
        counts[i] = 0;
        args[i].index = i;
        args[i].mode = mode;
        args[i].shared_counts = counts;
    }

    double start = now_seconds();

    for (int i = 0; i < n; i++) {
        if (pthread_create(&threads[i], NULL, worker, &args[i]) != 0) {
            fprintf(stderr, "Failed to create thread.\n");
            exit(EXIT_FAILURE);
        }
    }

    uint64_t checksum = 0;

    for (int i = 0; i < n; i++) {
        pthread_join(threads[i], NULL);
        checksum += counts[i];
    }

    double elapsed = now_seconds() - start;

    printf("  Checksum: %llu\n", (unsigned long long)checksum);

    free((void *)counts);
    free(args);
    free(threads);

    return elapsed;
}

int main(void) {
    int physical_cores = get_physical_cores();

    printf("=== TASK 3: Cache Line Contention (False Sharing) ===\n");
    printf("Operating System: macOS / Unix-compatible system\n");
    printf("Physical CPU Cores: %d\n", physical_cores);
    printf("Threads: %d\n", physical_cores);
    printf("Increments per thread: %llu\n",
           (unsigned long long)ITERATIONS);
    printf("Total increments per test: %llu\n",
           (unsigned long long)ITERATIONS * physical_cores);

    printf("\nRunning unpadded shared counters...\n");
    double unpadded_time = run_test(physical_cores, 0);

    printf("\nRunning local counters...\n");
    double local_time = run_test(physical_cores, 1);

    printf("\n=== RESULTS ===\n");
    printf("%-25s %12s\n", "Method", "Wall Time (s)");
    printf("----------------------------------------\n");
    printf("%-25s %12.6f\n", "Unpadded Shared", unpadded_time);
    printf("%-25s %12.6f\n", "Local Counter", local_time);

    printf("\nExecution Ratio (Unpadded / Local): %.3fx\n",
           local_time > 0 ? unpadded_time / local_time : 0.0);

    printf("\nNote: The ratio is measured on this machine and may vary.\n");
    printf("The local-counter test minimizes shared writes.\n");
    printf("Status: Completed successfully\n");

    return 0;
}
