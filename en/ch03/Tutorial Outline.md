
# Author's Words

First of all, I am deeply honored to participate in the AI + Hardware Open Source Tutorial Project. I am primarily responsible for writing and sharing tutorials on hardware circuit design, with a focus on PCB design and drawing. This course will not specifically cover digital or analog circuit theory. In future tutorials, I will be using some of my own projects and the OriginBot car, a collaboration between Sweet Potato Robot and Guyuejv, as examples to explain the concepts.

For beginner robot developers, using prefabricated hardware development boards for learning projects offers excellent cost-effectiveness in terms of both time and money. However, commercial off-the-shelf development boards may not meet the diverse needs of specific projects or may contain unnecessary functionalities. In these cases, we need to design hardware circuits that are tailored to the specific requirements of our projects.

During project development, breadboards and flying wires can be used for project verification. However, PCB design can integrate all jumper wires directly into the circuit board, making the debugging and software verification process more efficient. At this time, the PCB is mainly in the form of plug-in components. Once the project’s testing is complete, and its functions are finalized, the PCB design shifts to using Surface Mount Devices (SMD). This design offers a more optimized structure, better performance, and is easier to mass-produce.

In this course, the PCB design is done using the domestic software Jialichuang EDA (LCEDA). This software is free to use and very user-friendly. Additionally, PCBs with dimensions of up to 10cm x 10cm designed using this software can be fabricated for free as a prototype. I will not go into more details about the advantages of this software here.

Due to my limited technical expertise, I welcome feedback and suggestions for any issues found in the tutorial. Let’s make progress together. Feel free to contact me at: 13503388923.

---

# Software Download and Installation

## 1. Download URL

[Download Jialichuang EDA (LCEDA)](https://lceda.cn/page/download?src=index)

It is recommended to download the EDA Professional version, as it offers more powerful functions compared to the standard version.
*Note: You will need to register for a Jialichuang account in advance.*

## 2. Installation Tutorial and Usage Instructions

[Installation Guide](https://prodocs.lceda.cn/cn/faq/client/index.html)

## 3. Tutorial PDF Download

[LCEDA Pro Tutorial PDF](https://image.lceda.cn/files/LCEDA-Pro-Tutorial_v2.2.x.pdf)

---

# Project Case 1

This is a personal project where I share my design and production ideas. There is no need to replicate it exactly, nor do I recommend doing so. The second project will guide you in making an OriginBot underlying driver board (plug-in version), and the third project, if time permits, will involve making an OriginCar underlying driver board.

## 1. Project Introduction

This project involves an underlying driver board that I developed for my own robot. It receives CAN signals from the upper computer, processes these signals, and then controls the motor’s operation.

## 2. Composition of Hardware Circuit

This PCB consists of the following components:

* STM32F103 minimum system board
* Buck module
* CAN signal module
* XT30 power input interface
* Power switch
* Buzzer
* Motor driver module
* OLED display
* Motor interface
* Other reserved interfaces

## 3. Assigning Pins and Determining Connection Relationships

Before designing the PCB and drawing the schematic diagram, my practice is to list the footprints of each module and determine the pin connection relationships according to their respective definitions. I use the STM32F103 and will assign the pins based on the pin definitions to facilitate program development and I/O port usage.

### 1) Hardware Selection

This content cannot be displayed outside the Feishu document at the moment.

### 2) Pin Assignment

Hardware selection is done based on product functions, followed by pin assignment, which reflects the combination of software and hardware.
\[Project 1 Pin Assignment Table] (Click the blue font to open the pin assignment table)

When assigning pins, please follow these guidelines:

* **Avoid Pin Conflicts:** Prioritize pins with primary functions, then consider the multiplexing capabilities of pins.
* **Assign Special Function Pins First:** Focus on pins for serial communication (RX, TX), CAN communication, PWM timer pins, and encoder signal reading.
* **Consider Pin Location:** Arrange pins on the minimum system board in a way that minimizes future wiring obstacles.
* **Ordinary IO Pins:** These can be roughly assigned first, with re-assignment done based on the difficulty of the circuit when drawing the schematic diagram.

## 4. Drawing the Schematic Diagram

### 1) Select the Appropriate Size of Drawing Paper

Choose the size of the drawing paper based on the number of components. You can select the unit of the drawing paper as mm according to personal preferences.

### 2) Place Components

Using the pin assignment table, select components from the component library and place them in appropriate positions in the schematic. I prefer to start by placing the minimum system board first.

Click on the 'Common Library' on the left side of the schematic interface to select common components and development boards directly.

Click "Place" in the top menu bar, and then select "Device · Reuse Module" to pick the corresponding module.

### 3) Draw Network Labels and Wires

After placing the components, label the network on each pin to indicate its functional definition. Simultaneously, connect some components with wires.

### 4) Draw Short-Circuit Marks

Short-circuit marks are used to connect the pins of two different modules together.

### 5) Verify the Schematic Diagram

* **Check for Accuracy:** Ensure that the schematic is drawn correctly and that all components are placed according to the pin assignment table (assuming the table itself is correct).
* **Perform DRC Check:** The DRC (Design Rule Check) can help verify that the schematic adheres to the design rules.

### 6) Project 1 Schematic Diagram

## 5. Drawing the PCB

### 1) Convert the Schematic Diagram to PCB

Click "Design" in the top menu bar, and select "Update/Convert Schematic to PCB." After conversion, the components will be placed randomly on the PCB.

### 2) Draw the Board Frame

The board frame defines the outer shape and size of the PCB. For complex shapes, they can be drawn using drawing software, saved as DXF files, and then imported into Jialichuang. For square shapes, it's recommended to add small fillets to the frame.

### 3) Layout Component Positions

Position each component on the PCB and layout the interfaces accordingly.

### 4) Connect the Wires

* **Avoid Acute Angles and Right Angles:** Trace connections should not have sharp corners.
* **Trace Width:** This should depend on the specific requirements, such as voltage, current, and impedance.
* **Minimize Vias:** Try to avoid vias for signal lines as much as possible.

### 5) Draw the Silkscreen

Silkscreen functions like comments in code. It indicates the position, function, and pin definition of components on the PCB.

### 6) Add Teardrops and Copper Pouring

When performing copper pouring, cover both the top and bottom layers, but avoid areas like antennas or crystals. These regions should not have copper poured over them.

### 7) View the 3D Simulation

### 8) Export Files and Get Coupons for Proofing

* **Export Board-Making Files**
* **Download and Log In to the Order Assistant:** [Download here](https://www.jlc.com/portal/appDownloadsWithConfig.html)
* **Get Coupons:** Go to the User Center / Coupon Center / Free Coupon Collection menu.
* **Place the Order:** Click to place an order, import the board-making files, and select the corresponding parameters according to the guidance. Use FR4 as the board material, with a standard thickness of 1.6mm. Other parameters can be chosen freely, and paid services will be clearly indicated.

#### 9) Project Engineering Files

\[Click here for access to the engineering files]

---

# Subsequent Updates

Future articles will continue to be updated in the form of Feishu Cloud Documents, and the document materials used in the tutorials will also be uploaded to GitHub and Feishu Cloud Documents.

**Feishu Cloud Document update address:** [Update Link](https://ccnkcsofi4yc.feishu.cn/wiki/Dbd9wGgeOikcLyk8YWkcKvb7n5m?from=from_copylink)


