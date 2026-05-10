## 1. Introduction to RDK Studio  

Have you ever encountered issues when using AI development boards, such as oversized official board images that are difficult to store, sample projects that are hard to locate over time, or the need for external devices during the first login? To address these common challenges  in daily development, D-robotics has innovatively launched RDK Studio, an official developer software,bringing a new era of intelligent robot development! This software lowers the threshold for robot development, enabling even users with no experience to easily get started with RDK series boards. As an innovative tool, it offers all the essential functions for robot development, it has all the functions you can imagine:  

-Manage all RDK Series Boards: RDK Studio fully supports the entire RDK series, making it easy to manage the RDK X3, RDK X5, and RDK Ultra all from one software. Quickly and intuitively check the current status of each board.

-One-Click Flashing and System Upgrades: RDK Studio simplifies board image management, eliminating the hassle of finding and organizing images. With just one click, you can flash or upgrade the system on your board.

-Run Sample Programs with One Click: RDK Studio includes the official NodeHub from D-Robotics, allowing you to run and display sample programs effortlessly. Experience the powerful performance of RDK without any complicated steps.

-Launch Built-In Applications with One Click: Easily start built-in applications like VS Code and Jupyter on the board with a single click, so you can focus more on algorithm development.


## 2. Tutorial for Using RDK Studio  

### 1. Installation of RDK Studio  

