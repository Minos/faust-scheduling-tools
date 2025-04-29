import("stdfaust.lib");


omega = hslider("[0]freq", 440.0, 50, 1600, 1) * 2 * ma.PI;
gamma = hslider("[1]gamma", 0.5, 0.01, 2, 0.01);
zeta = hslider("[2]zeta", 0.5, 0.01, 2, 0.01);

clarinet = checkbox("[3]clarinet");

Q1 = hslider("Q1", 37, 1, 100, 1);
Q2 = hslider("Q2", 41, 1, 100, 1);
Z1 = hslider("Z1", 55, 1, 100, 1);
Z2 = hslider("Z2", 33, 1, 100, 1);

at = hslider("attack",0.05, 0, 0.5, 0.001);
dt = hslider("decay",0.05, 0, 0.5, 0.001);
sl = hslider("sustain", 0.8, 0, 1, 0.01);

rt = hslider("release",0.05, 0, 0.5, 0.001);

envelope = ba.if(checkbox("envelope"),
                 (button("gate") : tgroup("envelope_params", en.adsr(at, dt, sl, rt))),
                 1);
                 
freq_ratio = (2 + clarinet);
Omega = omega, omega*freq_ratio;
Q = Q1, Q2;
Z = Z1, Z2;

N = ba.count(Q);
M = 2*N;

clarinet_diff_eq(Q, Z, Omega, gamma, zeta) = si.bus(2*N) <: y, dy
with {
    x = ba.selectbus(N, 2, 0);
    dx = ba.selectbus(N, 2, 1);

    a = zeta * (3 * gamma - 1) / (2 * sqrt(gamma));
    b = -1 * zeta * (3 * gamma + 1) / (8 * sqrt(gamma^3));
    c = -1 * zeta * (gamma + 1) / (16 * sqrt(gamma^5));

    x_sum = x :> _;
    dx_sum = dx :> _;

    y = dx;
    dy = par(i, N,
            (omega / q) * (z * dx_sum * (a + 2*b*x_sum + 3*c*x_sum*x_sum) - xi) 
                - omega*omega*xi
            with {
                omega = ba.take(i+1, Omega);
                q = ba.take(i+1, Q);
                z = ba.take(i+1, Z);
                xi = x : ba.selector(i, N);
            }
        );
};

runge_kutta_step(eq) = si.bus(M) <: si.bus(M), (k : si.bpar(M, *(h/6))) :> si.bus(M)
with {
    h = 1/ma.SR;

    k1 = si.bus(M) : eq;
    k2 = si.bus(M), (k1 : si.bpar(M, *(h/2))) :> eq;
    k3 = si.bus(M), (k2 : si.bpar(M, *(h/2))) :> eq;
    k4 = si.bus(M), (k3 : si.bpar(M, *(h))) :> eq;

    k = k1, (k2 :si.bpar(M, *(2))), (k3 : si.bpar(M, *(2))), k4 :> si.bus(M);
};

runge_kutta_solver(eq, x0) = (si.bus(M), x :> runge_kutta_step(eq)) ~ si.bus(M)
with {
    x = x0, si.bpar(M, 0.0) : ba.selectbus(M, 2, ba.time > 0);
};

eq = clarinet_diff_eq(Q, Z, Omega, gamma, zeta);
init = si.bpar(M, 0.01);

process = runge_kutta_solver(eq, init) : ba.selectbus(N, 2, 0) :> *(envelope) <: si.bus(2);
