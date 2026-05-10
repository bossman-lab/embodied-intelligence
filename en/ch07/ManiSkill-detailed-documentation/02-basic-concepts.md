# Fundamentals of Simulation and Robotics

This document introduces basic concepts in simulation and robotics to help you better understand ManiSkill's technical details, such as what pose is, how quaternions are used, and what Actor and Articulation are.

## Common Terminology / Conventions

- **Pose**: The combination of an object's position and orientation in 3D space. In ManiSkill/SAPIEN, a pose consists of 3D position and 4D quaternion.
- **`https://en.wikipedia.org/wiki/Quaternion`**: A mathematical tool commonly used to represent rotation/orientation, consisting of four values. ManiSkill/SAPIEN uses quaternions in wxyz format. For more information about rotation representations in simulation, you can refer to this article `https://simulately.wiki/blog/rotation`.
- **Z-axis as "Up"**: In ManiSkill/SAPIEN, the Z-axis is considered the standard "up" direction. Therefore, objects like upright goblets typically have their long axis along the Z-axis.

## Simulation Objects

For rigid body simulation, which models objects that are not easily deformed physically (such as wooden blocks, computers, walls, etc.), ManiSkill/SAPIEN provides two main object types: **Actor** and **Articulation**.

In the simulation process, we usually start with a reconfiguration step, loading all objects into the simulation environment. After loading, we set the poses of all objects and initialize them.

### Actor

An Actor is usually a "single" object that moves as a whole without deformation when subjected to external forces. For example, baseball bats, glass cups, walls, etc., can be considered Actors. Actors have the following properties:

- **Pose**: The position and orientation of an object in 3D space. Position is in meters.
- **Linear velocity**: The translational velocity of the object in the x, y, z axes, in meters per second.
- **Angular velocity**: The angular velocity of the object in the x, y, z axes, in radians per second.

In simulation, an Actor consists of two main elements: collision shape and visual shape.

**Collision Shape:**

The collision shape defines how an object interacts physically in simulation. An Actor can consist of multiple convex collision shapes.

It should be noted that an Actor does not necessarily need to have a collision shape; they can be "ghost" objects used only for visual indication without participating in physical interactions.

**Visual Shape:**

The visual shape defines the appearance of an object in simulation for rendering display but does not affect physical simulation.

**Actor Types: Dynamic, Kinematic, Static**

There are three types of Actors:

- **Dynamic**: These Actors fully participate in physical simulation. When external forces are applied, they respond according to physical laws.
- **Kinematic**: These Actors partially participate in physical simulation. When external forces are applied, they do not deform or move. However, dynamic objects interacting with these Actors will be affected by reaction forces. Compared to dynamic Actors, kinematic Actors occupy less CPU/GPU resources and simulate faster.
- **Static**: These Actors are similar to kinematic Actors but their poses cannot be changed after being loaded into the simulation environment. They occupy less CPU/GPU resources and simulate faster. Walls, floors, cabinets, etc., are usually modeled as kinematic or static Actors because they typically do not move or get destroyed in reality.

Depending on the task you want to simulate, you may need to set certain objects as dynamic. For example, when simulating the task of moving a cup from a table to a shelf, the cup should be set as a dynamic Actor, while the shelf can be set as a kinematic or static Actor.

### Articulation

An Articulation consists of **Links** and **Joints**. In ManiSkill/SAPIEN, every two links are connected by a joint. Articulations are usually defined through XML or tree structures to represent more complex joint mechanisms. For example, cabinets, refrigerators, cars, etc., can be considered Articulations.

#### Links

Links are similar to Actors, with the same properties and can be physically simulated and manipulated. The difference is that a link must be connected to another link through a specific joint.

#### Joints

There are three main types of joints: fixed joints, revolute joints, and prismatic joints.

- **Fixed Joint**: Connects two links so that their relative positions remain fixed. This is useful when defining Articulations, as links connected by fixed joints can actually be considered as a single unit.
- **Revolute Joint**: Similar to a hinge, allowing connected links to rotate around the joint axis.
- **Prismatic Joint**: Allows connected links to slide along the joint axis.

