

wsl需要编译header



```
$ cat /proc/version
Linux version 6.6.87.2-microsoft-standard-WSL2 (root@439a258ad544) (gcc (GCC) 11.2.0, GNU ld (GNU Binutils) 2.37) #1 SMP PREEMPT_DYNAMIC Thu Jun  5 18:30:46 UTC 2025
Linux version 6.6.87.2-microsoft-standard-WSL2 (xxx@xxx) (gcc (Ubuntu 11.4.0-1ubuntu1~22.04.2) 11.4.0, GNU ld (GNU Binutils for Ubuntu) 2.38) #1 SMP PREEMPT_DYNAMIC Fri Oct  3 18:14:58 CST 2025


wget https://github.com/microsoft/WSL2-Linux-Kernel/archive/refs/tags/linux-msft-wsl-6.6.87.2.tar.gz
tar -zxvf linux-msft-wsl-6.6.87.2.tar.gz
cd WSL2-Linux-Kernel-linux-msft-wsl-6.6.87.2/
sudo apt-get update
sudo apt install build-essential flex bison dwarves libssl-dev libelf-dev cpio qemu-utils
make menuconfig KCONFIG_CONFIG=Microsoft/config-wsl
make -j$(nproc) KCONFIG_CONFIG=Microsoft/config-wsl
make -j$(nproc) INSTALL_MOD_PATH="$PWD/modules" modules_install
sudo ./Microsoft/scripts/gen_modules_vhdx.sh "$PWD/modules" $(make -s kernelrelease) modules.vhdx


```

存放于文件夹WSL2-Linux-Kernel-linux-msft-wsl-6.6.87.2/modules.vhdx

生成的内核Kernel位于WSL2-Linux-Kernel-linux-msft-[wsl](https://so.csdn.net/so/search?q=wsl&spm=1001.2101.3001.7020)-6.6.87.2/arch/x86/boot/bzImage
