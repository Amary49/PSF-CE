function psfce_adapter_awec(input_mat, output_mat, repo_root)
[base_parts, c, seed, params] = psfce_v4_load_input(input_mat);
if exist(fullfile(repo_root, 'solver_AWTP.m'), 'file') ~= 2
    error('PSFCE:AWEC:MissingOfficialCode', 'solver_AWTP.m not found under %s', repo_root);
end
addpath(genpath(repo_root));
lambda = psfce_v4_param(params, 'lambda', 0.1);
gamma = psfce_v4_param(params, 'gamma', 10);
max_order = psfce_v4_param(params, 'max_order', 2);
neighbor_rate = psfce_v4_param(params, 'neighbor_rate', 0.5);
decoder = psfce_v4_param(params, 'decoder', 'H');
if ~strcmp(decoder, 'H')
    error('PSFCE:AWEC:Variant', 'V4 predeclares AWEC-H; decoder must be H');
end

H = Gbe(base_parts);
CA = H * H' ./ size(base_parts,2);
local_kernel = V9_LocalKernelCalculation(CA, neighbor_rate, c);
connections = V9_generate_multi_connec(local_kernel, max_order);
rng(seed, 'twister');
[~, Z] = solver_AWTP(CA, connections, lambda, gamma, c);
similarity_vector = squareform(Z - diag(diag(Z)), 'tovector');
distance_vector = 1 - similarity_vector;
labels = cluster(linkage(distance_vector, 'average'), 'maxclust', c);
if min(labels) == 0, labels = labels + 1; end
details = struct('entrypoint','solver_AWTP','input','frozen_base_parts', ...
    'variant','AWEC-H','lambda',lambda,'gamma',gamma, ...
    'max_order',max_order,'neighbor_rate',neighbor_rate);
psfce_v4_save_output(output_mat, labels, 'AWEC', details);
end
