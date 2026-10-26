# Map-based localization of a depth camera against its own map (frame-to-model / scan-to-map registration) to bound odometry drift on an indoor drone

Scope: correcting a drifting pose by registering each ZED stereo depth frame (useful 0.3-8 m, 1280x720) to the accumulated map (TSDF, voxels, or points), plus how to detect and handle geometric degeneracy. Research date: 2026-10-26.

Verification legend. Items tagged **[verified]** were checked against the linked page during this session. Items tagged **[not re-fetched]** come from the primary paper, cited at its canonical URL. Their content is well known, but the exact wording or numbers were not re-read this session, so the report writer should treat them as lower confidence.

---

## Q1. Frame-to-model / scan-to-map registration: methods, accuracy, run time, and why it bounds drift only when revisiting

### Takeaway
Registering each frame to the accumulated model (KinectFusion-style raycast TSDF, surfels, a voxel hash map, or an ikd-tree) instead of to the previous frame turns per-frame error into error relative to the map. Revisiting already-mapped space therefore pulls the pose back toward where it was when that space was mapped. While exploring, the map in view was just built from the drifting pose, so scan-to-map is still open-loop odometry: KISS-ICP, for example, still drifts about 0.5% of distance travelled on KITTI. Only loop closure or global re-optimization (BundleFusion, ElasticFusion) or an external prior map removes drift that has already accumulated.

