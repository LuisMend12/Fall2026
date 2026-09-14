% Quick sanity checks for Problem 1 and Problem 2.
% Run this script in MATLAB (with samplevar.m and polyadd.m on the path)
% once you've filled in the TODOs.

%% Problem 1: samplevar
x = [2 4 4 4 5 5 7 9];

% TODO: call samplevar(x) and MATLAB's built-in var(x), and compare
% e.g.:
% mine = samplevar(x);
% builtin_val = var(x);
% fprintf('samplevar: %g, var: %g\n', mine, builtin_val);

%% Problem 2: polyadd
p = [1 2 3];      % x^2 + 2x + 3
q = [5 0 1 2];     % 5x^3 + 0x^2 + x + 2

% TODO: call polyadd(p, q) and check it by hand
% Expected: 5x^3 + 1x^2 + 3x + 5  ->  [5 1 3 5]
% r = polyadd(p, q)
