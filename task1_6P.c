#define _DARWIN_C_SOURCE

#include <stdio.h>
#include <stdlib.h>
#include <stdint.h>
#include <pthread.h>
#include <time.h>
#include <math.h>

#define N 8000
#define REPEATS 3
#define STUDENT_ID "230103324"
#define RNG_SEED UINT64_C(230103324)

typedef enum {
    ROW_MAJOR,
    COLUMN_MAJOR
} TraversalMode;

typedef struct {
    const double *matrix;
    size_t begin;
    size_t end;
    TraversalMode mode;
    double partial_sum;
} WorkerArgs;

static uint64_t rng_state = RNG_SEED;

static uint64_t next_random(void) {
    uint64_t x = rng_state;
    x ^= x >> 12;
    x ^= x << 25;
    x ^= x >> 27;
    rng_state = x;
    return x * UINT64_C(2685821657736338717);
}

static double next_float64(void) {
    return (double)(next_random() >> 11) *
           (1.0 / 9007199254740992.0);
}

static double wall_time(void) {
    struct timespec ts;
    clock_gettime(CLOCK_MONOTONIC, &ts);
    return (double)ts.tv_sec + (double)ts.tv_nsec / 1e9;
}

static int get_cpu_count(const char *key, int fallback) {
    char command[128];
    int count = 0;

    snprintf(command, sizeof(command), "sysctl -n %s", key);
    FILE *pipe = popen(command, "r");

    if (pipe != NULL) {
        if (fscanf(pipe, "%d", &count) != 1) {
            count = 0;
        }
        pclose(pipe);
    }

    return count > 0 ? count : fallback;
}

static void *sum_worker(void *arg) {
    WorkerArgs *w = (WorkerArgs *)arg;
    double sum = 0.0;

    if (w->mode == ROW_MAJOR) {
        /* Each worker receives a block of complete rows.
           Elements within a row are accessed sequentially. */
        for (size_t r = w->begin; r < w->end; r++) {
            const double *row = w->matrix + r * N;

            for (size_t c = 0; c < N; c++) {
                sum += row[c];
            }
        }
    } else {
        /* Each worker receives a block of columns.
           Walking down a column jumps N elements per access. */
        for (size_t c = w->begin; c < w->end; c++) {
            for (size_t r = 0; r < N; r++) {
                sum += w->matrix[r * N + c];
            }
        }
    }

    w->partial_sum = sum;
    return NULL;
}

static double run_test(
    const double *matrix,
    int workers,
    TraversalMode mode,
    double *total_sum
) {
    pthread_t *threads = malloc((size_t)workers * sizeof(*threads));
    WorkerArgs *args = calloc((size_t)workers, sizeof(*args));

    if (threads == NULL || args == NULL) {
        fprintf(stderr, "Error: unable to allocate thread structures.\n");
        free(threads);
        free(args);
        exit(EXIT_FAILURE);
    }

    double start = wall_time();

    for (int t = 0; t < workers; t++) {
        args[t].matrix = matrix;
        args[t].mode = mode;

        /* Divide rows in Mode A and columns in Mode B. */
        args[t].begin = N * (size_t)t / (size_t)workers;
        args[t].end = N * (size_t)(t + 1) / (size_t)workers;

        int rc = pthread_create(
            &threads[t], NULL, sum_worker, &args[t]
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

    double elapsed = wall_time() - start;

    *total_sum = 0.0;
    for (int t = 0; t < workers; t++) {
        *total_sum += args[t].partial_sum;
    }

    free(threads);
    free(args);

    return elapsed;
}

static double median3(double a, double b, double c) {
    if (a > b) {
        double tmp = a;
        a = b;
        b = tmp;
    }
    if (b > c) {
        double tmp = b;
        b = c;
        c = tmp;
    }
    if (a > b) {
        double tmp = a;
        a = b;
        b = tmp;
    }
    return b;
}

int main(void) {
    int logical_cores = get_cpu_count("hw.logicalcpu", 1);
    int physical_cores = get_cpu_count("hw.physicalcpu", logical_cores);

    size_t elements = (size_t)N * N;
    size_t bytes = elements * sizeof(double);

    double *matrix = malloc(bytes);

    if (matrix == NULL) {
        fprintf(stderr,
            "Error: could not allocate the 8000 x 8000 matrix "
            "(%.1f MiB required).\n",
            (double)bytes / (1024.0 * 1024.0));
        return EXIT_FAILURE;
    }

    printf("=== TASK 1: Row-Major vs. Column-Major Cache Traversal ===\n");
    printf("Student ID: %s\n", STUDENT_ID);
    printf("Matrix dimensions: %d x %d\n", N, N);
    printf("Element type: float64 (double, 8 bytes)\n");
    printf("Random seed: %s\n", STUDENT_ID);
    printf("Logical CPU cores: %d\n", logical_cores);
    printf("Physical CPU cores / workers: %d\n", physical_cores);
    printf("Matrix size: %.1f MiB\n",
           (double)bytes / (1024.0 * 1024.0));
    printf("Timing repetitions per mode: %d\n", REPEATS);

    printf("\nInitializing matrix...\n");

    for (size_t i = 0; i < elements; i++) {
        matrix[i] = next_float64();
    }

    printf("Matrix initialized successfully.\n");
    printf("Timing excludes allocation and initialization.\n");
    printf("Each timed pass includes thread creation and joining.\n");

    double row_times[REPEATS];
    double column_times[REPEATS];
    double row_sum = 0.0;
    double column_sum = 0.0;

    for (int r = 0; r < REPEATS; r++) {
        printf("\nBenchmark round %d/%d\n", r + 1, REPEATS);

        row_times[r] = run_test(
            matrix, physical_cores, ROW_MAJOR, &row_sum
        );

        printf("  Mode A (Row-Major): %.3f ms\n",
               row_times[r] * 1000.0);

        column_times[r] = run_test(
            matrix, physical_cores, COLUMN_MAJOR, &column_sum
        );

        printf("  Mode B (Column-Major): %.3f ms\n",
               column_times[r] * 1000.0);
    }

    double row_ms = median3(
        row_times[0], row_times[1], row_times[2]
    ) * 1000.0;

    double column_ms = median3(
        column_times[0], column_times[1], column_times[2]
    ) * 1000.0;

    printf("\n=== FINAL RESULTS (median of %d runs) ===\n", REPEATS);
    printf("Student ID: %s\n", STUDENT_ID);
    printf("Logical CPU cores: %d\n", logical_cores);
    printf("Workers used: %d physical cores\n", physical_cores);
    printf("Mode A - Row-Major runtime: %.3f ms\n", row_ms);
    printf("Mode B - Column-Major runtime: %.3f ms\n", column_ms);

    if (row_ms > 0.0) {
        printf("Cache penalty factor (B / A): %.3fx\n",
               column_ms / row_ms);
    }

    printf("Row-Major sum: %.12f\n", row_sum);
    printf("Column-Major sum: %.12f\n", column_sum);
    printf("Absolute sum difference: %.12f\n",
           fabs(row_sum - column_sum));
    printf("Note: floating-point sums may differ slightly "
           "because addition order changes.\n");
    printf("Status: Completed successfully\n");

    free(matrix);
    return EXIT_SUCCESS;
}
