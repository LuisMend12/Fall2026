function s2 = samplevar(x)
    % This function computes the sample variance of the input vector x
    % and returns the result as s2.

    % Initialize variables
    n = length(x);
    s2 = sum((x - mean(x)).^2) / (n - 1);
end

    % Display the result
    fprintf('The sum of the series is approximately: %.10f\n', s2);
end