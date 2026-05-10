https://github.com/TianxingChen/RoboTwin/tree/main?tab=readme-ov-file

According to the README, first configure the environment. I'll still use the dl environment.

Then check the config according to the README

![](https://icndr2yneehy.feishu.cn/space/api/box/stream/download/asynccode/?code=NGE2ZTgyZDQ3MjI3ZDBhN2FlN2ZhNDJiOTA1NzY3ZjdfMXZrNDNDaGxmZEp2NzMydkVmTjNvV1lXck1CSllCRnBfVG9rZW46TjU1Q2JOME1Jb3N5cm54ZDBsYmNYMURObkVwXzE3NTA4MjI0NDY6MTc1MDgyNjA0Nl9WNA)

For better visualization, let's use 20 and true to see the effect.

In this code configuration, `fovy` refers to the **Vertical Field of View**.

It represents the angular range of the scene that the camera can capture in the vertical direction, usually measured in degrees (°).

- For the `L515` camera, `fovy: 45` means its vertical field of view is 45 degrees.

- For the `D435` camera, `fovy: 37` means its vertical field of view is 37 degrees.

This parameter is related to the camera's focal length and sensor size, determining how "wide" the camera's field of view is vertically. The corresponding parameter is the horizontal field of view (fovx or hfov), which represents the horizontal viewing range.

However, during evaluation, I found that the robot can't even pick up a hammer. This reveals a significant limitation.

![](https://icndr2yneehy.feishu.cn/space/api/box/stream/download/asynccode/?code=MzIwNjQzMGFlY2IzYjdjMmJiNzhiYWQ4NjdkYTIxMTlfMzZVNVlGRng2TTZLU05oZXY1RjlSVUFPcnN6SE9oRTZfVG9rZW46Q05ubGJoSWtob0dZSXh4V0ZUdWMyQXg4bmllXzE3NTA4MjI0NDY6MTc1MDgyNjA0Nl9WNA)

It first attempts to grasp but misses, then circles around nearby, demonstrating that reinforcement learning still has issues with agile.x.
