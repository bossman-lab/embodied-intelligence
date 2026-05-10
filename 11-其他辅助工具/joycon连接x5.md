```
cd joycon-robotics/
ls
make install
ls /usr/src/linux-headers-6.1.83
make install --kernelsourcedir /usr/src/linux-headers-6.1.83
sudo mkdir -p /lib/modules/6.1.83
cd /lib/modules/6.1.83
sudo ln -fs /usr/src/linux-headers-6.1.83 build
sudo ln -fs /usr/src/linux-headers-6.1.83 source


```



