CC := clang
CXX := clang++

CFLAGS := -march=native -O3 -ffast-math --std=c++20 -Wall -Wno-unused-function
LDFLAGS := -lpfm -ldl

# FIXME: This condition is always true.
ifneq ($(FAUST_PREFIX), undefined)
CFLAGS += -I${FAUST_PREFIX}/architecture
endif

all: schedrun schedprint pfm_info

schedrun: arch/schedrun.o arch/dsp_measuring.o arch/pfm_utils.o arch/alsa.o arch/basic.o arch/load.o arch/jack.o
	@echo "LD     $@"
	@$(CXX) -ldl -lpfm -lasound -ljack $^ -o $@

schedprint: arch/schedprint.o arch/load.o
	@echo "LD     $@"
	@$(CXX) -ldl $^ -o $@

.cpp.o:
	@echo "CXX    $@"
	@$(CXX) ${CFLAGS} -c $< -o $@

pfm_info: pfm_info.c
	@echo "CC     $@"
	@$(CC) -lpfm $< -o $@

clean:
	@rm -f schedrun schedprint pfm_info
	@rm -f arch/*.o

.PHONY: all clean
