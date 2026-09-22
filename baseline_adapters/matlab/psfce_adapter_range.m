function psfce_adapter_range(input_mat, output_mat, repo_root)
[base_parts, c, seed, params] = psfce_v4_load_input(input_mat);
if exist(fullfile(repo_root, 'solve_RANGE.m'), 'file') ~= 2
    error('PSFCE:RANGE:MissingOfficialCode', 'solve_RANGE.m not found under %s', repo_root);
end
addpath(genpath(repo_root));
alpha = psfce_v4_param(params, 'alpha', 0.8);
fuzzy_threshold = psfce_v4_param(params, 'fuzzy_threshold', 0.8);
lambda = psfce_v4_param(params, 'lambda', 0.5);
anchor_offset = psfce_v4_param(params, 'anchor_offset', -1);
kmeans_replicates = psfce_v4_param(params, 'kmeans_replicates', 3);
anchor_count = max(1, c + anchor_offset);

H0 = Gbe(base_parts);
cluster_similarity = full(simxjac(H0'));
walk_similarity = RandomWalkofCluster(cluster_similarity);
H = HFES(H0, walk_similarity, alpha, fuzzy_threshold);
[Z_clean, ~] = solve_RANGE(H, anchor_count, lambda);
[U,~,~] = svd(Z_clean', 'econ');
row_norm = sqrt(sum(U.^2,2));
row_norm(row_norm < eps) = 1;
U = U ./ row_norm;
rng(seed, 'twister');
labels = kmeans(U, c, 'MaxIter', 100, 'Replicates', kmeans_replicates);
details = struct('entrypoint','HFES+solve_RANGE','input','frozen_base_parts', ...
    'alpha',alpha,'fuzzy_threshold',fuzzy_threshold,'lambda',lambda, ...
    'anchor_offset',anchor_offset,'kmeans_replicates',kmeans_replicates);
psfce_v4_save_output(output_mat, labels, 'RANGE', details);
end
