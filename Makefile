%.cpp: dsp/%.dsp bencharch.cpp
	./faust -a bencharch.cpp -ss 0 $< -lang ocpp -o $@

%: %.cpp
	clang++ --std=c++20 -O3 -ffast-math -march=native -lpfm $< -o $@
