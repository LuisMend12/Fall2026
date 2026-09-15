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
poly_cases = {
    % {p, q, expected}
    {[1 2 3],      [5 0 1 2],   [5 1 3 5]};     % original example, q longer
    {[1 2],        [3 4],       [4 6]};          % equal length
    {[1 0 -1],     [2],         [1 0 1]};        % p longer than q
    {[3],          [1 2 3],     [1 2 6]};        % q longer than p
    {[1 2],        [-1 3],      [0 5]};          % leading zero in result (not stripped)
    {[0 0],        [0 0],       [0 0]};          % all zeros
    {[5],          [3],         [8]};            % both scalars
    {[1.5 2.5],    [0.5 -0.5],  [2 2]};          % decimals
};

for k = 1:numel(poly_cases)
    p = poly_cases{k}{1};
    q = poly_cases{k}{2};
    expected = poly_cases{k}{3};
    r = polyadd(p, q);
    if isequal(r, expected)
        status = 'PASS';
    else
        status = 'FAIL';
    end
    fprintf('Poly case %d: polyadd = [%s], expected = [%s] -> %s\n', ...
        k, num2str(r), num2str(expected), status);
end