### Cited Findings
**Classic RGB-D dense frame-to-model**
- The standard way to localize a sensor in a TSDF is to register the current depth image against a point cloud raycast from the map at the previous pose, with a point-to-plane metric solved by Gauss-Newton **[verified]** — [ar5iv 2301.12796](https://ar5iv.labs.arxiv.org/html/2301.12796)
- KinectFusion (Newcombe et al., ISMAR 2011) introduced this approach: projective data association, point-to-plane ICP against the raycast TSDF surface, and GPU real-time. The paper argues frame-to-model tracking drifts much less than frame-to-frame. It used a fixed-size volume, so it works in a room-scale workspace only **[not re-fetched]** — [Microsoft Research PDF](https://www.microsoft.com/en-us/research/wp-content/uploads/2016/02/ismar2011.pdf)
- ElasticFusion (Whelan et al., RSS 2015) has a surfel map, frame-to-model tracking that combines ICP with photometric RGB terms, and non-rigid "model-to-model" loop closures through a deformation graph **[not re-fetched]** — [RSS 2015 proceedings](http://www.roboticsproceedings.org/rss11/p01.pdf)
- BundleFusion (Dai et al., arXiv 2016, published in ACM TOG 2017) optimizes a global set of camera poses on every frame using the full RGB-D history, hierarchically. It localizes against globally optimized frames rather than relying on frame-to-frame tracking. It combines sparse features with dense geometric and photometric matching, recovers from tracking failure, and re-estimates the 3D model in real time to keep it globally consistent **[verified, abstract]** — [arXiv 1604.01093](https://arxiv.org/abs/1604.01093). The mechanism is TSDF de-integration and re-integration of frames whose poses change. The paper runs on two desktop GPUs **[not re-fetched; hardware detail not in abstract]**.
- TUM RGB-D ATE RMSE (cm) as tabulated by later papers:
  - fr1/desk: BundleFusion 1.6, ElasticFusion 2.0 **[verified]** — [Robust Keyframe-based Dense SLAM, arXiv 1711.05166](https://arxiv.org/pdf/1711.05166)
  - fr2/xyz: BundleFusion 1.1, ElasticFusion 1.1 **[verified]** — [RTAB-Map paper, arXiv 2403.06341](https://arxiv.org/pdf/2403.06341)
  - fr3/office: BundleFusion 2.2, ElasticFusion 1.7 **[verified]** — [RTAB-Map paper, arXiv 2403.06341](https://arxiv.org/pdf/2403.06341)
  - ElasticFusion on fr1/room is 21.49 cm in a re-run table **[verified]** — [EGG-Fusion, arXiv 2512.01296](https://arxiv.org/pdf/2512.01296). This shows how values differ between papers that re-run methods and papers that copy them.
- ICL-NUIM (synthetic) ATE, kt0-kt3:
  - BundleFusion: 0.6 / 0.4 / 0.6 / 1.1 cm
  - ElasticFusion: 0.9 / 0.9 / 1.4 / 10.6 cm **[verified]** — [ROSEFusion, arXiv 2105.05600](https://arxiv.org/pdf/2105.05600)
- Colored ICP (Park, Zhou, Koltun, ICCV 2017) jointly optimizes a photometric and a geometric term on colored point clouds, which constrains registration along flat but textured surfaces where point-to-plane alone is degenerate. It is implemented in Open3D **[not re-fetched]** — [ICCV 2017 open access](https://openaccess.thecvf.com/content_iccv_2017/html/Park_Colored_Point_Cloud_ICCV_2017_paper.html)

**LiDAR-era scan-to-map (applies directly to depth point clouds)**
- KISS-ICP (Vizzo et al., RA-L 2023, vol. 8(2), pp. 1029-1036) uses point-to-point ICP against a local voxel map with adaptive thresholding. KITTI average relative translational error is 0.50% (seq 00-10) and 0.61% (seq 11-21), open loop. It ranked 2nd among open-source methods, behind CT-ICP, and 9th overall **[verified]** — [arXiv 2209.15397](https://arxiv.org/pdf/2209.15397)
- KISS-ICP run time is reported as 26 ms per frame in a later comparison table that cites the original paper **[verified as a secondary citation; not checked against RA-L]** — [arXiv 2503.21293](https://arxiv.org/pdf/2503.21293). It ran at 34.36 FPS on an i7-1370P laptop on a different automotive dataset **[verified]** — [Odyssey dataset, arXiv 2512.14428](https://arxiv.org/pdf/2512.14428)
- FAST-LIO2 (Xu et al., HKU; arXiv 2021, IEEE T-RO 2022):
  - Registers raw points directly to the map, with no feature extraction. Points are temporally downsampled 1:4, and each is matched to its 5 nearest map neighbours to fit a local plane. The point-to-plane residual drives an iterated Kalman filter update.
  - The map is an incremental ikd-tree with O(log n) updates, versus O(n log n) to rebuild a k-d tree. It is held in a local cube of side L = 1000 m (default) that shifts with the sensor, with 0.5 m spatial downsampling.
  - Benchmarked on 19 sequences from 5 datasets, running on a DJI Manifold 2-C (i7-8550U) and a Khadas VIM3 (ARM).
  - Achieves "up to 100 Hz odometry and mapping".
  - **[verified]** — [ar5iv 2107.06829](https://ar5iv.labs.arxiv.org/html/2107.06829)
  - In an aggressive-flip UAV test with a Livox AVIA, it averaged about 2.01 ms per scan **[verified, search summary of the paper]** — [arXiv 2107.06829](https://arxiv.org/pdf/2107.06829)
- VGICP (Koide et al., ICRA 2021, pp. 11054-11059) builds GICP on a voxel map. Each voxel's distribution aggregates the per-point covariances, so no nearest-neighbour search is needed. It runs at 30 Hz on CPU (about 15k points) and 120 Hz on GPU, with accuracy comparable to GICP. NDT, by contrast, is very sensitive to voxel resolution **[verified]** — [ICRA 2021 PDF](https://staff.aist.go.jp/k.koide/assets/pdf/icra2021_02.pdf). The fast_gicp README lists multi-threaded FastVGICP at about 70 FPS **[verified]** — [fast_gicp](https://github.com/psiori/fast_gicp)
- small_gicp (Koide, JOSS, 10 Aug 2024, DOI 10.21105/joss.06948) is a header-only C++ library with parallel downsampling, nearest-neighbour search, normal/covariance estimation, and ICP/GICP/VGICP. It is reported as about 2x faster than fast_gicp **[verified]** — [JOSS paper](https://joss.theoj.org/papers/10.21105/joss.06948.pdf)
- LOCUS 2.0 (CoSTAR / NASA JPL, RA-L 2022) combines normals-based GICP, an adaptive voxel-grid filter that keeps computation roughly constant regardless of geometry, and a sliding-window map that bounds memory. On its dataset F, its maximum absolute pose error is 0.67 m, while FAST-LIO diverges to tens of km **[verified]** — [arXiv 2205.11784](https://arxiv.org/pdf/2205.11784)
- nvblox (Millane et al., ICRA 2024) is a GPU TSDF/ESDF mapper:
  - Up to 177x faster TSDF integration than CPU state of the art.
  - ESDF 31x faster than voxblox and 7x faster than FIESTA, with no accuracy loss. The v1 preprint gave a range of 7x-63x instead.
  - At 1 cm TSDF / 2 cm ESDF resolution it is still faster than voxblox at 10 cm.
  - **[verified]** — [arXiv 2311.00626](https://arxiv.org/pdf/2311.00626), [GitHub](https://github.com/nvidia-isaac/nvblox)
  - Note: nvblox is a mapper only. It consumes an external pose and provides no localization/ICP of its own **[inference from the paper's scope; confirm in docs]**.

**Why exploring does not bound drift**
- FAST-LIO2 deviated 4.2 m from an RTK-GNSS trajectory on a drone where registration was under-constrained **[verified, search summary]** — [Metal detector drone, arXiv 2212.07132](https://arxiv.org/pdf/2212.07132)
- On KITTI, where routes rarely revisit within the local map window, scan-to-map open loop still gives about 0.5% drift (the KISS-ICP numbers above) — [arXiv 2209.15397](https://arxiv.org/pdf/2209.15397)

### Inferences
- **Revisiting vs exploring.** Suppose a voxel was mapped at time t0 with pose error e0. When the drone later sees it again with accumulated error e1, registration pulls the estimate toward e0. Error is "bounded" only to the error at the time of mapping. While exploring, every observed surface was inserted with the current error, so registration only removes high-frequency jitter, and the error keeps growing at a reduced odometry rate. This is the core reason scan-to-map must be paired with:
  - loop closure / pose-graph optimization plus map deformation (BundleFusion re-integration, ElasticFusion deformation graph, submaps), or
  - a frozen prior map.
- **ZED specifics.** For a ZED in a room, KinectFusion-style projective data association against a raycast nvblox/voxblox TSDF is the cheapest frame-to-model path. Downsampling the 1280x720 depth to about 160x90-320x180 is the norm in these pipelines (KinectFusion used a coarse-to-fine pyramid **[not re-fetched]**). VGICP/small_gicp against a voxelized point map is the CPU-friendly alternative (30-70 Hz on a CPU at 15k points).
- **RGB-D accuracy numbers are bounded-workspace results.** The 1-2 cm ATE figures come from desk-scale TUM sequences with small motion. They should not be extrapolated to a drone flying corridors without loop closure.

### Gaps
- KinectFusion, ElasticFusion and colored-ICP original numbers (run time, ms per frame on their GPUs) were not re-read this session.
- No published benchmark found of nvblox, or of voxblox-based frame-to-model ICP, used as a localizer with a ZED.
- FAST-LIO2's T-RO end-to-end drift table was not extracted. The truncated text showed only 25.3 m RMSE on utbm_8 with a 2000 m map.

---

## Q2. Degeneracy detection and degeneracy-aware registration (only correct observable directions)

### Takeaway
Linearize the point-to-plane cost and eigen-decompose the 6x6 Hessian J^T J. Analyse the rotation and translation blocks separately, because their units and scales differ. Treat eigen-directions with too little information as unobservable and, in those directions, keep the prior (odometry or VIO) instead of the ICP update. The most thorough 2024-2025 field study, Tuna et al., finds:
- Active mitigation is needed; plain point-to-plane and robust kernels alone break the map.
- Equality-constrained (hard) updates along degenerate directions are the most consistent choice when no tuning is possible.
- Nonlinear regularization is the most accurate but about 6x slower.
- Every method depends on a good motion prior.

### Cited Findings
**Zhang, Kaess, Singh (ICRA 2016, pp. 809-816)**
- Identifies degenerate directions from the constraint geometry and solves the optimization only partially, in the well-conditioned directions. This is the "solution remapping" approach. It was demonstrated on 6-DOF camera+lidar ego-motion in feature-poor or geometrically sparse scenes **[verified]** — [CMU RI page](https://www.ri.cmu.edu/publications/on-degeneracy-of-optimization-based-state-estimation-problems), [PDF](https://frc.ri.cmu.edu/~zhangji/publications/ICRA_2016.pdf)
- Detection uses the minimum Hessian eigenvalue **[verified, as summarized]** — [Tuna et al. 2408.11809](https://arxiv.org/html/2408.11809v1)
- X-ICP sets Zhang's eigenvalue threshold empirically to 120 for all its experiments, except the Opfikon Park dataset where it compares several values. It criticizes the method for needing environment-specific tuning, and because one scalar threshold cannot fit both translation and rotation scales **[verified]** — [ar5iv 2211.16335](https://ar5iv.labs.arxiv.org/html/2211.16335)
- Hinduja et al. (IROS 2019) use a relative condition number instead **[verified, as summarized]** — [Tuna et al. 2408.11809](https://arxiv.org/html/2408.11809v1)

**X-ICP (Tuna, Nubert, Nava, Khattak, Hutter; IEEE T-RO 2023; arXiv 2211.16335 v1 Nov 2022, v4 Feb 2024)**
- Localizability detection uses scan-to-map point and normal correspondences to measure contribution strength along each principal direction. Each eigen-direction is labelled `full`, `partial`, or `none`.
- Thresholds:
  - κ1 = 250 is the lower bound for `full`, illustrated as at least 250 perfectly aligned pairs.
  - κ2 = 180 is the boundary between `partial` and `full`.
  - κ3 = 35 is the boundary between `partial` and `none`.
  - The noise filter κf is cos 80° for a VLP-16 and cos 60° for an OS0-128. The strong-alignment cutoff is cos 45°.
  - The same κ values are used across all environments and sensors.
- Mitigation:
  - `none`: the update in that direction is constrained to 0.
  - `partial`: the strongest-contributing correspondences are re-sampled to solve a small least-squares problem for the constraint value.
  - Constraints are imposed as Cx = d through Lagrange multipliers and solved by SVD.
- The pipeline runs at 5 Hz scan-to-map on an i7-9750H, with leg odometry as the prior.
- Simulation results:
  - Tunnel: Zhang wrongly flagged 3 directions, while X-ICP flagged 1.
  - In the combined corridor/open-area test (246 m), Hinduja was over-pessimistic and leaned almost entirely on the prior, and Zhang was over-optimistic about rotation, which broke the map.
  - **[verified]** — [ar5iv 2211.16335](https://ar5iv.labs.arxiv.org/html/2211.16335), [ETH Research Collection](https://www.research-collection.ethz.ch/handle/20.500.11850/641538)
- A simplified variant, Xs-ICP, drops the `partial` category and categorizes only in the first ICP iteration **[verified]** — [arXiv 2211.16335](https://arxiv.org/pdf/2211.16335)

**"Informed, Constrained, Aligned" (Tuna et al., arXiv 2408.11809, Aug 2024, v3 Jul 2025): a field study of mitigation methods using X-ICP detection for all**
- Methods compared:
  - Cauchy kernel (κ = 1)
  - Inequality-constrained ICP (ε = 0.0014, rotation bound ε/2)
  - Equality-constrained ICP
  - Linear Tikhonov (λ = 440)
  - Nonlinear Tikhonov via Levenberg-Marquardt (λ = 675)
  - Prior-only
  - Zhang solution remapping
  - Truncated SVD (degenerate eigenvalues set to 1e-4)
  - Plain point-to-plane
- Rotation and translation Hessian blocks are eigen-decomposed separately.
- **[verified]** — [arXiv 2408.11809](https://arxiv.org/html/2408.11809v1)
- Ulmberg tunnel (mean RTE / ATE / ICP cost):

  | Method | RTE [m] | ATE [m] | Cost [ms] |
  |---|---|---|---|
  | Eq. Con. | 0.039 | 1.10 | 18.95 |
  | Ineq. Con. | 0.033 | 1.21 | 19.13 |
  | Zhang | 0.0383 | 1.125 | 18.90 |
  | TSVD | 0.0388 | 1.11 | 18.95 |
  | Plain point-to-plane | 0.073 | 2.90 | 16.96 |
  | Prior only | 0.056 | 1.54 | 10.24 |
  | NL-Reg | 0.035 | 1.097 | 80.14 |
  | Cauchy | 0.050 | 1.76 | 18.33 |

  **[verified]** — [same](https://arxiv.org/html/2408.11809v1)
- ANYmal forest, ATE: Eq. Con. 0.490 m, Ineq. Con. 0.405 m, Zhang 0.372 m, TSVD 0.542 m, plain point-to-plane 2.62 m, NL-Reg 0.364 m (59.86 ms vs about 10 ms for the others) **[verified]**
- ANYmal dynamic simulation, APE translation: Eq. Con. 0.0835 m vs plain point-to-plane 2.485 m and Zhang 0.658 m **[verified]**
- Conclusions:
  - Plain point-to-plane and Cauchy produced broken maps in every experiment.
  - Global registration (Quatro, FGR) is not a fix, because degeneracy is an absence-of-inliers problem rather than an outlier problem.
  - Hard constraints added before or during the optimization beat corrections applied afterward.
  - Recommendations: with no tuning, Eq. Con.; with limited compute and tuning, Ineq. Con.; with compute available, NL-Reg; for simplicity, TSVD.
  - Every method depends on a good motion prior.
  - **[verified]** — [same](https://arxiv.org/html/2408.11809v1)

**Newer (2024-2026)**
- Probabilistic degeneracy detection for point-to-plane (Hatleskog & Alexis, NTNU; IEEE RA-L, arXiv 2410.10784, v2 Feb 2025) propagates point and normal noise into Hessian noise, then estimates the probability that each direction is degenerate. Updates in degenerate directions are smoothly attenuated, and parameters come from the sensor datasheet rather than hand tuning. Tested on LiDAR only; code at github.com/ntnu-arl/drpm **[verified]** — [arXiv 2410.10784](https://arxiv.org/abs/2410.10784)
- GenZ-ICP (Lee, Lim, Han; RA-L 2024) adaptively weights point-to-plane against point-to-point by local geometry, to avoid ill-posed corridor problems **[verified, abstract only, no numbers]** — [arXiv 2411.06766](https://arxiv.org/abs/2411.06766)
- LP-ICP (arXiv 2501.02580, Jan 2025) mixes point-to-line and point-to-plane, runs localizability analysis on both, and applies soft and hard constraints **[verified, abstract-level]** — [arXiv 2501.02580](https://arxiv.org/html/2501.02580v3)
- "Degenerate in Whose Frame?" (Zhang et al., arXiv 2608.15532, 16 Aug 2026, submitted to RA-L; preprint):
  - The point-to-plane information matrix transforms by congruence under a body-frame change. Nullity is preserved, but per-axis labels and thresholded eigenvalues are not. In a noise-free circular tunnel, moving the origin 1 m changes which DOFs are flagged.
  - Proposes the generalized eigenproblem Hv = λMv with M = Σ JᵢᵀJᵢ (a point-displacement metric). Its eigenvalues are dimensionless and invariant to frame, unit and scene scale.
  - On 365 frame pairs, the remapping correction differs between frame choices on 44.5-69.5% of pairs (median 0.7-4.0 mm, maximum 0.87 m).
  - **[verified]** — [arXiv 2608.15532](https://arxiv.org/pdf/2608.15532)

### Inferences
- **Geometry primer for a narrow-FOV depth camera indoors** (standard point-to-plane rank argument, not from a specific source):
  - Single wall or floor (one plane, normal n): constrains 1 translation (along n) and 2 rotations (about axes perpendicular to n). It leaves 2 translations plus rotation about n unobservable.
  - Wall plus floor: constrains 2 translations and 3 rotations. Translation along the line where the planes meet is free.
  - Corridor (two walls plus floor): translation along the corridor axis is free.
  - A corner with 3 non-parallel planes: fully constrained.
  - Because the ZED sees a frustum rather than 360°, it hits these cases far more often than LiDAR. Looking at one wall is common, so detection is essential, not optional.
- **Recipe that maps onto the evidence.**
  1. Build H = JᵀJ from point-to-plane residuals weighted by 1/σ² (Q3).
  2. Eigen-decompose the rotation and translation blocks separately (Tuna), or use the frame-invariant generalized eigenproblem from 2608.15532.
  3. Classify directions with count-based thresholds in the X-ICP style, or probabilistically (Hatleskog & Alexis). The probabilistic version suits stereo because its noise model is explicit.
  4. Solve with an equality constraint fixing the update to 0 along degenerate directions (the "Eq. Con." recommended when no tuning is possible).
  5. Pass only the observable sub-space to the EKF, or inflate covariance along degenerate eigenvectors (Q4).
- **X-ICP's κ thresholds do not transfer directly.** They are counts of LiDAR correspondences. A downsampled ZED frame has a different point budget (for example about 10k-30k points at 160x90-320x180), so the counts would need re-scaling. The noise-derived probabilistic approach or the dimensionless generalized eigenvalue are better starting points for a depth camera.
- **Colored ICP or photometric terms** (ElasticFusion, colored ICP) can add constraints along textured planes. That is a degeneracy mitigation specific to RGB-D/stereo that LiDAR lacks. It will not help on white walls, where stereo depth also fails.

### Gaps
- X-ICP's real-world quantitative tables (Seemühle, Rümlang, Opfikon) were truncated in the fetched text.
- No paper was found that applies X-ICP-style localizability to stereo depth or RGB-D cameras specifically.
- The quantitative results of LP-ICP and GenZ-ICP were not extracted.

---

## Q3. Using stereo depth (noise ∝ z²) for ICP: weighting, range limits, results with ZED/RealSense on drones

### Takeaway
Stereo depth error grows with z² divided by (focal length × baseline). Stereolabs states roughly 1% of distance at close range rising to about 9% at maximum range, and worse on textureless or reflective surfaces. The ICP residuals and TSDF fusion weights should therefore be weighted by 1/σ_z² (or by the full anisotropic covariance), and the range used for registration should be capped well inside the 8 m useful range. Published drone results that use stereo frame-to-model ICP as the main localizer are scarce. Most drone systems use stereo depth for mapping and VIO for pose.

### Cited Findings
- Stereolabs says depth resolution scales with distance squared times a constant, with accuracy about 1% of distance at close range and up to about 9% at maximum range **[verified]** — [Stereolabs Depth Sensing docs](https://www.stereolabs.com/docs/depth-sensing). Stereolabs support describes the far-range error more loosely, as "a few percent" (a discrepancy) **[verified]** — [Stereolabs support article](https://support.stereolabs.com/hc/en-us/articles/1500008533841-For-the-depth-sensing-what-is-the-range-for-the-ZED-cameras-in-terms-of-measuring-distances-and-the-accuracy-of-the-detection)
- ZED 2i and ZED X baselines are 120 mm:
  - ZED X 2.2 mm lens: 0.3-20 m
  - ZED X 4 mm lens: 1.0-35 m
  - ZED 2i 4 mm lens: 1.5-35 m
  - Accuracy degrades on textureless, white or reflective surfaces.
  - **[verified]** — [Stereolabs support](https://support.stereolabs.com/hc/en-us/articles/1500008533841-For-the-depth-sensing-what-is-the-range-for-the-ZED-cameras-in-terms-of-measuring-distances-and-the-accuracy-of-the-detection), [Depth docs](https://www.stereolabs.com/docs/depth-sensing)
- Stereo depth error falls linearly with baseline and grows quadratically with distance (forum statement, consistent with the triangulation formula) **[verified, forum, low authority]** — [Stereolabs community](https://community.stereolabs.com/t/long-range-stereo-30-m-with-zed-x-one-custom-rigs-looking-for-real-world-experience/11495)
- Noise in structured-light and active-stereo depth cameras grows with the square of range. TSDF fusion weights should reflect per-observation uncertainty, otherwise distant noisy points swamp near precise ones **[verified]** — [arXiv 1505.01936](https://arxiv.org/pdf/1505.01936), [Uncertainty-aware mapping, arXiv 2507.10991](https://arxiv.org/pdf/2507.10991)
- An underwater stereo mapping paper sets TSDF weights from stereo matching confidence rather than from distance alone **[verified]** — [arXiv 2507.10991](https://arxiv.org/pdf/2507.10991)
- A 2014 study adapted KinFu's distance-aware weighting to outdoor stereo data, where IR depth cameras fail in sunlight **[verified]** — [SciTePress 2014](https://www.scitepress.org/Papers/2014/49015/49015.pdf)
- Probabilistic degeneracy detection can take sensor noise parameters straight from the datasheet **[verified]** — [arXiv 2410.10784](https://arxiv.org/abs/2410.10784)

### Inferences
- **Worked example** (formula σ_z ≈ z²·σ_d / (f·b); the parameters are assumptions, not ZED datasheet values). Take HD720 with f ≈ 700 px, b = 0.12 m (so f·b ≈ 84 px·m), and disparity noise σ_d ≈ 0.25 px:

  | Range z | σ_z |
  |---|---|
  | 1 m | ≈ 3 mm |
  | 2 m | ≈ 1.2 cm |
  | 4 m | ≈ 4.8 cm |
  | 8 m | ≈ 19 cm |

  This is consistent with the stated 1% near and about 9% far. The information weight 1/σ² falls by about 4000x between 1 m and 8 m. Points beyond about 4-5 m contribute little and mainly add bias from edge fattening and smoothing, so a registration range cap of about 4-5 m (with the map still built to 8 m at low weight) is a reasonable starting point.
- **The noise is anisotropic** (mostly along the viewing ray). Point-to-plane on walls seen obliquely is hit hardest. GICP/VGICP lets each point carry the anisotropic ray-aligned covariance Σ = R·diag(σ_x², σ_y², σ_z²)·Rᵀ instead of the default isotropic plane-fitted covariance. small_gicp accepts user-supplied covariances **[library capability: inference, confirm in API]**.
- **ZED-specific pitfalls.**
  - The SDK's depth confidence and texture-confidence thresholds, and depth filling (the "NEURAL" or "ULTRA" modes), produce smooth hallucinated surfaces on textureless walls. These can look strongly planar to ICP while being wrong.
  - Disable fill modes for registration, or mask by confidence.
  - Combine with degeneracy detection so that a white wall with filled depth does not falsely pin an axis.

### Gaps
- No peer-reviewed paper was found that reports ATE for frame-to-model ICP with a ZED or RealSense on a drone. Searches returned only patents and generic RGB-D work.
- No exact ZED HD720 disparity-noise σ_d figure was found in Stereolabs docs. The worked example's parameters are assumptions.
- RealSense D4xx RMS-error formulas (Intel white paper) were not retrieved this session.

---

## Q4. Fusing map-relative corrections into a flight-controller EKF (PX4/ArduPilot) and published drone drift results (SubT teams)

### Takeaway
Feeding a map-relative pose into PX4 EKF2 as external vision (EV) is mechanically simple. The requirements are a message rate of about 30-50 Hz, correct EKF2_EV_DELAY, a choice of fused components through EKF2_EV_CTRL, and per-measurement covariance. The DARPA SubT teams instead ran LiDAR-centric scan-to-map odometry inside their own estimators, with health monitoring and multi-modal fallbacks (CERBERUS CompSLAM, CoSTAR LOCUS 2.0). Drone-specific drift numbers from those teams were not found in this session.

### Cited Findings
- PX4 EV fusion:
  - `EKF2_EV_CTRL` selects horizontal position, vertical position, velocity and yaw fusion.
  - `EKF2_EV_DELAY` is the vision delay relative to the IMU. It can be zero with perfect time sync but usually needs tuning from logs.
  - If the rate is too low, EKF2 will not fuse; stream at about 30-50 Hz.
  - Reboot after changing these parameters.
  - **[verified]** — [PX4 docs: Using Vision or Motion Capture Systems](https://docs.px4.io/v1.14/en/ros/external_position_estimation)
- CERBERUS (Tunnel/Urban circuits paper, Field Robotics 2022) used an EKF fusing visual, thermal and inertial data, with LiDAR odometry on top. Odometry health was checked through covariance growth using the D-optimality criterion **[verified]** — [arXiv 2201.07067](https://arxiv.org/pdf/2201.07067)
- CompSLAM (CERBERUS, arXiv 2505.06483, 2025) is a hierarchical, multi-modal framework that gets resilience from redundancy across modalities. It ran on all aerial, legged and wheeled CERBERUS robots in their competition-winning final run. It was evaluated on a 740 m quadruped dataset (not aerial) **[verified]** — [arXiv 2505.06483](https://arxiv.org/html/2505.06483v1)
- CoSTAR LOCUS 2.0 (RA-L 2022) uses GICP scan-to-map with a sliding-window map and was evaluated in degenerate, dusty and dark environments **[verified]** — [arXiv 2205.11784](https://arxiv.org/pdf/2205.11784). The NeBula addendum (arXiv 2504.13461, 2025) keeps LOCUS 2.0 for larger environments **[verified, snippet]** — [arXiv 2504.13461](https://arxiv.org/pdf/2504.13461)
- Indoor drift-free depth-camera localization against a prior map (Tao et al., IET Cyber-systems and Robotics, Mar 2023):
  - Depth-only odometry, plus registration of the point cloud to a prior, cross-source map by 3D particle filtering.
  - The two results are fused, so the system tolerates an incomplete map.
  - **[verified, abstract]** — [DOAJ](https://doaj.org/article/a1c1889dfa334206add77b0b5f762b29)
- A MAV inspection system for GPS-denied construction sites (arXiv 2408.06030, 2024) runs an ESKF on LiDAR and IMU. It relocalizes by registering the live local map to a prior map **[verified, snippet]** — [arXiv 2408.06030](https://arxiv.org/pdf/2408.06030)

### Inferences
- **Practical PX4 integration** for a ZED-on-drone stack:
  1. Publish the corrected pose on `/mavros/vision_pose/pose_cov` or as ODOMETRY at 30 Hz, timestamped at image capture.
  2. Set `EKF2_EV_DELAY` from the log (the PX4 docs method).
  3. Along degenerate eigenvectors from Q2, inflate the covariance, or skip fusion of that axis via `EKF2_EV_CTRL` when it aligns with a world axis such as corridor-along-x.
  4. When the map-relative correction makes a discrete jump (relocalization or loop closure), increment the odometry `reset_counter` so EKF2 treats it as a reset, not an innovation spike.
  - The `reset_counter` and covariance-handling behaviour of PX4 were not verified this session; check the VehicleOdometry message and EKF2 source.
- **Feedback-loop risk.** If the VIO that seeds ICP is the same estimator the EKF fuses, and ICP output goes back into the EKF as EV, there is double counting and a feedback loop. Either feed ICP the raw VIO (not the EKF output) as the prior and fuse the ICP result as the only EV source, or fuse VIO and ICP as separate, independent sources (not possible in PX4 EKF2 with a single EV slot). The SubT teams avoided this by owning the full estimator (CompSLAM, LOCUS).

### Gaps
- CERBERUS, CoSTAR and Explorer (CMU/OSU, Super Odometry) aerial drift numbers were not extracted. The MIT (e.g. Kimera-Multi) and ETH flying-robot SubT drift numbers were not found this session.
- No published system was found that fuses depth-camera frame-to-model ICP into PX4 EKF2 as EV and reports drift numbers.

---

## Q5. Global / multi-session relocalization against a prior map; place recognition for depth in repetitive rooms

### Takeaway
Relocalizing against a prior map needs a global initial guess first (place recognition or global registration), because local ICP converges only within a small basin. Scan Context and Scan Context++ are the reference LiDAR descriptors, but they assume 360° egocentric scans. The 2024 field study shows global registration (FGR, Quatro) cannot solve degeneracy, so in repetitive rooms or halls a candidate must be validated geometrically and checked for degeneracy before it is accepted.

### Cited Findings
- Scan Context (G. Kim & A. Kim, IROS 2018, Madrid) is an egocentric polar-grid descriptor for 3D point clouds. It searches in two stages, with a ring-key KD-tree for candidate proposal **[verified]** — [GitHub gisbi-kim/scancontext](https://github.com/gisbi-kim/scancontext)
- Scan Context++ (Kim, Choi, Kim; IEEE T-RO, arXiv 2109.13494, 2021) is robust to rotation and lateral offset. It does topological retrieval followed by 1-DOF semi-metric localization **[verified]** — [arXiv 2109.13494](https://arxiv.org/pdf/2109.13494.pdf), [scancontext_tro](https://github.com/gisbi-kim/scancontext_tro)
- Global registration (Quatro, FGR) failed to recover rotation in degenerate tunnel and simulation scenes. Degeneracy is an absence of inliers, not an outlier problem **[verified]** — [arXiv 2408.11809](https://arxiv.org/html/2408.11809v1)
- BundleFusion recovers from tracking failure by relocalizing against globally optimized frames using sparse features **[verified, abstract]** — [arXiv 1604.01093](https://arxiv.org/abs/1604.01093)
- Tao et al. 2023 used a 3D particle filter on point-cloud-to-prior-map registration, indoors, in low light **[verified, abstract]** — [DOAJ](https://doaj.org/article/a1c1889dfa334206add77b0b5f762b29)

### Inferences
- **Scan Context fit.** Scan Context's polar grid assumes a full 360° sweep, which a ZED frustum (about 110° horizontal for ZED 2i/X with the 2.2 mm lens [not verified]) does not provide. For a forward stereo camera the closer analogue is:
  - visual place recognition on the RGB image (BoW/DBoW2 or a learned descriptor), then
  - depth ICP for metric verification, or
  - Scan Context run on a local submap accumulated over about 1-2 s of yaw.
- **Repetitive rooms** (identical offices, symmetric halls). Accept a relocalization only if all of these hold:
  - the ICP residual or inlier ratio passes a threshold;
  - the Hessian is non-degenerate (Q2);
  - the candidate is consistent with the odometry over several frames (a temporal or particle-filter vote, as in Tao et al.).
  - Otherwise ambiguity aliasing will produce confident wrong jumps.
- **Multi-session.** Store the frozen prior map with keyframes (pose, RGB, depth) so that place recognition works on images and metric refinement works on geometry.

### Gaps
- Scan Context recall numbers were not extracted.
- No evaluation was found of depth-only place recognition for narrow-FOV stereo cameras in repetitive indoor rooms.

---

## Q6. Pitfalls: map corrupted by its own drift, sliding windows and submaps, when to freeze the map

### Takeaway
A map built on a drifting pose bakes the drift into the geometry. Later frame-to-model registration then faithfully locks onto a bent map, which gives smooth local consistency with global error. Systems manage this in one of four ways:
- a bounded local window that discards old geometry (KISS-ICP, FAST-LIO2 cube, LOCUS 2.0 sliding window), which limits damage but loses revisit corrections;
- submaps plus pose-graph re-alignment (voxgraph-style), or full re-integration (BundleFusion);
- non-rigid deformation (ElasticFusion);
- a map frozen after a good survey run (often with loop closure), then pure localization.

### Cited Findings
- BundleFusion re-estimates the 3D model in real time as global poses change, which avoids a map frozen with old drift **[verified, abstract]** — [arXiv 1604.01093](https://arxiv.org/abs/1604.01093)
- LOCUS 2.0 uses a sliding-window map for bounded memory **[verified]** — [arXiv 2205.11784](https://arxiv.org/pdf/2205.11784)
- FAST-LIO2 keeps a moving local cube map (default 1000 m) in the ikd-tree and deletes points outside it **[verified]** — [ar5iv 2107.06829](https://ar5iv.labs.arxiv.org/html/2107.06829)
- A drone system for disaster sites (arXiv 2103.11742, 2021) limits drift damage by discarding old range measurements, removing stale obstacle data **[verified, snippet]** — [arXiv 2103.11742](https://arxiv.org/pdf/2103.11742)
- Degeneracy-aware methods perform well only with a good motion prior **[verified]** — [arXiv 2408.11809](https://arxiv.org/html/2408.11809v1)
- ElasticFusion applies non-rigid deformation to the surfel map on loop closure **[not re-fetched]** — [RSS 2015](http://www.roboticsproceedings.org/rss11/p01.pdf)

### Inferences
- **Self-reinforcement.**
  - In a degenerate corridor, the along-axis error integrated into the TSDF while flying out is "confirmed" by the map on the way back, unless something non-degenerate (the corridor end, a door frame) is in view.
  - Do not integrate frames into the map while the registration is degenerate in some direction, or integrate them at reduced weight. Otherwise unconstrained motion smears the map.
  - Gate integration on a good registration (inlier ratio, residual RMS) as well as on non-degeneracy.
- **Freeze policy for repeated indoor missions.**
  1. Survey: build the map with loop closure (or BundleFusion-style re-integration), then freeze it.
  2. Mission: localize to the frozen map with degeneracy-aware ICP, and keep a separate live local map for obstacle avoidance only.
  - This turns "bounded only when revisiting" into "bounded everywhere the survey covered", at the cost of failing on changed geometry (moved furniture). Mitigate that with robust kernels and an inlier-ratio gate.
- **Exploration flights** with no prior map need submaps:
  - Use keyframe submaps of about 5-10 m of travel.
  - Register to the current and the most recent submap, and re-anchor submaps on loop closure.
  - Treat cross-submap revisits as loop closures rather than as direct ICP corrections, so that a drifted old submap does not yank the pose.
- **Timing hazard.** Keep the map frame pose used for integration consistent with the pose that is corrected afterwards. For example, if the EKF output, after the EV correction, is also used to integrate depth into nvblox, every correction jump shifts newly integrated geometry relative to the old geometry. That creates doubled walls, which then corrupt the next registration. Integrate with the same pose that the ICP produced, or with a smoothed one.

### Gaps
- No quantitative study was found of map-corruption effects (for example drift-baked TSDF error vs. ICP lock-on error) for depth cameras on drones.
- Voxgraph (Reijgwart et al., RA-L 2020) submap results were not retrieved this session.
