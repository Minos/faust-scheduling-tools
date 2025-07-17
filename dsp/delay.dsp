import("stdfaust.lib");

d = _ <: @(1000) * 0.3 + @(1001) * 0.2;

process = si.bpar(16, d);
