function s2 = samplevar(x)
    % s2 = samplevar(x)
    % Computes the sample variance of the vector x:
    %   s^2 = 1/(n-1) * sum_i (x_i - xbar)^2,  xbar = mean(x)

    % TODO 1: get n = number of elements in x
    n = numel(x);
    % TODO 2: compute xbar, the mean of x
    xbar = mean(x);
    % TODO 3: compute s2 using the formula above
    %   careful: you need ELEMENT-WISE squaring here, not matrix power
    s2 = 0;
    for i = 1:n
        s2 = s2 + (x(i) - xbar)^2;
    end
    s2 = s2 / (n - 1);
end
