BENCHARCH := bencharch.cpp
BENCHDIREXT := bench
DSP := dsp
FAUST := ./faust
FAUSTLANG := ocpp

CFLAGS := -ffast-math -O3 --std=c++20
LDFLAGS := -lpfm

COMPILERS := clang++ g++
ARCHS := x86-64 native
STRATEGIES := 0 1 2 3

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

clean:
	rm -f $(cpp_sources) $(binaries)

define FAUST_BUILD
$(DSP)/$(1).$(BENCHDIREXT)/$(1)_ss$(2).cpp: $(DSP)/$(1).dsp $(BENCHARCH)
	$(FAUST) -a $(BENCHARCH) -lang $(FAUSTLANG) -ss $(2) $$< -o $$@

endef

$(foreach f, $(faust_programs), \
	$(foreach s, $(STRATEGIES), \
		$(eval $(call FAUST_BUILD,$(f),$(s)))))

define CPP_BUILD
$(DSP)/$(1).$(BENCHDIREXT)/$(1)_ss$(2)_$(3)_$(4): $(DSP)/$(1).$(BENCHDIREXT)/$(1)_ss$(2).cpp
	$(3) $(CFLAGS) $(LDFLAGS) -march=$(4) $$< -o $$@

endef

$(foreach f, $(faust_programs), \
	$(foreach s, $(STRATEGIES), \
		$(foreach cc, $(COMPILERS), \
			$(foreach arch, $(ARCHS), \
				$(eval $(call CPP_BUILD,$(f),$(s),$(cc),$(arch)))))))

.PHONY: all clean cpp binaries
.PRECIOUS: %.cpp
