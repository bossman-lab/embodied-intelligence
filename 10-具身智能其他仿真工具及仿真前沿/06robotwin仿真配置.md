https://github.com/TianxingChen/RoboTwin/tree/main?tab=readme-ov-file

按照readme，首先配置环境，我的还是采用dl环境

然后按照readme看config

![](https://icndr2yneehy.feishu.cn/space/api/box/stream/download/asynccode/?code=NGE2ZTgyZDQ3MjI3ZDBhN2FlN2ZhNDJiOTA1NzY3ZjdfMXZrNDNDaGxmZEp2NzMydkVmTjNvV1lXck1CSllCRnBfVG9rZW46TjU1Q2JOME1Jb3N5cm54ZDBsYmNYMURObkVwXzE3NTA4MjI0NDY6MTc1MDgyNjA0Nl9WNA)

为了更好可视化，我们采用20和true吧，看一看效果

在这个代码配置中，`fovy` 指的是 **垂直视场角 (Vertical Field of View)**。

它表示相机在垂直方向上能够捕捉到的场景的角度范围，通常以度（°）为单位。

- 对于 `L515` 相机，`fovy: 45` 意味着它的垂直视场角是 45 度。

- 对于 `D435` 相机，`fovy: 37` 意味着它的垂直视场角是 37 度。

这个参数与相机的焦距和传感器尺寸有关，决定了相机视野的“上下”有多宽。与之对应的是水平视场角 (fovx 或 hfov)，表示“左右”的视野范围。

但是eval的时候发现，这个玩意连个榔头都拉不起来，笑了

![](https://icndr2yneehy.feishu.cn/space/api/box/stream/download/asynccode/?code=MzIwNjQzMGFlY2IzYjdjMmJiNzhiYWQ4NjdkYTIxMTlfMzZVNVlGRng2TTZLU05oZXY1RjlSVUFPcnN6SE9oRTZfVG9rZW46Q05ubGJoSWtob0dZSXh4V0ZUdWMyQXg4bmllXzE3NTA4MjI0NDY6MTc1MDgyNjA0Nl9WNA)

先夹一下夹空，然后在旁边兜圈子，证明强化学习在agile.x上还是有问题的。
