```
sudo apt install linux-tools-generic hwdata

sudo update-alternatives --install /usr/local/bin/usbip usbip /usr/lib/linux-tools/*-generic/usbip 20


```

```
(py311) PS C:\WINDOWS\system32> usbipd list
Connected:
BUSID  VID:PID    DEVICE                                                        STATE
1-3    8087:0029  英特尔(R) 无线 Bluetooth(R)                                   Shared
1-4    1bcf:2a02  Integrated Webcam                                             Not shared
2-2    30fa:1440  USB 输入设备                                                  Not shared
2-3    187c:0550  USB 输入设备                                                  Not shared
2-4    0d62:3740  WinUSB 设备, USB 输入设备                                     Not shared

Persisted:
GUID                                  DEVICE

把蓝牙适配器连接上wsl
(py311) PS C:\WINDOWS\system32> usbipd attach --wsl --busid 1-3
usbipd: info: Using WSL distribution 'Ubuntu-22.04' to attach; the device will be available in all WSL 2 distributions.
usbipd: info: Loading vhci_hcd module.
usbipd: info: Detected networking mode 'mirrored'.
usbipd: info: Using IP address 127.0.0.1 to reach the host.
WSL usbip: error: Attach Request for 1-3 failed - Device busy (exported)
usbipd: warning: The device appears to be used by Windows; stop the software using the device, or bind the device using the '--force' option.
usbipd: error: Failed to attach device with busid '1-3'.
# windows端关闭蓝牙即可
(py311) PS C:\WINDOWS\system32> usbipd attach --wsl --busid 1-3
usbipd: info: Using WSL distribution 'Ubuntu-22.04' to attach; the device will be available in all WSL 2 distributions.
usbipd: info: Detected networking mode 'mirrored'.
usbipd: info: Using IP address 127.0.0.1 to reach the host.
```

