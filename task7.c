#define _DARWIN_C_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <pthread.h>
#include <time.h>
#include <math.h>
#include <unistd.h>

#ifdef __APPLE__
#include <sys/types.h>
#include <sys/sysctl.h>
#endif

#define N 30000000ULL
#define REPEATS 3

enum { MEMORY_COPY = 0, COMPUTE = 1 };

typedef struct {
    const double *a;
    double *b;
    size_t start;
    size_t end;
    int kernel;
} WorkerArgs;

static double wall_seconds(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1e9;
}

static int get_cpu_count(const char *name) {
#ifdef __APPLE__
    int count = 0;
    size_t size = sizeof(count);

    if (sysctlbyname(name, &count, &size, NULL, 0) == 0 &&
        count > 0) {
        return count;
    }
#else
    (void)name;
#endif
    long fallback = sysconf(_SC_NPROCESSORS_ONLN);
    return fallback > 0 ? (int)fallback : 1;
}

static void *run_worker(void *arg) {
    WorkerArgs *w = (WorkerArgs *)arg;

    if (w->kernel == MEMORY_COPY) {
        for (size_t i = w->start; i < w->end; i++) {
            w->b[i] = w->a[i];
        }
    } else {
        for (size_t i = w->start; i < w->end; i++) {
            double x = w->a[i];
            w->b[i] = sin(x) * cos(x) + tan(x);
        }
    }

    return NULL;
}

static double run_once(
    const double *a, double *b, int workers, int kernel
) {
    pthread_t *threads = malloc((size_t)workers * sizeof(*threads));
    WorkerArgs *args = malloc((size_t)workers * sizeof(*args));

    if (threads == NULL || args == NULL) {
        fprintf(stderr, "Error: could not allocate thread structures.\n");
        free(threads);
        free(args);
        exit(EXIT_FAILURE);
    }

    double start_time = wall_seconds();

    for (int t = 0; t < workers; t++) {
        args[t].a = a;
        args[t].b = b;
        args[t].start = N * (size_t)t / (size_t)workers;
        args[t].end = N * (size_t)(t + 1) / (size_t)workers;
        args[t].kernel = kernel;

        int rc = pthread_create(
            &threads[t], NULL, run_worker, &args[t]
        );

        if (rc != 0) {
            fprintf(stderr, "Error: pthread_create failed (%d).\n", rc);
            exit(EXIT_FAILURE);
        }
    }

    for (int t = 0; t < workers; t++) {
        int rc = pthread_join(threads[t], NULL);
        if (rc != 0) {
            fprintf(stderr, "Error: pthread_join failed (%d).\n", rc);
            exit(EXIT_FAILURE);
        }
    }

    double elapsed = wall_seconds() - start_time;

    free(threads);
    free(args);

    return elapsed;
}

static double median3(double a, double b, double c) {
    if (a > b) {
        double temp = a;
        a = b;
        b = temp;
    }
    if (b > c) {
        double temp = b;
        b = c;
        c = temp;
    }
    if (a > b) {
        double temp = a;
        a = b;
        b = temp;
    }
    return b;
}

static double benchmark(
    const double *a, double *b, int workers, int kernel
) {
    double samples[REPEATS];

    for (int r = 0; r < REPEATS; r++) {
        samples[r] = run_once(a, b, workers, kernel);
    }

    return median3(samples[0], samples[1], samples[2]);
}

static void print_table(
    const char *name,
    const double times[3],
    const int worker_counts[3]
) {
    printf("\n=== %s ===\n", name);
    printf("%8s | %15s | %10s | %12s\n",
           "Cores", "Wall Time (ms)", "Speedup", "Efficiency");
    printf("----------------------------------------------------\n");

    for (int i = 0; i < 3; i++) {
        double speedup = times[0] / times[i];
        double efficiency = speedup / worker_counts[i];

        printf("%8d | %15.3f | %9.3fx | %11.3f\n",
               worker_counts[i],
               times[i] * 1000.0,
               speedup,
               efficiency);
    }
}

