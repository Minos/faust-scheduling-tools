BENCHARCH := bencharch.cpp
BENCHDIREXT := bench
DSP := dsp
FAUST := ./faust
FAUSTLANG := ocpp

CC ?= clang
CXX ?= clang++

CFLAGS := -ffast-math -O3 --std=c++20
LDFLAGS := -lpfm

COMPILERS ?= clang++ g++
ARCHS ?= x86-64 native
STRATEGIES ?= 0 1 2 3

faust_programs = $(foreach d, $(wildcard $(DSP)/*.dsp), $(basename $(notdir $(d)) .dsp))

cpp_sources = \
	$(foreach f, $(faust_programs), \
		$(foreach s, $(STRATEGIES), \
			$(DSP)/$(f).$(BENCHDIREXT)/$(f)_ss$(s).cpp))

binaries = \
	$(foreach cpp, $(cpp_sources), \
		$(foreach cc, $(COMPILERS), \
			$(foreach arch, $(ARCHS), \
				$(basename $(cpp))_$(cc)_$(arch))))

all: binaries

binaries: $(binaries)

cpp: $(cpp_sources)

events: events.c
	$(CC) -lpfm $< -o $@

clean:
	@rm -f $(cpp_sources) $(binaries)


define FAUST_BUILD
$(DSP)/$(1).$(BENCHDIREXT)/$(1)_ss$(2).cpp: $(DSP)/$(1).dsp $(BENCHARCH)
	@echo "  FAUST " $(1) [strategy $(2)]
	@mkdir -p $$(dir $$@)
	@$(FAUST) -a $(BENCHARCH) -lang $(FAUSTLANG) -ss $(2) $$< -o $$@

endef

$(foreach f, $(faust_programs), \
	$(foreach s, $(STRATEGIES), \
		$(eval $(call FAUST_BUILD,$(f),$(s)))))

define CPP_BUILD
$(DSP)/$(1).$(BENCHDIREXT)/$(1)_ss$(2)_$(3)_$(4): $(DSP)/$(1).$(BENCHDIREXT)/$(1)_ss$(2).cpp
	@echo "  CXX   " $(1) [strategy $(2), $(3), $(4)]
	@$(3) $(CFLAGS) $(LDFLAGS) -march=$(4) $$< -o $$@

endef

$(foreach f, $(faust_programs), \
	$(foreach s, $(STRATEGIES), \
		$(foreach cc, $(COMPILERS), \
			$(foreach arch, $(ARCHS), \
				$(eval $(call CPP_BUILD,$(f),$(s),$(cc),$(arch)))))))

define DSP_TARGET
$(DSP)/$(1): $(foreach s, $(STRATEGIES),\
		$(foreach cc, $(COMPILERS),\
			$(foreach arch, $(ARCHS),\
				$(DSP)/$(1).$(BENCHDIREXT)/$(1)_ss$(s)_$(cc)_$(arch))))

.PHONY: $(DSP)/$(1)

endef

$(foreach f, $(faust_programs), $(eval $(call DSP_TARGET,$f)))

.PHONY: all clean cpp binaries
.PRECIOUS: %.cpp