#### Example

Consider a cabinet example. The cabinet has a base link, a top drawer link, and a bottom door link.

- The bottom drawer is connected to the base via a prismatic joint, allowing the drawer to slide in a specific direction.
- The bottom door is connected to the base via a revolute joint, allowing the door to rotate around an axis.

By understanding these basic concepts, you can more deeply participate in ManiSkill's development and application, designing more complex and realistic simulation scenarios.

# GPU Simulation

ManiSkill utilizes `https://developer.nvidia.cn/physx-sdk` for physics simulation on the GPU. This approach differs from traditional CPU-based simulation methods, with specific details as follows. It is recommended to read this section to understand the basics of GPU simulation and ManiSkill's design principles, which will help in writing more efficient code and building optimized GPU parallel tasks.

## Scenes and Subscenes

Under the GPU parallelization framework, thousands of tasks can be simulated simultaneously on the GPU. In ManiSkill/SAPIEN, this is achieved by placing all Actors and Articulations **into the same PhysX scene** and creating a small workspace called a **subscene** in this scene for each task.

The subscene design ensures that when reading data such as Actor poses, it is automatically preprocessed as data relative to the subscene center, rather than the entire PhysX scene. The following figure shows how to organize 64 subscenes. Note that the distance between each subscene is defined by the `sim_config.spacing` parameter in the simulation configuration, which can be set when building tasks.

SAPIEN allows subscenes to be located anywhere, but ManiSkill typically chooses a square layout with fixed spacing parameters. It should be noted that if objects in one subscene exceed their workspace, they may affect other subscenes. This is a common issue when users simulate large scenes (such as houses or outdoor environments), for example, when the spacing parameter is set too low, objects in subscene 0 may interact with objects in subscene 1.

## GPU Simulation Lifecycle

In ManiSkill, the Gym API is used to create, reset, and advance the environment. The `env.reset` process includes one-time reconfiguration followed by initialization steps:

1. **Reconfiguration**: Load objects (including Actors, Articulations, light sources) into the scene, i.e., generate them in their initial poses.
2. Call `physx_system.gpu_init()` to initialize all GPU memory buffers and set up rendering groups required for parallel rendering.
3. Initialize all Actors and Articulations (set poses, qpos values, etc.).
4. Run `physx_system.gpu_apply_*` to save the initialized data from step 3 to GPU buffers in preparation for simulation.
5. Run `physx_system.gpu_update_articulation_kinematics()` to update Articulation data (e.g., link poses) for retrieval.
6. Run `physx_system.gpu_fetch_*` to update relevant GPU buffers and generate observation data.

In code, we save the `physx_system` variable as `env.scene.px`.

The `env.step` process involves repeatedly executing the following steps to process actions and generate outputs:

1. Get the user's action (and clip if necessary).
2. Process the action, converting it into control signals (such as joint positions/velocities) to control the Agent.
3. Run `physx_system.gpu_apply_articulation_target_position` and `physx_system.gpu_apply_articulation_target_velocity` to apply the targets from step 2.
4. Run `physx_system.step()` to advance the simulation.
5. Run `physx_system.gpu_fetch_*` to update relevant GPU buffers and generate observation data.
6. Return step data: observations, rewards, termination flags, truncation flags, and other information.

## Data Organization on GPU

Rigid body data (including pose (7D), linear velocity (3D), and angular velocity (3D)) for each rigid body Actor and Articulation link in each subscene is tightly packed in `physx_system.cuda_rigid_body_data`, forming a large matrix organized as follows:

```plaintext
[Actor 1 Data] [Actor 2 Data] ... [Articulation 1 Link 1 Data] [Articulation 1 Link 2 Data] ... [Articulation N Link M Data]
```



Understanding this organization may be helpful for users planning to directly manipulate GPU buffers. Otherwise, if you use the API provided by ManiSkill, these details are handled automatically.

