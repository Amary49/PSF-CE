function [labels,obj] = run_gpec_one_pool(BP,targetC,frozen)
%RUN_GPEC_ONE_POOL Call the unmodified official GPEC entry point.
% The official optimization/litekmeans.m resets rng(2025) internally.
% The wrapper therefore does not reseed or alter the author's RNG behavior.
if size(BP,2)~=20, error('GPEC:InputM','GPEC formal input must contain exactly M=20 frozen partitions.'); end
if targetC<1, error('GPEC:TargetC','Invalid target cluster count.'); end
if double(frozen.rng_seed)~=2025, error('GPEC:RNGContract','Frozen source-internal RNG seed must be 2025.'); end
[labels,~,obj]=runBiasDiversity(double(BP),double(targetC),double(frozen.alpha));
labels=double(labels(:)); if numel(labels)~=size(BP,1)||any(~isfinite(labels)), error('GPEC:Output','Official GPEC returned invalid labels.'); end
end
