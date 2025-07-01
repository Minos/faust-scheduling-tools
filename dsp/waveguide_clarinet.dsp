import("stdfaust.lib");

// The G function
g_function(gamma, zeta, p_minus) = gamma - x - p_minus
with {
    y = gamma - 2 * p_minus;
    psi = 1 / (zeta^2);
    mu = (9/2) * (3*y - 1);

    non_beating_positive_flow = (-2/3 * eta * sin(1/3 * asin((psi - mu) / (zeta * eta^3))) + 1/(3 * zeta))^2 
    with { 
        eta = sqrt(3 + psi);
    };

    non_beating_negative_flow = positive_discr, negative_discr : select2(discr < 0)
    with {
        q = 1/9 * (3 - psi);
        r = 0 - (psi + mu) / (27*zeta);
        discr = q^3 + r^2;

        positive_discr = 0 - (s - q/s - 1/(3 * zeta))^2
        with {
            s = pow(r + sqrt(discr), 1/3);
        };

        negative_discr = 0 - (2/3 * eta2 * cos(1/3 * acos(0 - (psi + mu) / (zeta * eta2^3))) - 1/(3*zeta))^2
        with {
            eta2 = sqrt(-3 + psi);
        };
    };

    non_beating_flow = non_beating_positive_flow, non_beating_negative_flow : select2(y < 0);
    beating_reed = y;

    x = non_beating_flow, beating_reed : select2(y > 1);
};

// The reflection function
reflection_function(cutoff, delay, lambd) = lambd * fi.lowpass(filter_order, cutoff) : @(safe_delay)
with {
    filter_order = 1;
    safe_delay = delay : min(1 << 14) : max(0);
};


clarinet_model(gamma, zeta, lambd, cutoff, delay) = (g ~ reflection) :> _
with {
    g = g_function(gamma, zeta), _;
    reflection = reflection_function(cutoff, delay, lambd) <: _, _;
};


clarinet_model_freq(gamma, zeta, lambd, cutoff, freq) = clarinet
with {
    speed_of_sound = 340;
    air_density = 1.2;
    tube_length = speed_of_sound / (4 * freq) - 0.012;
    delay = 2 * tube_length / speed_of_sound * ma.SR;
    clarinet = clarinet_model(gamma, zeta, lambd, cutoff, delay);
};

process = clarinet_model;
