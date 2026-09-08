function s2 = samplevar(x)
n = length(x);
s2 = sum((x-mean(x))^2)/(n-1);
end