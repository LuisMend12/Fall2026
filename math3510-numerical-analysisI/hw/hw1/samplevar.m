function s2 = samplevar(x)
    % s2 = samplevar(x)
    % Computes the sample variance of the vector x:
    %   s^2 = 1/(n-1) * sum_i (x_i - xbar)^2,  xbar = mean(x)

    n = numel(x);
    xbar = mean(x);
    s2 = 0;
    for i = 1:n
        s2 = s2 + (x(i) - xbar)^2;
    end
    s2 = s2 / (n - 1);
end
