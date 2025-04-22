import("stdfaust.lib");

process = si.bpar(8, @(1024)) :> si.bus(2);
