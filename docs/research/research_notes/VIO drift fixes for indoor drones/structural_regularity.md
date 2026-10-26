# Structural regularity (Manhattan / Atlanta / planar) constraints for drift-free VIO in indoor rooms

Scope: methods that use dominant wall/floor directions and planes to remove rotational (yaw) drift and give wall-relative position, for a drone with a ZED Mini (stereo depth) and IMU in box-shaped rooms and warehouses. Research date: 2026-10-26. Most core papers are 2015-2021 (older; marked by year). Numbers below were read from the papers' own tables unless noted otherwise.

## 1. Manhattan-frame / drift-free rotation from depth normals or vanishing directions (RGB-D VO/SLAM)

### Takeaway
The finding repeated across these papers is that rotation drift is the main source of VO position error. Tracking the Manhattan frame (MF) from depth-image surface normals, plus image lines where available, gives an absolute, drift-free rotation, typically with errors of about 0.2 deg on synthetic ICL-NUIM and 3 deg or less on real data fused with an IMU. With rotation fixed, translation becomes much easier. The main weakness is degeneracy when only one plane or MF axis is visible. LPVO, ManhattanSLAM and Structure-SLAM add lines or fall back to feature tracking to cope with it.

### Cited Findings
**Straub, Bhandari, Leonard, Fisher, "Real-time Manhattan World Rotation Estimation in 3D" (RTMF), IROS 2015 (older)**
- Three algorithms (direct tangent-space Gaussian, approximate, and vMF-based) estimate the full 3D rotation to the MW from depth-image surface normals in as little as 20 ms. The paper explicitly frames it as a "structure compass" for estimating gyro/odometry bias. — [Straub et al. 2015 PDF](https://jstraub.github.io/download/straub2015rtmf_web.pdf)
- Timing (Intel i7-3940XM + NVIDIA Quadro K2000M GPU, 640x480 depth): vMF-based 19.8 ms/frame on average, approximate method about 12 ms slower, direct method 105 ms (not real-time). The vMF and approximate methods run at 30 Hz camera rate. — [Straub et al. 2015](https://jstraub.github.io/download/straub2015rtmf_web.pdf)
- Accuracy against Vicon (Xtion + Microstrain 3DM-GX3 IMU, waved in front of a wall with a rectangular pillar):
  - 90 s sequence: vMF RMSE 6.36 deg, approximate 4.92 deg, IMU-only 3.91 deg; fused with IMU in a quaternion EKF, 3.05 deg (vMF) and 3.28 deg (approximate).
  - 4.5 min sequence: RTMF alone below 3.4 deg with zero drift, IMU-only 8.50 deg (drifting), fused below 2.8 deg.
  - Source: [Straub et al. 2015](https://jstraub.github.io/download/straub2015rtmf_web.pdf)
- Failure mode: "large angular deviations occur when there are surface normals on only one or two MF axes for several frames". The gyro carries the estimate through these periods and RTMF removes gyro bias, which the authors call complementary. — [Straub et al. 2015](https://jstraub.github.io/download/straub2015rtmf_web.pdf)
- 90 deg ambiguity: the MF is tracked consistently as long as inter-frame rotation is under 45 deg about any axis. It was tracked through 90 deg corridor turns at 50 deg/s while running. — [Straub et al. 2015](https://jstraub.github.io/download/straub2015rtmf_web.pdf)
- Large-scale test (Turtlebot, MIT Killian Court hallways): one hallway section is not aligned with the global MW, so the estimate locks to that local MW. Where there is no nearby structure, the estimate "is off due to the lack of data". The authors conclude the MW should be treated as a local property. — [Straub et al. 2015](https://jstraub.github.io/download/straub2015rtmf_web.pdf)
- Normal extraction pipeline: guided filter (edge-preserving, O(1) per pixel via integral images), then the point cloud, then Sobel gradients p_u and p_v, with normal = p_u x p_v. — [Straub et al. 2015](https://jstraub.github.io/download/straub2015rtmf_web.pdf)
- The follow-up journal paper is "The Manhattan Frame Model: Manhattan World Inference in the Space of Surface Normals" (Straub et al., TPAMI 2018). It covers mixtures of Manhattan frames for scenes with several rotated MWs. — [ResearchGate entry](https://www.researchgate.net/publication/313260449_The_Manhattan_Frame_Model_-_Manhattan_World_Inference_in_the_Space_of_Surface_Normals)

**Kim, Coltin, Kim, OPVO: "Visual Odometry with Drift-Free Rotation Estimation Using Indoor Scene Regularities", BMVC 2017 (older; it is BMVC, not ICRA)**
- Hybrid VO. Drift-free rotation comes from tracking the MF with an SO(3)-constrained mean shift on surface normals. Translation then minimizes a "de-rotated reprojection error" of tracked features. — [OPVO PDF](http://brian.coltin.org/pub/kim2017visual.pdf); [code](https://github.com/PyojinKim/OPVO)
- The motivating experiment found that if rotation is known (ground truth), feature VO drift largely disappears, so "drift of the rotation estimate is the main source of position inaccuracy in VO". — [OPVO PDF](http://brian.coltin.org/pub/kim2017visual.pdf)
- Normals are computed from u/v tangential vectors averaged with integral images, for speed and noise reduction. — [OPVO PDF](http://brian.coltin.org/pub/kim2017visual.pdf)
- Limitation: it needs at least two orthogonal planes visible at all times, plus points with depth. It fails when only a single plane is visible, as stated in the LPVO paper. — [LPVO PDF](http://brian.coltin.org/pub/kim2018low.pdf)

**Kim, Coltin, Kim, LPVO: "Low-Drift Visual Odometry in Structured Environments by Decoupling Rotational and Translational Motion", ICRA 2018, pp. 7247-7253 (older)**
- Fuses vanishing directions from image lines (Gaussian sphere, from at least two parallel lines) with depth surface normals, using SO(3)-constrained mean shift. It needs only one plane plus one pair of lines parallel to an MW axis. Translation uses points with and without depth. — [LPVO PDF](http://brian.coltin.org/pub/kim2018low.pdf); [code (MATLAB)](https://github.com/PyojinKim/LPVO)
- ICL-NUIM ATE RMSE averages: LPVO 0.04 m, ORB 0.21, DEMO 0.36, DVO 0.35, MWO 0.60, OPVO 0.06. MWO and OPVO fail on lr-kt0 and of-kt2 when only one plane is visible. — [LPVO PDF](http://brian.coltin.org/pub/kim2018low.pdf)
- Average rotation error on ICL-NUIM: LPVO 0.22 deg, ORB 1.63, DEMO 3.15, DVO 8.12, MWO 0.22, OPVO 0.21 deg. LPVO, MWO and OPVO "drift less than 0.5 degrees". — [LPVO PDF](http://brian.coltin.org/pub/kim2018low.pdf)
- TUM RGB-D ATE (m), LPVO vs ORB vs OPVO:

  | Sequence | LPVO | ORB | OPVO |
  |---|---|---|---|
  | fr3 struc_notex_far | 0.07 | 0.28 | 0.13 |
  | fr3 struc_notex_near | 0.08 | 0.63 | 0.16 |
  | fr3 large_cabinet | 0.28 | 0.47 | 0.51 |
  | fr3 longoffice (imperfect structure) | 0.19 | 0.02 | failed |
  | fr3 struc_tex_far (textured) | 0.17 | 0.03 | 0.18 |

  ORB wins in textured or imperfectly structured scenes. Source: [LPVO PDF](http://brian.coltin.org/pub/kim2018low.pdf)
- Loop drift (final error / distance): TAMU Corridor-A (88 m, four pure rotations, one single-plane segment) under 0.3%; author corridors of 93 m under 0.2% and 120 m under 0.7%. Runs at 13.5 Hz in unoptimized MATLAB on an i5 at 3.2 GHz. — [LPVO PDF](http://brian.coltin.org/pub/kim2018low.pdf)

**Kim, Coltin, Kim, L-SLAM: "Linear RGB-D SLAM for Planar Environments", ECCV 2018 (the user's list says ICRA 2018; the PDF and search show ECCV) (older)**
- With rotation fixed by LPVO (about 0.2 deg average error), SLAM becomes a linear Kalman filter. Each orthogonal plane is one scalar (offset), so the state is 3+n, compared with 7+7n to 12+10n in other EKF-SLAMs. The process model is the LPVO 3-DoF translation and the measurement is the camera-to-plane distance. — [L-SLAM PDF](http://brian.coltin.org/pub/kim2018linear.pdf)
- ICL-NUIM (noisy) average ATE: L-SLAM 0.038 m, ORB-SLAM2 0.057, DVO-SLAM 0.197, CPA-SLAM 0.028 (GPU), KDP-SLAM 0.053, LPVO 0.046. Runs above 20 Hz on CPU (i5). 120 m corridor final drift under 0.1% with no loop closure. — [L-SLAM PDF](http://brian.coltin.org/pub/kim2018linear.pdf)

**Globally optimal MF estimation (initialization / re-acquisition)**
- Joo, Oh, Kim, Kweon: CVPR 2016 "Globally Optimal Manhattan Frame Estimation in Real-time", extended in TPAMI 2019 vol. 41(3), pp. 682-696. Branch-and-bound inlier maximization over rotations, with bounds computed on the extended Gaussian image (constant-time bounds), giving guaranteed global optimality in near real time. Extensions cover multiple MFs and VP clustering. — [CVF open access](https://openaccess.thecvf.com/content_cvpr_2016/html/Joo_Globally_Optimal_Manhattan_CVPR_2016_paper.html); [TPAMI record](https://koasas.kaist.ac.kr/handle/10203/251481)
- A 2022 Journal of Field Robotics paper, "A fast Manhattan frame estimation method based on normal vectors" (Zhang et al.), exists. A citing paper notes that RTMF meets real time with a GPU but "is sensitive to initial conditions and cannot guarantee the global optimal result". — [Wiley JFR](https://onlinelibrary.wiley.com/doi/abs/10.1002/rob.22064); summary via search of [Straub record](https://www.researchgate.net/publication/308850552_Real-time_manhattan_world_rotation_estimation_in_3D)

**Structure-SLAM, ManhattanSLAM and related monocular/RGB-D SLAM**
- Structure-SLAM (Li, Brasch, Wang, Navab, Tombari), RA-L 2020. Monocular. CNN-predicted surface normals plus lines give drift-free rotation by spherical mean-shift under a weak Manhattan assumption. Translation comes from points and lines, then map-to-frame refinement. Claims better results than the state of the art on ICL-NUIM and TUM. — [arXiv 2008.01963](https://arxiv.org/abs/2008.01963)
- ManhattanSLAM (Yunus, Li, Tombari), ICRA 2021. RGB-D, built on ORB-SLAM2, GPLv3. Detects MFs from orthogonal plane pairs (mixture of MFs). Uses drift-free MF rotation only on frames where an MF is detected; otherwise falls back to point/line/plane feature tracking. — [arXiv 2103.15068](https://arxiv.org/abs/2103.15068); [code](https://github.com/razayunus/ManhattanSLAM)
  - ICL-NUIM average ATE: ManhattanSLAM 0.014 m, S-SLAM 0.040, RGBD-SLAM 0.017, ORB-SLAM2 0.023, SP-SLAM 0.020, L-SLAM 0.039. — [arXiv 2103.15068](https://arxiv.org/abs/2103.15068)
  - TUM fr3 structure sequences 0.012-0.040 m. On fr3 cabinet ORB-SLAM2 fails while ManhattanSLAM gets 0.023 m (L-SLAM 0.291 m).
  - On cluttered TUM fr1/fr2 sequences an MF was found in only 0-26 of 600-3,669 frames. Synthetic ICL frames had an MF most of the time (for example 1,203 of 1,510).
  - Source for both: [arXiv 2103.15068](https://arxiv.org/abs/2103.15068)
  - TAMU loop drift: Corridor-A 0.53 m with MF vs 0.77 m without MF vs 3.13 m ORB-SLAM2; Entry-Hall 0.39 vs 0.81 vs 2.22 m. Runs at about 15 Hz (67 ms tracking) on an i5-8250U CPU. — [arXiv 2103.15068](https://arxiv.org/abs/2103.15068)
- StructSLAM (Zhou, Zou, Pei, Ying, Liu, Yu). Published in IEEE Transactions on Vehicular Technology 64(4), 2015, not TRO (older). EKF monocular SLAM where "building structure lines" are parameterized by dominant directions, which carry global orientation and limit heading error. RAWSEEDS indoor with wheel odometry and no loop closure: about 0.79 m position error over 967 m. — [project page](https://drone.sjtu.edu.cn/dpzou/project/structslam/)
- Li, Yao, Bazin et al., "A Monocular SLAM System Leveraging Structural Regularity in Manhattan World", ICRA 2018, pp. 2518-2525 (older). A later TPAMI 2023 paper, "Hong Kong World", extends this to sloping directions. — [KAIST record](https://koasas.kaist.ac.kr/handle/10203/248908?mode=full); [Hong Kong World PDF](https://mpil.sookmyung.ac.kr/wp-content/uploads/2023/05/2023_TPAMI.pdf)
- Atlanta-world RGB-D: Joo, Kim, Hebert, Kweon, "Linear RGB-D SLAM for Atlanta World", ICRA 2020, later TPAMI 2022. One vertical direction plus a set of horizontal directions, in a linear formulation. — [KAIST EE page](https://ee.kaist.ac.kr/en/?p=118488)
- Newer VO variants:
  - MSC-VO (2021/22): RGB-D points and lines with Manhattan axes. — [arXiv 2111.03408](https://arxiv.org/abs/2111.03408)
  - Mixture-of-MF robust VO (Sensors 2022). — [MDPI](https://www.mdpi.com/1424-8220/22/22/8644)
  - GFS-VO (2024). — [arXiv 2403.01110](https://arxiv.org/html/2403.01110)
  - MonoSLAM with global structure optimization (2025), which notes that MW direction vectors are hard to put into a factor graph as a single primitive and uses co-planarity constraints instead. — [arXiv 2503.09296](https://arxiv.org/html/2503.09296v1)

### Inferences
- ICL-NUIM is rendered from a rigid Manhattan model, so its sub-degree rotation numbers are optimistic. ManhattanSLAM says this explicitly. Real-sensor numbers (Straub: 3-6 deg RMSE standalone, under 3 deg with IMU) are the realistic guide for a ZED Mini.
- The few MF-detected frames on cluttered TUM sequences in ManhattanSLAM show how often a strict MF detector will be silent in cluttered rooms. A warehouse with racks is likely somewhere between ICL and TUM fr1/fr2.

### Gaps
- I did not retrieve the TPAMI 2018 Manhattan Frame Model numbers or the CVPR 2018 "Indoor RGB-D compass from a single line and plane" (Kim et al.) numbers.
- OPVO's own tables were not extracted. OPVO numbers above come from the LPVO comparison tables.
- Structure-SLAM's ATE tables were not extracted.

## 2. Visual-inertial odometry with structural constraints (Manhattan/Atlanta lines, planes)

### Takeaway
In VIO the gain is mostly in heading (yaw), which is the IMU's unobservable direction.
- StructVIO (Atlanta world, structural lines) reduced mean loop drift from about 1% to 0.29% over 190-650 m indoor runs. Assuming a single Manhattan world in non-orthogonal buildings increased RMSE by 287%.
- Plane-aided VIO (ov_plane, PGD-VIO) helps when planes are tracked reliably. Gains are small in clutter: ov_plane barely improves on OpenVINS on CID-SIMS. RGB-D plane VIO with plane-map drift suppression (PGD-VIO) shows large gains.

### Cited Findings
**StructVIO (Zou, Wu, Pei, Ling, Yu), IEEE TRO 35(4):999-1013, Aug 2019 (older)**
- Method: MSCKF-style VIO. Structural lines are parameterized relative to local Manhattan worlds. Each local MW is detected on the fly, and its heading is a state variable refined over time, forming an Atlanta world (multiple MWs sharing gravity). — [arXiv 1810.06796](https://arxiv.org/abs/1810.06796)
- Long indoor tests: Project Tango tablet, 15 Hz images and 100 Hz IMU, 16 sequences of 190-650 m in three buildings, with ArUco-based end-point ground truth (about 2.8 cm vs Vicon).
  - Mean drift: StructVIO 0.292%, OKVIS 1.078%, VINS without loop closure 1.410%, Project Tango 6.180%, point-only 0.957%, point+line (no structure) 0.956%.
  - Median drift: StructVIO 0.176% vs 0.538-0.900% for the others.
  - Source: [arXiv 1810.06796](https://arxiv.org/abs/1810.06796)
- Adding generic lines without structural (MW) priors gave no gain (0.957% vs 0.956%). The gain comes from the heading prior. — [arXiv 1810.06796](https://arxiv.org/abs/1810.06796)
- Atlanta vs Manhattan: on the "Soft" and "Mech" buildings, which have oblique corridors, forcing a single Manhattan world raised RMSE by about 287% on average (for example Soft-03: 0.325 m Atlanta vs 3.352 m Manhattan). — [arXiv 1810.06796](https://arxiv.org/abs/1810.06796)
- EuRoC: large improvement in the box-like Machine Hall, but results similar to other methods in the cluttered, textured Vicon rooms. Even when no MW is detected, vertical lines still help by revealing gravity. Clutter can create spurious multiple MWs. — [arXiv 1810.06796](https://arxiv.org/abs/1810.06796)
- Failure modes: slanted walls give slanted lines, which are treated as outliers, so the system reverts to point-only VIO. It "may fail" in scenes with only slanted walls and little texture. — [arXiv 1810.06796](https://arxiv.org/abs/1810.06796)

**Planar VIO**
- ov_plane (Chen, Geneva, Peng, Lee, Huang), "Monocular Visual-Inertial Odometry with Planar Regularities", ICRA 2023, pp. 6224-6231. Built on OpenVINS (MSCKF). Monocular plane detection with no depth or neural network. Point-on-plane constraints apply to SLAM and MSCKF features, and long-lived planes are kept in the state, which allows "point-to-plane loop-closures". ROS 1. — [GitHub ov_plane](https://github.com/rpng/ov_plane); venue and pages via the [PGD-VIO references](https://arxiv.org/abs/2407.17709)
- PGD-VIO (Zhang, Tang, Xu, Wu, Ma), arXiv July 2024. RGB-D + IMU EKF with plane features in the state, plus graph-based drift detection that finds duplicated plane structures in the map and aligns them. — [arXiv 2407.17709](https://arxiv.org/abs/2407.17709)
  - CID-SIMS ATE (m, wheeled robot), OpenVINS → ov_plane → PGD-VIO:

    | Sequence | OpenVINS | ov_plane | PGD-VIO |
    |---|---|---|---|
    | Office 1 | 0.155 | 0.133 | 0.030 |
    | Floor3_1 | 0.833 | 0.655 | 0.112 |
    | Floor14_2 | 1.750 | 1.704 | 0.163 |
    | Office 2 (ov_plane worse) | 0.079 | 0.102 | 0.029 |

    ov_plane's gain "is limited as few planes are successfully tracked in the clustered environments". Source: [arXiv 2407.17709](https://arxiv.org/abs/2407.17709)
  - Plane states alone ("PGD w/o G.") already cut ATE strongly versus the same RGB-D-inertial system without planes, for example Office 1 from 0.097 to 0.030 m. Graph-based drift suppression added a 45% average improvement on long VCU-RVI corridors. — [arXiv 2407.17709](https://arxiv.org/abs/2407.17709)
  - In the same comparison PlanarSLAM (RGB-D, Manhattan rotation, no IMU) "easily collapses" and fails on many sequences. — [arXiv 2407.17709](https://arxiv.org/abs/2407.17709)
- Other related works not read in detail:
  - PLP-VIO, "Leveraging Planar Regularities for Point Line VIO" (Li et al., 2020). — [arXiv 2004.11969](https://arxiv.org/abs/2004.11969)
  - "Structural Regularity Aided VIO with Novel Coordinate Alignment and Line Triangulation" (IEEE 2022, Manhattan assumption, weak texture). — [IEEE 9842325](https://ieeexplore.ieee.org/abstract/document/9842325)
  - SLC-VIO (stereo, structural lines). — [Robotica](https://www.cambridge.org/core/journals/robotica/article/abs/slcvio-a-stereo-visualinertial-odometry-based-on-structural-lines-and-points-belonging-to-lines/D00E89F41A81E1D2B19E1E9851C5B6CE)
  - Monocular point-line VIO with structural constraints (Visual Computer 2023). — [Springer](https://link.springer.com/article/10.1007/s00371-023-02807-z)

### Inferences
- For a drone with VIO already running, the StructVIO result suggests the part worth copying is the heading-of-local-MW-in-the-state idea (a yaw prior), not line features by themselves.
- Plane landmarks give the largest gains with real depth (RGB-D/stereo). Monocular plane detection (ov_plane) adds little in clutter. A ZED Mini provides dense stereo depth, so it can use the PGD/L-SLAM style.

### Gaps
- I did not obtain the ov_plane paper's own EuRoC/TUM-VI numbers (the author PDF link returned 404).
- I did not find published yaw-drift-only numbers (deg/min) for StructVIO.
- I found no 2025-2026 paper that tightly couples a depth-normal MF yaw measurement into VIO with flight tests.

## 3. Plane-based localization / planar SLAM (walls, floor, ceiling as landmarks)

### Takeaway
Infinite-plane landmarks can be added to factor graphs and filters cheaply. The minimal quaternion-like parameterization for iSAM/GTSAM comes from Kaess (2015). Once rotation is known from the MF, each wall reduces to a single offset parameter (L-SLAM). Walls then constrain position along their normals, which bounds drift in a box room: the floor bounds height, and two orthogonal walls bound x/y. This is the simplest "wall-relative position" mechanism found.

### Cited Findings
- Kaess, "Simultaneous Localization and Mapping with Infinite Planes", ICRA 2015 (older). Homogeneous plane parameterization with a minimal (quaternion-style) representation, suitable for Gauss-Newton, Dog-Leg and iSAM. Adds a relative plane formulation that improves convergence. Real-time handheld RGB-D mapping of indoor scenes. — [Kaess 2015 PDF](https://www.cs.cmu.edu/~kaess/pub/Kaess15icra.pdf)
- The GTSAM `OrientedPlane3` factor descends from this work (inference; not verified in this session).
- CPA-SLAM (Ma, Kerl, Stückler, Cremers), ICRA 2016, pp. 1285-1291 (older). Dense direct RGB-D SLAM that couples frame-to-keyframe and frame-to-plane alignment in an EM framework with a global plane model that limits drift. Needs a GPU. Its ICL-NUIM average ATE of 0.028 m is quoted in the L-SLAM paper. — [CPA-SLAM PDF](https://cvai.cit.tum.de/_media/spezial/bib/lingni16icra.pdf); [L-SLAM PDF](http://brian.coltin.org/pub/kim2018linear.pdf)
- L-SLAM's KF with plane offsets (state 3+n): the authors estimate the EKF update is about 100x faster than Martinez-style EKF-SLAM for 10 planes. Measurement = camera-to-plane distance along the known MW axis. — [L-SLAM PDF](http://brian.coltin.org/pub/kim2018linear.pdf)
- SP-SLAM ("supposed planes", Zhang et al. 2019) ICL-NUIM average 0.020 m, as reported in ManhattanSLAM's comparison. — [arXiv 2103.15068](https://arxiv.org/abs/2103.15068)
- PGD-VIO: planes in an EKF state with RGB-D-inertial input gave large ATE reductions (Section 2). Its drift-suppression step detects "ghost" duplicate walls caused by drift and aligns them, which acts as a structural loop closure without bundle adjustment. — [arXiv 2407.17709](https://arxiv.org/abs/2407.17709)

### Inferences
- In a box room, if the wall/floor planes in a persistent map are kept fixed (or slowly refined), the distance from the current depth frame to each re-observed wall is a direct measurement of position along that wall's normal. In L-SLAM's terms this is a linear measurement once rotation is known. It removes x/y/z drift whenever two orthogonal walls and the floor are in view, and leaves drift along a corridor axis when only parallel walls are visible.
- With a ZED Mini (about 0.1-15 m range, roughly 90 deg horizontal FoV), large warehouse walls may be beyond reliable depth range. The floor is usually visible from a forward-down tilt, and rack faces form Manhattan-aligned planes. These sensor specs are general knowledge, not from the sources above.

### Gaps
- I did not extract the original SP-SLAM paper (Zhang et al. 2019); the arXiv ID tried was wrong.
- I did not extract CPA-SLAM's own TUM numbers.
- I found no source quantifying plane-offset measurement noise for stereo depth at warehouse ranges.

## 4. Practical recipe: extracting the MF, one-wall robustness, 90 deg ambiguity, EKF fusion, failure cases

### Takeaway
A minimal, well-supported pipeline:
1. Compute normals from smoothed depth (guided filter, then Sobel gradient cross product, or integral-image tangent averaging).
2. Downsample.
3. Track the MF with mean shift or vMF MAP on the unit sphere, initialized from the previous estimate (45 deg rule), with global branch-and-bound or histogram initialization.
4. Fuse in an EKF as an absolute-rotation (or yaw-only, given gravity) measurement while the gyro propagates.

A single visible plane only constrains 2 DoF of rotation, so yaw from one wall needs the floor or gravity (IMU) plus that wall. Gate the update on axis coverage and fall back to VIO otherwise. Use an Atlanta-world model (gravity plus multiple horizontal headings) when rooms are not strictly orthogonal.

### Cited Findings
- Normals: guided filter, then point cloud, then Sobel p_u x p_v at 640x480. Normal preprocessing dominates runtime. — [Straub et al. 2015](https://jstraub.github.io/download/straub2015rtmf_web.pdf). Alternative: average u/v tangent vectors with integral images. — [OPVO PDF](http://brian.coltin.org/pub/kim2017visual.pdf)
- Tracking: SO(3)-constrained mean shift that alternately projects normals into the tangent planes of the x, y and z MF axes. — [OPVO PDF](http://brian.coltin.org/pub/kim2017visual.pdf); lines are added as vanishing directions on the Gaussian sphere in [LPVO PDF](http://brian.coltin.org/pub/kim2018low.pdf)
- Global (re)initialization: branch-and-bound on the extended Gaussian image with a global-optimality guarantee in near real time. — [Joo et al. TPAMI 2019](https://koasas.kaist.ac.kr/handle/10203/251481)
- 90 deg ambiguity: the MF rotation is only defined modulo the 24 cube symmetries. Consistent tracking is guaranteed if inter-frame rotation is under 45 deg. — [Straub et al. 2015](https://jstraub.github.io/download/straub2015rtmf_web.pdf)
- EKF fusion pattern (Straub):
  - State: quaternion plus gyro bias.
  - Gyro rates drive the prediction and the RTMF rotation drives the update.
  - The measurement uncertainty was set to a fixed value; deriving a proper covariance was left as future work.
  - Result: under 2.8 deg RMSE over 4.5 min vs 8.50 deg for IMU-only.
  - Source: [Straub et al. 2015](https://jstraub.github.io/download/straub2015rtmf_web.pdf)
- StructVIO keeps each local MW heading in the filter state and refines it as new observations arrive, rather than using a fixed world MF. This handles multiple rotated MWs (Atlanta). — [arXiv 1810.06796](https://arxiv.org/abs/1810.06796)
- One plane / one wall:
  - OPVO and MWO fail when only one plane is visible.
  - LPVO needs one plane plus one pair of MW-parallel lines.
  - ManhattanSLAM switches to feature tracking when no MF is detected.
  - RTMF accuracy degrades when normals fall on only one or two axes.
  - Sources: [LPVO PDF](http://brian.coltin.org/pub/kim2018low.pdf); [arXiv 2103.15068](https://arxiv.org/abs/2103.15068); [Straub et al. 2015](https://jstraub.github.io/download/straub2015rtmf_web.pdf)
- Failure cases reported in the papers:
  - Non-orthogonal or oblique corridors: RMSE +287% if a single MW is forced. — [StructVIO](https://arxiv.org/abs/1810.06796)
  - A hallway misaligned with the global MW causes the estimate to lock to the local MW. — [Straub et al. 2015](https://jstraub.github.io/download/straub2015rtmf_web.pdf)
  - Cluttered scenes: MF rarely detected on TUM fr1/fr2 ([ManhattanSLAM](https://arxiv.org/abs/2103.15068)); no gain in the cluttered EuRoC Vicon rooms ([StructVIO](https://arxiv.org/abs/1810.06796)).
  - Noisy real depth: "MW-based methods suffer" on TUM compared with ICL. — [ManhattanSLAM](https://arxiv.org/abs/2103.15068)
  - Slanted-only walls. — [StructVIO](https://arxiv.org/abs/1810.06796)
- Robustness to clutter: RTMF segmentations on NYU depth scenes "perform well on a wide range of cluttered scenes". — [Straub et al. 2015](https://jstraub.github.io/download/straub2015rtmf_web.pdf)

### Inferences (implementation recommendation for ZED Mini + existing VIO/EKF, e.g. PX4 EKF2 external vision or a ROS filter)
- **Simplest viable correction (recommended first):** a yaw-only "Manhattan compass" node.
  1. Take ZED depth at reduced resolution (for example 320x180) and compute normals as above.
  2. Rotate the normals into a gravity-aligned frame using the VIO/IMU roll and pitch, which are drift-free thanks to gravity.
  3. Keep only near-horizontal normals (|n_z| < about 0.3).
  4. Build a histogram of their azimuth modulo 90 deg. A 1 deg-bin histogram with 4-fold folding (angle*4 on the circle) is a 1-D Atlanta/Manhattan estimate, using atan2(sum sin 4θ, sum cos 4θ)/4.
  5. Measured yaw = the room axis closest to the current VIO yaw (unwrap modulo 90 deg around the prediction).
  6. Innovation = wrap90(measured − VIO_yaw); accept only if |innovation| < about 10-20 deg, enough normals support it, and the histogram peak is sharp.
  7. Feed it as a heading measurement (yaw with variance of a few deg²) or as a slowly applied yaw offset correction on the VIO pose.

  This needs only one vertical wall, because gravity supplies the other two rotation DoF. This is the main practical advantage of IMU-aided MF over the RGB-D-only OPVO, which needs two planes. It mirrors the Straub EKF and Doer/Trommer yaw-aiding patterns.
- Expected accuracy: real-sensor RTMF gives about 3 deg full-3D RMSE. A yaw-only fold-histogram on gravity-leveled normals should do at least as well on large walls, but this is an untested inference. Even 2-3 deg absolute, non-drifting yaw beats unbounded VIO yaw drift over long flights. Position error from a yaw error ε over distance d is about ε·d (1 deg is about 1.7 cm per metre).
- **Position (second step):** with yaw fixed, store each room's dominant wall planes (offset along the MW x/y axes) and the floor height in a small map. Measure plane offsets in each depth frame (RANSAC on Manhattan-segmented points, or median of projected points per segmented axis) and apply 1-D position corrections along each wall normal, L-SLAM style. Expect observability only along normals of visible walls.
- **Warehouse caveats:**
  - Racks are aligned with the building, which helps: rack faces and uprights give Manhattan normals and vertical lines.
  - Pallets, goods and pillars add clutter.
  - Long aisles give only parallel walls, so position along the aisle is unconstrained.
  - Gate on normal-count and peak sharpness, and run an Atlanta (multi-heading) mode or reject secondary peaks when the 4-fold histogram is not unimodal.
- **90 deg / initialization:** the absolute room frame is set once at takeoff, with the yaw offset chosen as the MF axis nearest the initial VIO yaw. After that only the 45 deg rule matters. Real VIO yaw drift of a few deg/min means slip by a quadrant is practically impossible if updates come at 1 Hz or faster.

### Gaps
- I found no source giving Manhattan-yaw accuracy specifically for ZED / stereo depth (as opposed to Kinect/Xtion structured light). Stereo depth noise on textureless walls (the very surfaces that make good normals) may be worse; that would need to be measured.
- I did not find a published, quantitatively evaluated "loosely coupled Manhattan yaw on top of an off-the-shelf VIO" paper for vision. The closest is Straub's EKF (gyro + RTMF) and the Doer/Trommer radar yaw aiding.

## 5. Drone / MAV papers using Manhattan or plane constraints in flight

### Takeaway
Flight-tested examples are few.
- Doer and Trommer (ICINS 2021, x-RIO) used Manhattan-world yaw aiding in an EKF radar-inertial odometry on drones indoors. This is the closest analogue to the proposed "yaw correction on top of odometry" design.
- Older MAV work (2011-era) used vanishing points for heading in corridors.
- A recent UAV VIO study confirms accumulated yaw drift is the dominant residual error on non-revisiting EuRoC trajectories, which is the problem this would fix.
- I found no warehouse-inventory-drone paper that publishes Manhattan or plane-constraint drift numbers.

### Cited Findings
- Doer and Trommer, "Yaw aided Radar Inertial Odometry using Manhattan World Assumptions", ICINS 2021.
  - Filter-based 3D radar-inertial odometry with yaw aiding from Manhattan-world assumptions. "Once initialized, our approach enables instantaneous yaw aiding using only a single radar scan."
  - Evaluated on handheld and drone datasets, including indoor flight experiments.
  - Accuracy similar to state-of-the-art VIO and runs many times faster than real time on an embedded computer.
  - Code and datasets are public.
  - Source: [author page](https://christopherdoer.github.io/publications/2021_05_ICINS2021); [IEEE](https://ieeexplore.ieee.org/document/9470842/)
- x-RIO (Doer and Trommer, Gyroscopy and Navigation vol. 12, pp. 329-339) fuses radar 3D ego velocity and optional Manhattan-world yaw measurements, and calibrates extrinsics online. — [KIT repository](https://publikationen.bibliothek.kit.edu/1000143699)
- Bills, Chen, Saxena, "Autonomous MAV Flight in Indoor Environments using Single Image Perspective Cues", ICRA 2011 (older). AR.Drone in corridors and stairs, with heading from perspective cues and vanishing points (monocular). — [PDF](https://www.cs.cornell.edu/~asaxena/MAV/saxena_MAV_perspectivecues_stairs.pdf)
- An AIAA JAIS quadrotor indoor-navigation paper regulated yaw drift with a downward camera plus landmarks, and determined heading from the vanishing point of a forward camera. — [AIAA](https://arc.aiaa.org/doi/10.2514/1.I010249)
- A recent GTSAM monocular VIO study for indoor UAVs (MDPI Drones vol. 10) reports that the dominant residual on non-revisiting EuRoC trajectories is accumulated yaw drift. — [MDPI Drones](https://www.mdpi.com/2504-446X/10/9/685)
- StructVIO's EuRoC (MAV dataset) results: clear gains in the box-like Machine Hall, none in cluttered Vicon rooms. — [arXiv 1810.06796](https://arxiv.org/abs/1810.06796)

### Inferences
- The Doer/Trommer design (EKF state; yaw pseudo-measurement from Manhattan-structured range data; single-scan update after initialization) maps almost directly onto ZED depth normals in place of radar returns. It is a proven-on-drone template for a loosely coupled correction.
- For PX4 specifically (the user's stack uses MAVROS), the simplest integration is to correct the yaw of the vision pose sent to EKF2 (an external-vision yaw source). The other option is a separate heading message, but which interface PX4 accepts best was not verified here.

### Gaps
- I found no warehouse inventory drone papers (for example academic work on aisle-following inventory UAVs) with quantitative structural-constraint results in this session.
- I could not access the Doer ICINS 2021 full text for numeric yaw error and the details of how the 90 deg ambiguity is handled.
- I found no 2024-2026 flight-tested vision-based Manhattan-yaw VIO paper. This may be a real literature gap or a limit of the search.