It is worth noting that the organization of this GPU buffer may not follow an intuitive structure (e.g., every k rows representing data for one subscene), as this is a trade-off for better performance. For example, the following example shows how data is organized when the PhysX scene contains 3 rigid body Actors (shown in red) and 3 Articulations with different numbers of links/degrees of freedom (DOF) (shown in green). SAPIEN pads the number of rows allocated to each Articulation to match the highest number of degrees of freedom in the entire PhysX scene.

## ManiSkill's Design Principles

### Batch Everything

ManiSkill is designed to support parallel simulation schemes for both CPU and GPU. The reason is that for certain tasks, even in non-industrial settings, GPU simulation may not be faster than using more CPUs. Therefore, almost all code in ManiSkill exposes data to users in batch form (batch dimension = number of parallel environments), treating CPU simulation with batch size 1 as a special case.

### Manage Objects and Views

ManiSkill can be considered as a Python interface for SAPIEN.

# Controllers / Action Spaces

Controllers are the interface between the user/policy and the robot. Whenever you take a step in the environment and provide an action, that action is sent to the selected controller, which converts the action into control signals for the robot. At the lowest level, all robots in simulation are controlled through joint position or joint velocity control, essentially specifying the position or velocity each joint should reach.

For example, the `arm_pd_ee_delta_pose` controller takes relative motion of the end effector as input and uses `https://en.wikipedia.org/wiki/Inverse_kinematics` to convert the input action into target positions for the robot's joints. The robot uses `https://en.wikipedia.org/wiki/PID_controller` to drive the motors to achieve the target joint positions.

In ManiSkill, there are several key points to note about controllers:

- Controllers define the action space of the task.
- Robots can have independent controllers for different joint groups. The action space is the concatenation of the action spaces of all controllers.
- A single robot may have multiple sets of available controllers.

The following sections detail each pre-built controller and its functionality.

## Passive

```python
from mani_skill.agents.controllers import PassiveControllerConfig
```

This controller allows you to force specified joints to be uncontrolled by actions. For example, in `https://github.com/haosulab/ManiSkill/blob/main/mani_skill/envs/tasks/control/cartpole.py`, the hinge joint of the CartPole robot is set to passive control (i.e., only allowing control of the sliding box).

## PD Joint Position

```python
from mani_skill.agents.controllers import PDJointPosControllerConfig
```

Uses a PD controller to control the position of specified joints through actions.

## PD EE (End Effector) Pose

```python
from mani_skill.agents.controllers import PDEEPoseControllerConfig
```

This controller has both pose and position variants, allowing more intuitive control of the robot's end effector (or any link). The default options of this controller are set in a more intuitive way, but various options are also available.

To understand how it works, you first need to understand the following three related transformation coordinate systems:

1. World coordinate system
2. Root link coordinate system
3. End effector/link coordinate system

In the following figure, these coordinate systems are represented by RGB axes, where red = X-axis, green = Y-axis, blue = Z-axis. The target link to be controlled is a virtual link representing the Tool Control Point (TCP), which is a simple offset of the end effector link (so its origin is located between the two grippers). Note that in ManiSkill/SAPIEN, the Z-axis is generally considered the natural "up direction", which differs from some other simulators.

In this controller, decoupled control of end effector translation and rotation is implemented. This means that actions used for translation do not affect actions used for rotating the end effector. This provides 6 dimensions of control, 3 for 3D translation and another 3 for rotation, as detailed below.

The controller provides two modes: incremental control and absolute control. In each environment time step, given an action, ManiSkill calculates a new target pose for the end effector and uses inverse kinematics to determine joint actions that can best achieve this target pose. The configuration of this controller effectively changes how the new target pose is calculated.

### Incremental Control

This mode is enabled by default and configured via the `use_delta` attribute. It allows users to submit actions that define increments in end effector pose to move toward a target. There are 4 combinations of control frames, derived from two choices for translation and rotation. Frames are defined by the `frame` attribute, with naming conventions as follows: