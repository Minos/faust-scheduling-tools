process = noise * button("play") : resonator(80, 1)
with {
    resonator(d, a) = (+ : @(d-1)) ~ (average : *(a));
    average(x) = x+x' : *(0.5);
    random = +(12345) ~ *(1103515245);
    noise = random / 2147483647.0;
};