int main(void) {
    int physical_cores = get_cpu_count("hw.physicalcpu");
    int logical_cores = get_cpu_count("hw.logicalcpu");

    int worker_counts[3] = {1, 2, physical_cores};

    size_t bytes = (size_t)N * sizeof(double);
    double *a = NULL;
    double *b = NULL;

    if (posix_memalign((void **)&a, 64, bytes) != 0 ||
        posix_memalign((void **)&b, 64, bytes) != 0) {
        fprintf(stderr,
                "Error: allocation failed. This test needs about "
                "480 MB for two float64 arrays.\n");
        free(a);
        free(b);
        return EXIT_FAILURE;
    }

    printf("=== TASK 7: Arithmetic Intensity vs. Memory Bottlenecks ===\n");
    printf("Student ID: 230103324\n");
    printf("Operating System: macOS / Unix-compatible system\n");
    printf("Physical CPU cores: %d\n", physical_cores);
    printf("Logical CPU cores: %d\n", logical_cores);
    printf("Array elements: %llu\n", (unsigned long long)N);
    printf("Bytes per array: %.1f MiB\n",
           (double)bytes / (1024.0 * 1024.0));
    printf("Worker counts: 1, 2, %d physical cores\n", physical_cores);
    printf("Repeats per configuration: %d (median reported)\n", REPEATS);
    printf("Timing includes thread creation and joining.\n");

    printf("\nInitializing arrays...\n");
    for (size_t i = 0; i < N; i++) {
        /* Keep values moderate so tan(x) stays away from its poles. */
        a[i] = 0.1 + (double)(i % 1000) * 0.0008;
        b[i] = 0.0;
    }

    double memory_times[3];
    double compute_times[3];
    volatile double checksum = 0.0;

    printf("\nRunning Kernel A: Memory-Bound vector copy...\n");
    for (int i = 0; i < 3; i++) {
        printf("  Kernel A with %d worker(s)...\n", worker_counts[i]);
        memory_times[i] = benchmark(
            a, b, worker_counts[i], MEMORY_COPY
        );
        checksum += b[0] + b[N / 2] + b[N - 1];
    }

    printf("\nRunning Kernel B: Compute-Bound trigonometric operation...\n");
    for (int i = 0; i < 3; i++) {
        printf("  Kernel B with %d worker(s)...\n", worker_counts[i]);
        compute_times[i] = benchmark(
            a, b, worker_counts[i], COMPUTE
        );
        checksum += b[0] + b[N / 2] + b[N - 1];
    }

    print_table("KERNEL A: MEMORY COPY", memory_times, worker_counts);
    print_table("KERNEL B: SIN * COS + TAN", compute_times, worker_counts);

    printf("\n=== SCALING DIAGNOSIS ===\n");
    printf("Kernel A max-core speedup: %.3fx\n",
           memory_times[0] / memory_times[2]);
    printf("Kernel B max-core speedup: %.3fx\n",
           compute_times[0] / compute_times[2]);

    if (physical_cores > 2) {
        double memory_gain_2_to_max =
            memory_times[1] / memory_times[2];
        double compute_gain_2_to_max =
            compute_times[1] / compute_times[2];

        double memory_eff_max =
            (memory_times[0] / memory_times[2]) / physical_cores;
        double compute_eff_max =
            (compute_times[0] / compute_times[2]) / physical_cores;

        printf("Kernel A speedup from 2 to max cores: %.3fx\n",
               memory_gain_2_to_max);
        printf("Kernel B speedup from 2 to max cores: %.3fx\n",
               compute_gain_2_to_max);
        printf("Kernel A max-core efficiency: %.3f\n", memory_eff_max);
        printf("Kernel B max-core efficiency: %.3f\n", compute_eff_max);

        if ((memory_eff_max < compute_eff_max * 0.85) ||
            (memory_gain_2_to_max < 1.25 &&
             compute_gain_2_to_max >= 1.25)) {
            printf("Conclusion: Kernel A (Memory-Bound) stalled in "
                   "scaling relative to Kernel B. This is consistent "
                   "with memory-channel/bandwidth saturation.\n");
        } else {
            printf("Conclusion: Kernel A (Memory-Bound) is the "
                   "memory-bandwidth candidate, but this run did not "
                   "show a clear saturation plateau relative to "
                   "Kernel B. Wall-time results alone cannot prove "
                   "memory-channel saturation.\n");
        }
    } else {
        printf("Conclusion: More than 2 physical cores are needed "
               "for the 2-to-max scaling diagnosis.\n");
    }

    printf("Output checksum: %.10f\n", (double)checksum);
    printf("Status: Completed successfully\n");

    free(a);
    free(b);

    return 0;
}
