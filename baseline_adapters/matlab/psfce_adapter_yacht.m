function psfce_adapter_yacht(input_mat, output_mat, repo_root)
[base_parts, c, seed, params] = psfce_v4_load_input(input_mat);
code_root = fullfile(repo_root, 'measure');
if exist(fullfile(code_root, 'solve_YACHT.m'), 'file') ~= 2
    error('PSFCE:YACHT:MissingOfficialCode', 'solve_YACHT.m not found under %s', code_root);
end
addpath(code_root);
alpha = psfce_v4_param(params, 'alpha', 0.95);
theta = psfce_v4_param(params, 'theta', 0.4);
anchor_offset = psfce_v4_param(params, 'anchor_offset', -1);
walk_order = psfce_v4_param(params, 'walk_order', 20);
kmeans_replicates = psfce_v4_param(params, 'kmeans_replicates', 3);
anchor_count = max(1, c + anchor_offset);

H0 = Gbe(base_parts);
[~, micro_labels] = computeMicroclusters(H0);
local_indicator = base_clustering_preserve(micro_labels, c);
cluster_similarity = full(simxjac(H0'));
walk_similarity = psfce_v4_yacht_walk(cluster_similarity, walk_order);
H = align_hyper(H0, walk_similarity, alpha);
edge_weights = computeECI_hyper(H, theta, size(base_parts,2));
rng(seed, 'twister');
[U, ~] = solve_YACHT(H, anchor_count, edge_weights', local_indicator);
row_norm = sqrt(sum(U.^2,2));
row_norm(row_norm < eps) = 1;
U = U ./ row_norm;
labels = kmeans(U, c, 'MaxIter', 100, 'Replicates', kmeans_replicates);
details = struct('entrypoint','solve_YACHT','input','frozen_base_parts', ...
    'alpha',alpha,'theta',theta,'anchor_offset',anchor_offset, ...
    'walk_order',walk_order,'kmeans_replicates',kmeans_replicates, ...
    'compatibility_patch','paper walk order is parameterized; repository helper hard-codes 10');
psfce_v4_save_output(output_mat, labels, 'YACHT', details);
end

function R = psfce_v4_yacht_walk(W, walk_order)
N = size(W,1);
W = W - diag(diag(W));
D = diag(1 ./ sum(W,1));
D(isinf(D)) = 0;
P = D * W;
power = P;
acc = power * power';
for i = 1:max(0,walk_order-1)
    power = power * P;
    acc = acc + power * power';
end
den = repmat(diag(acc),1,N);
R = acc ./ sqrt(den .* den');
R(~isfinite(R)) = 0;
isolated = sum(P,2) < 1e-10;
R(isolated,:) = 0;
R(:,isolated) = 0;
end
