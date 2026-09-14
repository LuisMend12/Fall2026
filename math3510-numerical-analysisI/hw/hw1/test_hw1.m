% Quick sanity checks for Problem 1 and Problem 2.
% Run this script in MATLAB (with samplevar.m and polyadd.m on the path)
% once you've filled in the TODOs.

%% Problem 1: samplevar
test_cases = {
    [2 4 4 4 5 5 7 9];      % original example
    [1 2];                   % smallest possible n=2
    [5 5 5 5 5];              % all identical -> variance 0
    [-3 -1 0 2 7];             % negative numbers
    [1.5 2.25 3.75 4.1 -0.5];  % decimals
    (1:100);                   % larger vector
    [10 -10];                  % symmetric around 0
    rand(1, 20);                % random vector
};

for k = 1:numel(test_cases)
    x = test_cases{k};
    mine = samplevar(x);
    builtin_val = var(x);
    ok = abs(mine - builtin_val) < 1e-10;
    if ok
        status = 'PASS';
    else
        status = 'FAIL';
    end
    fprintf('Case %d: samplevar = %g, var = %g -> %s\n', ...
        k, mine, builtin_val, status);
end

%% Problem 2: polyadd
p = [1 2 3];      % x^2 + 2x + 3
q = [5 0 1 2];     % 5x^3 + 0x^2 + x + 2

% TODO: call polyadd(p, q) and check it by hand
% Expected: 5x^3 + 1x^2 + 3x + 5  ->  [5 1 3 5]
% r = polyadd(p, q)
