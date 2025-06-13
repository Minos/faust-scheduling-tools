#include <cstring>
#include <iostream>

#include <perfmon/pfmlib.h>
#include <perfmon/pfmlib_perf_event.h>

#include "pfm_utils.h"

void pfm_utils_initialize()
{
    int ret = pfm_initialize();
    if (ret != PFM_SUCCESS) {
        std::cerr << "Error: " << pfm_strerror(ret) << std::endl;
        pfm_terminate();
        exit(ret);
    }
}

void pfm_utils_terminate()
{
    pfm_terminate();
}

void pfm_utils_parse_events(const char* arg, std::vector<std::string>& events)
{
    const char* event = arg;
    const char* end;
    size_t      size;

    while ((end = strchr(event, ',')) != NULL) {
        size = end - event;
        events.emplace_back(event, size);
        event = end + 1;
    }

    events.emplace_back(event);
}

int pfm_utils_open_named_event(const char* str, int group_fd)
{
    int                   ret;
    perf_event_attr       attr = {.size = sizeof(perf_event_attr)};
    pfm_perf_encode_arg_t arg  = {.attr = &attr, .size = sizeof(pfm_perf_encode_arg_t)};

    ret = pfm_get_os_event_encoding(str, PFM_PLM3, PFM_OS_PERF_EVENT_EXT, &arg);
    if (ret != PFM_SUCCESS) {
        std::cerr << "Error opening event " << str << ": " << pfm_strerror(ret) << std::endl;
        pfm_terminate();
        exit(ret);
    }

    attr.disabled       = 1;
    attr.exclude_kernel = 1;
    attr.exclude_hv     = 1;

    return syscall(SYS_perf_event_open, &attr, 0, -1, group_fd, 0);
}
