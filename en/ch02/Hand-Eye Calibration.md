# 6.1 Hand-Eye Calibration

- [6.1 Hand-Eye Calibration](#61-hand-eye-calibration)
  - [6.1.1 Definition of Hand-Eye Calibration](#611-definition-of-hand-eye-calibration)
  - [6.1.2 Mathematical Model of Hand-Eye Calibration](#612-mathematical-model-of-hand-eye-calibration)
    - [6.1.2.1 Eye In Hand](#6121-eye-in-hand)
    - [6.1.2.2 Eye To Hand](#6122-eye-to-hand)
  - [6.1.3 Solving $AH = HB$](#613-solving-ah--hb)
    - [6.1.3.1 Solving Rotation Using Park's Method](#6131-solving-rotation-using-parks-method)
    - [6.1.3.2 Solving Translation Using Park's Method](#6132-solving-translation-using-parks-method)
  - [6.1.4 Hand-Eye Calibration Methods in OpenCV and Calibration Notes](#614-hand-eye-calibration-methods-in-opencv-and-calibration-notes)
    - [6.1.4.1 Hand-Eye Calibration Interfaces in OpenCV](#6141-hand-eye-calibration-interfaces-in-opencv)
    - [6.1.4.2 Calibration Notes](#6142-calibration-notes)
  - [6.1.5 Evaluating Hand-Eye Calibration Effect](#615-evaluating-hand-eye-calibration-effect)
  - [References](#references)

## 6.1.1 Definition of Hand-Eye Calibration

Hand-Eye Calibration is a fundamental and critical issue in robotic vision applications. It is mainly used to unify the coordinate systems of the vision system and the robot. Specifically, it determines the relative pose relationship between the camera and the robot.

> When we want to use vision to guide a robot to grasp an object, we need to know three relative positional relationships:
>
> 1. The relative positional relationship between the end effector and the robot base
> 2. The relative positional relationship between the camera and the end effector
> 3. The relative position and orientation between the object and the camera
>
> Hand-Eye Calibration mainly solves the second problem, that is, determining the spatial transformation relationship between the "hand" and the "eye" mounted on it, i.e., solving the transformation matrix between the camera coordinate system and the robot coordinate system. Here, we refer to the robot's end effector as the "hand" and the camera as the "eye."

According to the installation methods of the camera, hand-eye calibration is divided into two forms: 1. If the camera is installed at the end of the robotic arm, it is called Eye-in- Hand. 2. If the camera is installed on the robot base outside the robotic arm, it is called Eye-to-Hand.

![alt text](Figure\6_image_0.png)

## 6.1.2 Mathematical Model of Hand-Eye Calibration

Whether it is for Eye in Hand or Eye to Hand, the mathematical equation they solve is the same, both being $AH = HB$. First, we need to define the following coordinate systems:

$F_b$: **Base Frame**, fixed on the base of the robotic arm, is the global reference coordinate system for the robotic arm's movement.

$F_e$: **End-Effector Frame**, fixed on the end effector of the robotic arm (such as a gripper or tool).

$F_c$: **Camera Frame**, fixed at the optical center of the camera, is the reference frame for visual perception.

$F_t$: **Calibration Target Frame**: fixed on the calibration target (such as a chessboard, dot board).

The relationship between coordinate systems is usually represented by a homogeneous transformation matrix (rigid body transformation) T:

$T^i_j=\left[\begin{array}{cc}
R^i_j & t^i_j \\
0 & 1
\end{array}\right]$

Where $R ∈ SO(3)$ and $t ∈ \R^{3}$ correspond to rotation transformation and translation transformation,respectively. The superscript and subscript of T indicate which two coordinate systems the transformation is for. For example:

$T^e_c$: The transformation that converts the camera coordinate system to the end-effector coordinate system also represents the pose of the camera in the end  - effector coordinate system. In the case of eye - in - hand, this is the target matrix we need to find.

### 6.1.2.1 Eye In Hand

When the camera is fixed at the end of the robotic arm, the transformation between the camera and end-effector coordinate systems remains constant. This is called "Eye-in-Hand". When performing this type of hand - eye calibration, the calibration target is fixed in one place, and then the robotic arm is controlled to move to different positions. The camera fixed on the robotic arm is used to capture images of the calibration target at different positions, and multiple sets of images of the calibration target  at different positions are taken.

![alt text](Figure\6_image_1.png)

Since the calibration target and the robot base are fixed, their relative pose relationship remains unchanged, so:

$T^b_t = T^b_{e1}T^{e1}_{c1}T^{c1}_{t} = T^b_{e2}T^{e2}_{c2}T^{c2}_{t}$

The equation above is transformed as follows:

$(T^b_{e2})^{-1}T^b_{e1}T^{e1}_{c1}T^{c1}_{t} =T^{e2}_{c2}T^{c2}_{t} \\
(T^b_{e2})^{-1}T^b_{e1}T^{e1}_{c1} =T^{e2}_{c2}T^{c2}_{t}(T^{c1}_{t})^{-1} \\
T^{e2}_{e1}T^{e1}_{c1} =T^{e2}_{c2}T^{c2}_{c1} \\
T^{e2}_{e1}T^{e}_{c} =T^{e}_{c}T^{c2}_{c1} \\
AH = HB$

$T^e_c$ is the $H$ we need to solve finally.

### 6.1.2.2 Eye To Hand

When the camera is fixed outside the robotic arm, the relative position between the camera and the end-effector changes as the robotic arm moves. This is called "eye-to-hand". When performing this type of hand-eye calibration, the calibration target  is fixed to the end of the robotic arm, and then the robotic arm is controlled to hold the calibration target  and capture images around the fixed camera. For the accuracy of the solution, generally more than 10 sets of photos need to be taken.

![alt text](Figure\6_image_2.png)

Since the calibration target is fixed at the end of the robotic arm at this time, their relative position remains unchanged when taking different photos, so:

$T^e_t = T^{e1}_bT^{b}_{c}T^{c}_{t1} = T^{e2}_bT^{b}_{c}T^{c}_{t2}$

$T^{e1}_bT^{b}_{c}T^{c}_{t1} = T^{e2}_bT^{b}_{c}T^{c}_{t2} \\
(T^{e2}_b)^{-1}T^{e1}_bT^{b}_{c}T^{c}_{t1} = T^{b}_{c}T^{c}_{t2} \\
(T^{e2}_b)^{-1}T^{e1}_bT^{b}_{c} = T^{b}_{c}T^{c}_{t2}(T^{c}_{t1})^{-1} \\
(T^b_{e2}T^{e1}_b)T^{b}_{c} = T^{b}_{c}(T^{c}_{t2}T^{t1}_c) \\
AH = HB$

## 6.1.3 Solving $AH = HB$

As an important part of robotics, hand-eye calibration has been extensively studied by the academic community since the 1980s, with numerous methods developed to solve the equation $AH = HB$. Currently, a step-by-step solution method is commonly used, which decomposes the system of equations, uses the properties of the rotation matrix to solve the rotation, and then substitutes the rotation solution into the translation equation to find the translation part.

The classic two-step algorithms include the Tsai-Lenz method that converts the rotation matrix into a rotation vector for solving, the Park method that solves based on the Lie group properties of the rotation matrix (the adjoint property of the Lie group) and so on. Next, the Park method will be introduced.

### 6.1.3.1 Solving Rotation Using Park's Method

The three variables in the original equation are all homogeneous transformation matrices,which write rotation and translation transformations in a 4x4 matrix, representing the transformation between two coordinate systems. The basic structure is:

$H=\left[\begin{array}{cc}
R & t \\
0 & 1
\end{array}\right]$

Where $R\in SO(3)$ and $t\in \mathbb{R}^{3}$ correspond to the rotation transformation and the translation transformation respectively.

The original equation is transformed as follows:

$AH  = HB \\
\begin{array}{l}
\left[\begin{array}{cc}
\theta_{A} & b_{A} \\
0 & 1
\end{array}\right]\left[\begin{array}{cc}
\theta_{X} & b_{X} \\
0 & 1
\end{array}\right]  =\left[\begin{array}{cc}
\theta_{X} & b_{X} \\
0 & 1
\end{array}\right]\left[\begin{array}{cc}
\theta_{B} & b_{B} \\
0 & 1
\end{array}\right]\\
\end{array}$

Therefore, we have (the rotation and translation parts of the product result are equal in corresponding positions):

$\begin{aligned}
\theta_{A} \theta_{X} & =\theta_{X} \theta_{B} \\
\theta_{A} b_{X}+b_{A} & =\theta_{X} b_{B}+b_{X}
\end{aligned}$

First, solve the first equation containing only the rotation matrix.

$\begin{aligned}
\theta_{A} \theta_{X}  =\theta_{X} \theta_{B} \\
\theta_{A}  =\theta_{X} \theta_{B} \theta_{X}^T 
\end{aligned}$

Rotation matrices belong to the SO (3) group, and the SO (3) group is a Lie group. Every Lie group has a corresponding Lie algebra. Its Lie algebra lies in a low - dimensional Euclidean space (linear space) and is the tangent space representation of the local open domain of the Lie group. Lie groups and Lie algebras can be transformed into each other through the exponential map and the logarithmic map:

![alt text](Figure\6_image_3.png)
For the rotation matrix $R$, the transformation relationship with the corresponding Lie algebra $\boldsymbol{\Phi}$ can be expressed as follows:

$R = \exp(Φ^{\wedge}) = \exp [Φ]$

Where the [] symbol represents the ^ operation, i.e., converting to an antisymmetric matrix, or cross product.

For SO(3), its adjoint property is:

![alt text](Figure\6_image_3_1.png)

$\begin{aligned}
\theta_{A}  & =\theta_{X} \theta_{B} \theta_{X}^T \\
\exp [\alpha] & = \theta_{X}\exp [\beta]\theta_{X}^T  \\
\exp [\alpha] & = \exp [\theta_{X}\beta]  \\
\alpha &= \theta_{X}\beta
\end{aligned}$

When there are multiple sets of observations, the above problem can be transformed into the following least squares problem:

![alt text](Figure\6_image_3_2.png)

α and β are the Lie algebras of the corresponding rotations, and they are both three-dimensional vectors, which can be regarded as a three-dimensional point. Then the above problem is equivalent to a point cloud registration problem:
![alt text](Figure\6_image_3_4_1.png)

The least squares solution to this problem is:
![alt text](Figure\6_image_3_3.png)

Where:
![alt text](Figure\6_image_3_4.png)

### 6.1.3.2 Solving Translation Using Park's Method

After solving the rotation matrix, substitute the rotation matrix value into the second equation:

$\begin{aligned}
\theta_{A} b_{X}+b_{A} & =\theta_{X} b_{B}+b_{X} \\
\theta_{A} b_{X} - b_{X} & =\theta_{X} b_{B}- b_{A} \\
(\theta_{A} - I)b_{X}  & =\theta_{X} b_{B}- b_{A} \\
Cb_{X} &= D
\end{aligned}$

Where both C and D are known values. Since C is not necessarily invertible, the original equation is transformed as follows:
$\begin{aligned}
Cb_{X} &= D \\
C^TCb_{X} &= C^TD \\
b_{X} &= (C^TC)^{-1}C^TD
\end{aligned}$

Then the translation part can be obtained.

When there are multiple sets of observation values:
![alt text](Figure\6_image_3_5.png)

The final solution is:
$\begin{aligned}
H = \left[\begin{array}{cc}
\theta_{X} & b_{X} \\
0 & 1
\end{array}\right]
\end{aligned}$

## 6.1.4 Hand-Eye Calibration Methods in OpenCV and Calibration Notes

According to their implementation principles, hand-eye calibration algorithms can be divided into three categories: separable closed-form solutions, simultaneous closed-form solutions, and iterative methods.

> a. Separable closed-form solutions: a method where rotational components are solved separately from translational components.
>
> Disadvantage: The calculation error of the rotation component Rx will be introduced into the calculation of the translational components tx.
>
> b. Simultaneous closed-form solutions: a method where both translational components and rotational components are solved simultaneously.
>
> Disadvantage: Due to the influence of noise, the solution of the rotation component Rx may not be an orthogonal matrix. Therefore, an orthogonalization step must be taken for the rotation component. However, the corresponding translational component is not recalculated, which will lead to solution errors.
>
> c. Iterative solutions: a method that uses optimization techniques to solve for rotational components and translational components iteratively.
>
> Disadvantage: This method may have high computational complexity because these methods usually include complex optimization procedures. In addition, as the number of equations (n) increases, the difference between the iterative solution and the closed-form solution usually becomes smaller. Therefore, before using this method, it is necessary to decide whether the accuracy of the iterative solution is worth the calculation cost.

### 6.1.4.1 Hand-Eye Calibration Interfaces in OpenCV

![alt text](Figure\6_image_4.png)

OpenCV mainly implements the first two types of methods, with the default method being TSAI. PARK and HORAUD are also separable solutions while ANDREFF and DANIILIDIS are simultaneous closed - form solutions. (According to the experiments with the same set of data, it is concluded that the error of the solution obtained by the TSAI method in the separable solutions is relatively large.)

Collect multiple sets of calibration data, input the corresponding robotic arm data and camera calibration target positioning data, and then the calibration results can be obtained.

### 6.1.4.2 Calibration Notes

If this is your first time to perform calibration, a few points should be noted:

1. If the internal parameters used to obtain the rotation matrix (R) and translation vector (t) from the calibration target  to the camera via calibrateCamera differ from those used for grasping, errors will result.

2. The corner direction of the calibration target  is reversed. By default, it is from left to right, but sometimes it is from right to left, resulting in the coordinate systems not being unified.

3. If the area of the calibration target is too small, and only moves within the central region,it will lead to inaccuracy at the edges.

4. Rotate during calibration.

5. There should be at least 10 images.

6. The transformation matrix of RGBD in some cameras should be noted.

## 6.1.5 Evaluating Hand-Eye Calibration Effect

![alt text](Figure\6_image_6.png)

## References

[1. Hand-Eye Calibration Algorithm---Sai-Lenz (A New Technique for Fully Autonomous and Efficient 3D Robotics Hand/Eye Calibration)](https://blog.csdn.net/u010368556/article/details/81585385)

[2. User Guide for Robot Hand-Eye Calibration](https://docs.mech-mind.net/1.5/zh-CN/SoftwareSuite/MechVision/CalibrationGuide/CalibrationGuide.html)

[3. Calibration Study Notes (IV) -- Detailed Explanation of Hand-Eye Calibration](https://blog.csdn.net/qq_45006390/article/details/121670412)

[4. Camera Calibration and 3D Reconstruction](https://docs.opencv.org/4.10.0/d9/d0c/group__calib3d.html#gad10a5ef12ee3499a0774c7904a801b99)

[5. 3D Vision Workshop - Hand-Eye Calibration (with OpenCV implementation code)](https://blog.csdn.net/z504727099/article/details/115494147)
