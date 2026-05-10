# 📸 Visualization and Rendering

Genesis' visualization system is managed by the `visualizer` of the scene you just created (i.e., `scene.visualizer`). There are two ways to visualize a scene: 1) using an interactive viewer running in a separate thread, 2) manually adding cameras to the scene and using them to render images.

## Viewer

If you have a display connected, you can use the interactive viewer to visualize the scene. Genesis uses different `options` groups to configure various components in the scene. To configure the viewer, you can change parameters in `viewer_options` when creating the scene. Additionally, we use `vis_options` to specify visualization-related properties that will be shared between the viewer and cameras (we'll add cameras soon).
Create a scene with more detailed viewer and visualization settings (this looks a bit complex but is just for illustration purposes):

```python
scene = gs.Scene(
    show_viewer    = True,
    viewer_options = gs.options.ViewerOptions(
        res           = (1280, 960),
        camera_pos    = (3.5, 0.0, 2.5),
        camera_lookat = (0.0, 0.0, 0.5),
        camera_fov    = 40,
        max_FPS       = 60,
    ),
    vis_options = gs.options.VisOptions(
        show_world_frame = True, # Visualize the coordinate frame of `world` at its origin
        world_frame_size = 1.0, # Length of world coordinate frame (meters)
        show_link_frame  = False, # Do not visualize coordinate frames of entity links
        show_cameras     = False, # Do not visualize added cameras' meshes and frustums
        plane_reflection = True, # Turn on plane reflection
        ambient_light    = (0.1, 0.1, 0.1), # Ambient light settings
    ),
    renderer = gs.renderers.Rasterizer(), # Use rasterizer for camera rendering
)
```

Here we can specify the viewer camera's pose and field of view. If `max_FPS` is set to `None`, the viewer will run as fast as possible. If `res` is set to None, Genesis will automatically create a 4:3 window with height set to half of the display height. Note that in the above settings, we set to use the rasterization backend for camera rendering. Genesis provides two rendering backends: `gs.renderers.Rasterizer()` and `gs.renderers.RayTracer()`. The viewer always uses the rasterizer. By default, cameras also use the rasterizer.
Once the scene is created, you can access the viewer object via `scene.visualizer.viewer` or the shorthand `scene.viewer`. You can query or set the viewer camera pose:

```python
cam_pose = scene.viewer.camera_pose()
scene.viewer.set_camera_pose(cam_pose)
```

## Cameras and Headless Rendering

Now let's manually add a camera object to the scene. Cameras are not connected to a viewer or display and only return rendered images when you request them. Thus, cameras work in headless mode.

```python
cam = scene.add_camera(
    res    = (1280, 960),
    pos    = (3.5, 0.0, 2.5),
    lookat = (0, 0, 0.5),
    fov    = 30,
    GUI    = False
)
```

If `GUI=True`, each camera will create an OpenCV window to dynamically display rendered images. Note that this is different from the viewer GUI.
Then, once we build the scene, we can render images using the camera. Our cameras support rendering RGB images, depth maps, segmentation masks, and surface normals. By default, only RGB is rendered; you can enable other modes by setting parameters when calling `camera.render()`:

```python
scene.build()
# Render RGB, depth, segmentation mask and normal map
rgb, depth, segmentation, normal = cam.render(depth=True, segmentation=True, normal=True)
```

If you used `GUI=True` and have a display connected, you should now see 4 windows. (Sometimes OpenCV windows may have additional latency, so if the window is black, you can call an extra `cv2.waitKey(1)` or simply call `render()` again to refresh the window.)

```{figure}

```

**Recording Videos with Cameras**
Now, let's render only RGB images, move the camera, and record a video. Genesis provides a convenient tool for recording videos:

```python
# Start camera recording. Once started, all rendered RGB images will be internally recorded
cam.start_recording()
import numpy as np
for i in range(120):
    scene.step()
    # Change camera position
    cam.set_pose(
        pos    = (3.0 * np.sin(i / 60), 3.0 * np.cos(i / 60), 2.5),
        lookat = (0, 0, 0.5),
    )

    cam.render()
# Stop recording and save video. If `filename` is not specified, a name will be automatically generated using the calling filename.
cam.stop_recording(save_to_filename='video.mp4', fps=60)
```

You saved the video to `video.mp4`:
<video preload="auto" controls="True" width="100%">


import genesis as gs
gs.init(backend=gs.cpu)
scene = gs.Scene(
    show_viewer = True,
    viewer_options = gs.options.ViewerOptions(
        res           = (1280, 960),
        camera_pos    = (3.5, 0.0, 2.5),
        camera_lookat = (0.0, 0.0, 0.5),
        camera_fov    = 40,
        max_FPS       = 60,
    ),
    vis_options = gs.options.VisOptions(
        show_world_frame = True,
        world_frame_size = 1.0,
        show_link_frame  = False,
        show_cameras     = False,
        plane_reflection = True,
        ambient_light    = (0.1, 0.1, 0.1),
    ),
    renderer=gs.renderers.Rasterizer(),
)
plane = scene.add_entity(
    gs.morphs.Plane(),
)
franka = scene.add_entity(
    gs.morphs.MJCF(file='xml/franka_emika_panda/panda.xml'),
)
cam = scene.add_camera(
    res    = (640, 480),
    pos    = (3.5, 0.0, 2.5),
    lookat = (0, 0, 0.5),
    fov    = 30,
    GUI    = False,
)
scene.build()
# Render RGB, depth, segmentation mask and normal map
# rgb, depth, segmentation, normal = cam.render(rgb=True, depth=True, segmentation=True, normal=True)
cam.start_recording()
import numpy as np
for i in range(120):
    scene.step()
    cam.set_pose(
        pos    = (3.0 * np.sin(i / 60), 3.0 * np.cos(i / 60), 2.5),
        lookat = (0, 0, 0.5),
    )
    cam.render()
cam.stop_recording(save_to_filename='video.mp4', fps=60)



## Parallel Simulation

```python
import torch
import genesis as gs

gs.init(backend=gs.gpu)

scene = gs.Scene(
    show_viewer   = False,
    rigid_options = gs.options.RigidOptions(
        dt                = 0.01,
    ),
)

plane = scene.add_entity(
    gs.morphs.Plane(),
)

franka = scene.add_entity(
    gs.morphs.MJCF(file='xml/franka_emika_panda/panda.xml'),
)

scene.build(n_envs=30000)

# Control all robots
franka.control_dofs_position(
    torch.tile(
        torch.tensor([0, 0, 0, -1.0, 0, 0, 0, 0.02, 0.02], device=gs.device), (30000, 1)
    ),
)

for i in range(1000):
    scene.step()
```

# test_genesis_bottle.py

```py
import argparse
import time

import genesis as gs
import numpy as np
import torch

parser = argparse.ArgumentParser()
parser.add_argument("-B", type=int, default=1) # batch size
parser.add_argument("-v", action="store_true", default=False) # visualize
parser.add_argument("-r", action="store_true", default=False) # random action
                    
args = parser.parse_args()

########################## init ##########################
gs.init(backend=gs.gpu)

########################## create a scene ##########################
```