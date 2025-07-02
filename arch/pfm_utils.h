#ifndef __FCSCHEDTOOL_PFM_UTILS_H__
#define __FCSCHEDTOOL_PFM_UTILS_H__

#include <string>
#include <vector>

void pfm_utils_initialize();
void pfm_utils_terminate();

void pfm_utils_parse_events(const char* arg, std::vector<std::string>& events);
int  pfm_utils_open_named_event(const char* str, int group_fd);

#endif
