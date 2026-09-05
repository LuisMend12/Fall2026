function s2 = hw1()
    % This function computes the sum of the series 1/n^2 for n=1 to infinity
    % and returns the result as s2.

    % Initialize variables
    s2 = 0; % Sum of the series
    n = 1;  % Starting value of n

    % Loop until the term is smaller than a threshold (e.g., 1e-10)
    while true
        term = 1 / (n^2); % Compute the current term
        if term < 1e-10
            break; % Exit loop if term is small enough
        end
        s2 = s2 + term; % Add the term to the sum
        n = n + 1;      % Increment n
    end

    % Display the result
    fprintf('The sum of the series is approximately: %.10f\n', s2);
end