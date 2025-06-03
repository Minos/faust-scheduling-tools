import("stdfaust.lib");

process = button("play") : ba.impulsify : resonator(80, 1)
with {
    resonator(d, a) = (+ : @(d-1)) ~ (average : *(a));
    average(x) = x+x' : *(0.5);
};
