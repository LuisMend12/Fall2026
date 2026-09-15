function r = polyadd(p, q)
    % r = polyadd(p, q)
    % p and q are row vectors of polynomial coefficients in DECREASING
    % degree order, e.g. p = [1 2 3] means 1*x^2 + 2*x + 3.
    % p and q may have different lengths (different degrees).
    % Returns r, the coefficient vector of p + q.

    % TODO 1: find the length of p and q
    np = length(p);
    nq = length(q);

    % TODO 2: figure out how many leading zeros each vector needs so
    %   that both vectors line up by DEGREE (not by index) before adding.
    %   Hint: the shorter vector is the lower-degree polynomial, so you
    %   pad zeros on the LEFT (the high-degree end) of the shorter one.
    max_len = max(np, nq);
    pp = [zeros(1, max_len - np), p];
    qq = [zeros(1, max_len - nq), q];

    % TODO 3: build padded versions pp and qq of p and q that are the
    %   same length

    % TODO 4: add them elementwise to get r
    r = pp + qq;
end
