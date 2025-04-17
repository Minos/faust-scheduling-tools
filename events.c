#include <perfmon/pfmlib.h>
#include <perfmon/pfmlib_perf_event.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>

void check_pfm_result(int code, const char* desc)
{
    if (code != PFM_SUCCESS) {
        printf("ERROR: %s: %s\n", desc, pfm_strerror(code));
        pfm_terminate();
        exit(code);
    }
}

void list_pmu_events(pfm_pmu_t pmu)
{
    pfm_event_info_t info  = {.size = sizeof(pfm_event_info_t)};
    pfm_pmu_info_t   pinfo = {.size = sizeof(pfm_pmu_info_t)};
    int              i, ret;

    ret = pfm_get_pmu_info(pmu, &pinfo);
    check_pfm_result(ret, "pfm_get_pmu_info");

    for (i = pinfo.first_event; i != -1; i = pfm_get_event_next(i)) {
        ret = pfm_get_event_info(i, PFM_OS_PERF_EVENT_EXT, &info);
        check_pfm_result(ret, "pfm_get_event_info");
        printf("%s Event: %s::%s %s\n", pinfo.is_present ? "Active" : "Supported", pinfo.name,
               info.name, info.desc);
    }
}

void print_pmu_event(const char* event_name)
{
    int                    ret;
    char*                  fstr = NULL;
    struct perf_event_attr attr = {};
    pfm_perf_encode_arg_t  arg  = {
          .size = sizeof(pfm_perf_encode_arg_t), .attr = &attr, .fstr = &fstr};

    ret = pfm_get_os_event_encoding(event_name, PFM_PLM3, PFM_OS_PERF_EVENT_EXT, &arg);
    check_pfm_result(ret, "find_event");

    printf("Found event type: 0x%x\n", arg.attr->type);
    printf("Found event config: 0x%lx\n", arg.attr->config);
    printf("Event string: %s\n", *arg.fstr);
}

int main(int argc, char** argv)
{
    int ret;

    ret = pfm_initialize();
    check_pfm_result(ret, "pfm_initialize");

    if (argc == 1) {
        list_pmu_events(PFM_PMU_ARM_CORTEX_A72);
    } else {
        for (int i = 1; i < argc; i++) {
            print_pmu_event(argv[i]);
        }
    }

    pfm_terminate();

    return EXIT_SUCCESS;
}
