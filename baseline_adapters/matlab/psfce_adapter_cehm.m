function psfce_adapter_cehm(input_mat, output_mat, repo_root)
[base_parts, c, seed, ~] = psfce_v4_load_input(input_mat);
code_root = fullfile(repo_root, 'demo code');
if exist(fullfile(code_root, 'CEHM.m'), 'file') ~= 2
    error('PSFCE:CEHM:MissingOfficialCode', 'CEHM.m not found under %s', code_root);
end
addpath(code_root);
rng(seed, 'twister');
[labels, ~] = CEHM(base_parts, c);
details = struct('entrypoint','CEHM','input','frozen_base_parts','variant','published');
psfce_v4_save_output(output_mat, labels, 'CEHM', details);
end
