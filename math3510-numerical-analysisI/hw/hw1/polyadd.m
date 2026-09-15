function r = polyadd(p, q)
    % r = polyadd(p, q)
    % p and q are row vectors of polynomial coefficients in DECREASING
    % degree order, e.g. p = [1 2 3] means 1*x^2 + 2*x + 3.
    % p and q may have different lengths (different degrees).
    % Returns r, the coefficient vector of p + q.

    np = length(p);
    nq = length(q);

    max_len = max(np, nq);
    pp = [zeros(1, max_len - np), p];
    qq = [zeros(1, max_len - nq), q];

    r = pp + qq;
end
