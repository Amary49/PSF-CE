function psfce_v4_save_output(output_mat, labels, method, details)
labels = double(labels(:));
adapter_meta = struct('schema','psfce-v4-matlab-adapter-v1', ...
    'method',method,'details',details);
adapter_meta_json = jsonencode(adapter_meta);
save(output_mat, 'labels', 'adapter_meta_json', '-v7');
end
