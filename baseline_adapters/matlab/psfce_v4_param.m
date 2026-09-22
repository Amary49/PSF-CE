function value = psfce_v4_param(params, name, default_value)
if isfield(params, name)
    value = params.(name);
else
    value = default_value;
end
end