Now that we've introduced RDK Studio, let's dive into the tutorial on how to use it! First, we can find the RDK Studio details page in the Software section of the top-right navigation bar of the D-robotics Developer Official Website ([D-robotics Developer Community Homepage](https://developer.d-robotics.cc/)).  

![image-20241231011946197](https://img2023.cnblogs.com/blog/3505969/202412/3505969-20241231011947327-1719050444.png)  

This page contains introductions and download options for RDK Studio. Click the eye-catching <font color="red">"Download RDK Studio"</font> button to navigate to the specific download page. Currently, RDK Studio only supports Windows, but version for Mac OS and Linux versions will come soon in the first quarter of 2025.  

![image-20241231012058850](https://img2023.cnblogs.com/blog/3505969/202412/3505969-20241231012100040-1328317018.png)  

![image-20241231012215390](https://img2023.cnblogs.com/blog/3505969/202412/3505969-20241231012216891-1624806344.png)  


Next, You can choose between two packaging methods. The difference between the User Installer and .zip is that former is a directly downloadable installation package, while the latter is a compressed installation package. If you download via the User Installer, there may be a warning as follows— don't worry and click "仍然保留（Keep）" to proceed.  


![image-20241231012431528](https://img2023.cnblogs.com/blog/3505969/202412/3505969-20241231012432787-889270557.png)  

Next, double-click the downloaded .exe file to automatically install and launch RDK Studio. A shortcut will also be created on the desktop. The default installation path of RDK Studio is "C:\Users\\{User}\AppData\Local\rdk_studio". Since the software does not modify the registry, if you don't want to install it on the C drive, you can directly move the directory to any of your preferred locations.  

![image-20241231014221474](https://img2023.cnblogs.com/blog/3505969/202412/3505969-20241231014223330-200840883.png)  


### 2. Using RDK Studio  

Opening the software, you will see the interface of RDK Studio as follows. Next, we will introduce how to use the software in different scenarios.  

![image-20241231020605367](https://img2023.cnblogs.com/blog/3505969/202412/3505969-20241231041505630-55216625.png)  


### 2.1 Flashing a New Board  

If you’ve just received a new RDK X5 board, open RDK Studio and click the Flashing section on the left. You can see that you can select and connect the device you are about to flash. You can also click the <font color="red">Use Flash Connect (Type-C)</font> button next to X5 to learn more about the Flash Connect mode. The RDK X5 board can only have its system flashed when in Flash Connect mode.  

![image-20241231024350810](https://img2023.cnblogs.com/blog/3505969/202412/3505969-20241231024352793-2099235498.png)  

![image-20241231024839013](https://img2023.cnblogs.com/blog/3505969/202412/3505969-20241231024840606-882520385.png)  

According to official instructions, there are two Type-C ports on the X5: the right port in the picture above is the power port, and the left one is the Flash Connect USB2 port. Insert the SD card into the RDK X5, then use a Type-C data cable to connect the board to your computer, press and hold the power button while powering on the RDK X5, and continue holding it for 3-5 seconds to enter Flash Connect mode. After entering Flash Connect mode, the system will automatically recognize the X5 as a USB drive. Then, return to the flashing interface of RDK Studio and click "Next" to enter the system download configuration interface. On this interface, you can select the system version to download and the download path, etc.  

![image-20241231025448211](https://img2023.cnblogs.com/blog/3505969/202412/3505969-20241231025449865-2073792881.png)  

Next, select to download the latest image and click "Next" to start selecting the flashing path. Choose "/dev/sdb". If no device is displayed when clicking "Next", click the refresh button next to the yellow prompt to re-detect. If no device is detected after refreshing, it means the board has not entered Flash Connect mode, and you need to return to the beginning, press the button again, and power on.  

![image-20241231025521254](https://img2023.cnblogs.com/blog/3505969/202412/3505969-20241231025522574-1971904316.png)  

Then, click "Install" and the software will automatically download and flash the selected image.  

![image-20241231025800980](https://img2023.cnblogs.com/blog/3505969/202412/3505969-20241231025802284-1728877661.png)  

![image-20241231032628828](https://img2023.cnblogs.com/blog/3505969/202412/3505969-20241231032630752-1677053665.png)  

After a short wait, the system will be installed successfully!


### 2.2 Adding an Existing Board  

After completing the system flashing, or if you already have a board with a pre-flashed system, you can add your device on the device management page after powering it on again. RDK supports three device addition methods: Ethernet connection, Flash Connect, and IP address connection (for known IPs). You can choose the corresponding connection method according to your needs.  

![image-20241231032759328](https://img2023.cnblogs.com/blog/3505969/202412/3505969-20241231032801047-45604871.png)  

A newly flashed device can be connected directly via Flash Connect. Click "Next" and you will be asked to select the network device of your board. Simply select the network device connected to the RDK board based on your connection method.  

![image-20241231033030785](https://img2023.cnblogs.com/blog/3505969/202412/3505969-20241231033032230-767577743.png)  

Then, click "Next" and you will be asked to select the login user. You can choose a regular user or the Root user according to your needs. In this example, I choose the Root user.

![image-20241231033225778](https://img2023.cnblogs.com/blog/3505969/202412/3505969-20241231033227541-1618372285.png)  

Next, you will enter the WiFi connection page. Select the WiFi in your current environment and enter the password to connect. You can choose to skip this step.  

![image-20241231033630688](https://img2023.cnblogs.com/blog/3505969/202412/3505969-20241231041451498-211015426.png)  

The final step is to specify the device name, description, and contact information as needed to complete the whole process.  

![image-20241231033744625](https://img2023.cnblogs.com/blog/3505969/202412/3505969-20241231041448306-844098832.png)  

Click "Confirm", and you can see the newly added device in the device management section !

![image-20241231033836377](https://img2023.cnblogs.com/blog/3505969/202412/3505969-20241231041439889-130155801.png)  


### 2.3 Device Management  

After adding a device, you can see the added device on the device management page. The following figure illustrates the basic functions of the page.

![image-20241231034515974](https://img2023.cnblogs.com/blog/3505969/202412/3505969-20241231034517858-5525647.png)  

Click "Add Application" to see the list of applications supported by the current board. Select and download or use them as needed.

![image-20241231034605816](https://img2023.cnblogs.com/blog/3505969/202412/3505969-20241231041433824-151742712.png)  


### 2.4 One-click Startup of Sample Applications  

After adding your device, you can open the sample programs in the left sidebar. Then you can select the device name to run on and perform corresponding operations in the drop-down box. Click "Download Sample" or the corresponding application to immediately experience predefined projects!  

![image-20241231034702723](https://img2023.cnblogs.com/blog/3505969/202412/3505969-20241231041431744-1807077157.png)  


### 3. Uninstalling RDK Studio  

When you no longer need RDK Studio and wish to uninstall it, you can open System Settings, select "Apps" -> "Installed apps", enter "RDK Studio" in the search box to find the application. Click the three-dot menu ("⋯") on the right and select "Uninstall" button to uninstall.  

![image-20241231041320067](https://img2023.cnblogs.com/blog/3505969/202412/3505969-20241231041425887-1178161419.png)
