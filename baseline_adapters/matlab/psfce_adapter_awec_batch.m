function psfce_adapter_awec_batch(input_mat, output_mat, repo_root)
data = load(input_mat);
required = {'base_parts','c','seed','params_json_list'};
for i = 1:numel(required)
    if ~isfield(data, required{i})
        error('PSFCE:Input:MissingField', 'Missing %s', required{i});
    end
end
if isfield(data,'y') || isfield(data,'gt') || isfield(data,'ground_truth')
    error('PSFCE:Input:Leakage', 'Ground truth must not enter an official baseline adapter');
end
if exist(fullfile(repo_root, 'solver_AWTP.m'), 'file') ~= 2
    error('PSFCE:AWEC:MissingOfficialCode', 'solver_AWTP.m not found under %s', repo_root);
end
addpath(genpath(repo_root));

base_parts = double(data.base_parts);
c = double(data.c(1));
seed = double(data.seed(1));
params_json_list = data.params_json_list;
if ischar(params_json_list) || isstring(params_json_list)
    params_json_list = {char(params_json_list)};
end
p = numel(params_json_list);

pre_tic = tic;
H = Gbe(base_parts);
CA = H * H' ./ size(base_parts,2);
first_params = jsondecode(char(params_json_list{1}));
max_order = psfce_v4_param(first_params, 'max_order', 2);
neighbor_rate = psfce_v4_param(first_params, 'neighbor_rate', 0.5);
connections = V9_generate_multi_connec( ...
    V9_LocalKernelCalculation(CA, neighbor_rate, c), max_order);
preprocess_seconds = toc(pre_tic);

labels_matrix = zeros(size(base_parts,1), p, 'int32');
runtime_seconds = zeros(1,p);
adapter_meta_json_list = cell(1,p);
for j = 1:p
    params = jsondecode(char(params_json_list{j}));
    lambda = psfce_v4_param(params, 'lambda', 0.1);
    gamma = psfce_v4_param(params, 'gamma', 10);
    decoder = psfce_v4_param(params, 'decoder', 'H');
    if ~strcmp(decoder, 'H')
        error('PSFCE:AWEC:Variant', 'V4 predeclares AWEC-H; decoder must be H');
    end
    if psfce_v4_param(params, 'max_order', 2) ~= max_order || ...
            psfce_v4_param(params, 'neighbor_rate', 0.5) ~= neighbor_rate
        error('PSFCE:AWEC:BatchInvariant', ...
            'All batch settings must share max_order and neighbor_rate');
    end
    rng(seed, 'twister');
    solver_tic = tic;
    [~, Z] = psfce_awec_solver_scalar_inverse(CA, connections, lambda, gamma, c);
    similarity_vector = squareform(Z - diag(diag(Z)), 'tovector');
    distance_vector = 1 - similarity_vector;
    labels = cluster(linkage(distance_vector, 'average'), 'maxclust', c);
    if min(labels) == 0, labels = labels + 1; end
    runtime_seconds(j) = toc(solver_tic) + preprocess_seconds / p;
    labels_matrix(:,j) = int32(labels(:));
    details = struct('entrypoint','solver_AWTP', ...
        'execution','batched_preprocessing_scalar_identity_inverse', ...
        'adapter_revision','awec-batch-scalar-inverse-v2c', ...
        'input','frozen_base_parts','variant','AWEC-H', ...
        'lambda',lambda,'gamma',gamma,'max_order',max_order, ...
        'neighbor_rate',neighbor_rate,'preprocess_seconds_share',preprocess_seconds/p);
    adapter_meta_json_list{j} = jsonencode(details);
end
save(output_mat, 'labels_matrix', 'runtime_seconds', ...
    'adapter_meta_json_list', 'preprocess_seconds', '-v7');
end
