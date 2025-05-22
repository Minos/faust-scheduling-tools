#include <stdlib.h>

#include <perfmon/perf_event.h>
#include <perfmon/pfmlib.h>
#include <perfmon/pfmlib_perf_event.h>
#include <string.h>

#define NB_ITER 100000

static int perf_event_open_named(const char* str, int group_fd)
{
    int                    ret;
    struct perf_event_attr attr = {.size = sizeof(struct perf_event_attr)};
    pfm_perf_encode_arg_t  arg  = {.attr = &attr, .size = sizeof(pfm_perf_encode_arg_t)};

    ret = pfm_get_os_event_encoding(str, PFM_PLM3, PFM_OS_PERF_EVENT_EXT, &arg);
    if (ret != PFM_SUCCESS) {
        fprintf(stderr, "Error opening event %s: %s\n", str, pfm_strerror(ret));
        pfm_terminate();
        exit(ret);
    }

    attr.disabled       = 1;
    attr.exclude_kernel = 1;
    attr.exclude_hv     = 1;

    return syscall(SYS_perf_event_open, &attr, 0, -1, group_fd, 0);
}

void print_event_list()
{
    int ret;

    pfm_pmu_t             pmu;
    pfm_pmu_info_t        pmu_info   = {.size = sizeof(pfm_pmu_info_t)};
    pfm_event_info_t      event_info = {.size = sizeof(pfm_event_info_t)};
    pfm_event_attr_info_t attr_info  = {.size = sizeof(pfm_event_attr_info_t)};
    int                   has_attrs  = 0;

    pfm_for_all_pmus(pmu)
    {
        ret = pfm_get_pmu_info(pmu, &pmu_info);
        if (ret != PFM_SUCCESS || !pmu_info.is_present) {
            continue;
        }

        printf("+----------------------------------------------------------+\n");
        printf("| PMU name: %s (%s)\n", pmu_info.name, pmu_info.desc);
        printf("| Number of generic counters: %d\n", pmu_info.num_cntrs);
        printf("| Number of fixed counters: %d\n", pmu_info.num_fixed_cntrs);
        printf("+----------------------------------------------------------+\n");

        for (int idx = pmu_info.first_event; idx != -1; idx = pfm_get_event_next(idx)) {
            ret = pfm_get_event_info(idx, PFM_OS_PERF_EVENT_EXT, &event_info);
            if (ret != PFM_SUCCESS) {
                fprintf(stderr, "Could not get event info: %s\n", pfm_strerror(ret));
                continue;
            }

            printf("%s: %s", event_info.name, event_info.desc);

            if (event_info.equiv != NULL && !strcmp(event_info.equiv, event_info.name)) {
                printf(" (short for %s)\n", event_info.equiv);
                continue;
            } else {
                printf("\n");
            }

            has_attrs = 0;
            for (int attr = 0; attr < event_info.nattrs; attr++) {
                ret = pfm_get_event_attr_info(idx, attr, PFM_OS_PERF_EVENT_EXT, &attr_info);
                if (ret != PFM_SUCCESS) {
                    fprintf(stderr, "Could not get event attr info: %s\n", pfm_strerror(ret));
                    continue;
                }

                if (attr_info.type == PFM_ATTR_UMASK) {
                    has_attrs = 1;
                    printf("    %s.%s: %s\n", event_info.name, attr_info.name, attr_info.desc);
                }
            }

            if (has_attrs) {
                printf("\n");
            }
        }

        printf("\n");
    }
}

int main(int argc, char** argv)
{
    int ret = pfm_initialize();
    if (ret != PFM_SUCCESS) {
        fprintf(stderr, "Could not initialize PFM: %s\n", pfm_strerror(ret));
        return ret;
    }

    print_event_list();

    pfm_terminate();

    return 0;
}
