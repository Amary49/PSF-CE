function [base_parts, c, seed, params] = psfce_v4_load_input(input_mat)
S = load(input_mat);
required = {'base_parts','c','seed','params_json','input_meta_json'};
for i = 1:numel(required)
    if ~isfield(S, required{i})
        error('PSFCE:BadInput', 'Missing required input field: %s', required{i});
    end
end
forbidden = {'y','Y','gt','ground_truth','labels'};
for i = 1:numel(forbidden)
    if isfield(S, forbidden{i})
        error('PSFCE:LabelLeakage', 'Forbidden evaluator field reached adapter: %s', forbidden{i});
    end
end
base_parts = double(S.base_parts);
c = double(S.c(1));
seed = double(S.seed(1));
raw = S.params_json;
if iscell(raw), raw = raw{1}; end
if isstring(raw), raw = char(raw); end
params = jsondecode(raw);
if size(base_parts,1) < 2 || size(base_parts,2) < 1
    error('PSFCE:BadInput', 'base_parts must have shape n x M');
end
if any(base_parts(:) < 1) || any(base_parts(:) ~= floor(base_parts(:)))
    error('PSFCE:BadInput', 'base_parts must contain positive integer labels');
end
rng(seed, 'twister');
end
