j@j-Latitude-5510:~$ uname -a
lscpu
free -h
lsblk -o NAME,SIZE,TYPE,MOUNTPOINT,MODEL
lspci
lsusb
sudo dmidecode -t system -t baseboard -t memory
sudo hwinfo --short
Linux j-Latitude-5510 6.17.0-19-generic #19~24.04.2-Ubuntu SMP PREEMPT_DYNAMIC Fri Mar  6 23:08:46 UTC 2 x86_64 x86_64 x86_64 GNU/Linux
Architecture:                x86_64
  CPU op-mode(s):            32-bit, 64-bit
  Address sizes:             39 bits physical, 48 bits virtual
  Byte Order:                Little Endian
CPU(s):                      8
  On-line CPU(s) list:       0-7
Vendor ID:                   GenuineIntel
  Model name:                Intel(R) Core(TM) i5-10210U CPU @ 1.60GHz
    CPU family:              6
    Model:                   142
    Thread(s) per core:      2
    Core(s) per socket:      4
    Socket(s):               1
    Stepping:                12
    CPU(s) scaling MHz:      19%
    CPU max MHz:             4200.0000
    CPU min MHz:             400.0000
    BogoMIPS:                4199.88
    Flags:                   fpu vme de pse tsc msr pae mce cx8 apic sep mtrr pg
                             e mca cmov pat pse36 clflush dts acpi mmx fxsr sse 
                             sse2 ss ht tm pbe syscall nx pdpe1gb rdtscp lm cons
                             tant_tsc art arch_perfmon pebs bts rep_good nopl xt
                             opology nonstop_tsc cpuid aperfmperf pni pclmulqdq 
                             dtes64 monitor ds_cpl vmx est tm2 ssse3 sdbg fma cx
                             16 xtpr pdcm pcid sse4_1 sse4_2 x2apic movbe popcnt
                              tsc_deadline_timer aes xsave avx f16c rdrand lahf_
                             lm abm 3dnowprefetch cpuid_fault epb ssbd ibrs ibpb
                              stibp ibrs_enhanced tpr_shadow flexpriority ept vp
                             id ept_ad fsgsbase tsc_adjust bmi1 avx2 smep bmi2 e
                             rms invpcid mpx rdseed adx smap clflushopt intel_pt
                              xsaveopt xsavec xgetbv1 xsaves dtherm ida arat pln
                              pts hwp hwp_notify hwp_act_window hwp_epp vnmi md_
                             clear flush_l1d arch_capabilities
Virtualization features:     
  Virtualization:            VT-x
Caches (sum of all):         
  L1d:                       128 KiB (4 instances)
  L1i:                       128 KiB (4 instances)
  L2:                        1 MiB (4 instances)
  L3:                        6 MiB (1 instance)
NUMA:                        
  NUMA node(s):              1
  NUMA node0 CPU(s):         0-7
Vulnerabilities:             
  Gather data sampling:      Vulnerable
  Ghostwrite:                Not affected
  Indirect target selection: Mitigation; Aligned branch/return thunks
  Itlb multihit:             KVM: Mitigation: Split huge pages
  L1tf:                      Not affected
  Mds:                       Not affected
  Meltdown:                  Not affected
  Mmio stale data:           Mitigation; Clear CPU buffers; SMT vulnerable
  Old microcode:             Not affected
  Reg file data sampling:    Not affected
  Retbleed:                  Mitigation; Enhanced IBRS
  Spec rstack overflow:      Not affected
  Spec store bypass:         Mitigation; Speculative Store Bypass disabled via p
                             rctl
  Spectre v1:                Mitigation; usercopy/swapgs barriers and __user poi
                             nter sanitization
  Spectre v2:                Mitigation; Enhanced / Automatic IBRS; IBPB conditi
                             onal; PBRSB-eIBRS SW sequence; BHI SW loop, KVM SW 
                             loop
  Srbds:                     Mitigation; Microcode
  Tsa:                       Not affected
  Tsx async abort:           Not affected
  Vmscape:                   Mitigation; IBPB before exit to userspace
               total        used        free      shared  buff/cache   available
Mem:            15Gi       6.2Gi       4.5Gi       813Mi       5.4Gi       9.0Gi
Swap:          4.0Gi       1.1Gi       2.9Gi
NAME          SIZE TYPE MOUNTPOINT                          MODEL
loop0           4K loop /snap/bare/5                        
loop1        55.5M loop /snap/core18/2979                   
loop2        63.8M loop /snap/core20/2717                   
loop3          74M loop /snap/core22/2339                   
loop4        55.5M loop /snap/core18/2999                   
loop5       516.2M loop /snap/gnome-42-2204/226             
loop6        91.7M loop /snap/gtk-common-themes/1535        
loop7        66.8M loop /snap/core24/1499                   
loop8        18.5M loop /snap/firmware-updater/212          
loop9       206.8M loop /snap/flutter/149                   
loop10      606.1M loop /snap/gnome-46-2404/153             
loop11      254.9M loop /snap/firefox/7967                  
loop12      531.4M loop /snap/gnome-42-2204/247             
loop13       63.8M loop /snap/core20/2769                   
loop14         74M loop /snap/core22/2411                   
loop15       10.8M loop /snap/snap-store/1270               
loop17       40.3M loop /snap/pinta/90                      
loop18       66.8M loop /snap/core24/1587                   
loop19       16.4M loop /snap/firmware-updater/223          
loop20        395M loop /snap/mesa-2404/1165                
loop21       40.3M loop /snap/pinta/86                      
loop22       48.1M loop /snap/snapd/25935                   
loop23       48.4M loop /snap/snapd/26382                   
loop24        576K loop /snap/snapd-desktop-integration/343 
loop25        576K loop /snap/snapd-desktop-integration/315 
loop26       15.5M loop /snap/snap-store/1310               
loop27      321.1M loop /snap/vlc/3777                      
loop28      273.5M loop /snap/firefox/8054                  
mmcblk0       117G disk                                     
nvme0n1     476.9G disk                                     NX-512 2280
├─nvme0n1p1     1G part /boot/efi                           
└─nvme0n1p2 475.9G part /                                   
00:00.0 Host bridge: Intel Corporation Comet Lake-U v1 4c Host Bridge/DRAM Controller (rev 0c)
00:02.0 VGA compatible controller: Intel Corporation CometLake-U GT2 [UHD Graphics] (rev 02)
00:04.0 Signal processing controller: Intel Corporation Xeon E3-1200 v5/E3-1500 v5/6th Gen Core Processor Thermal Subsystem (rev 0c)
00:08.0 System peripheral: Intel Corporation Xeon E3-1200 v5/v6 / E3-1500 v5 / 6th/7th/8th Gen Core Processor Gaussian Mixture Model
00:12.0 Signal processing controller: Intel Corporation Comet Lake Thermal Subsytem
00:14.0 USB controller: Intel Corporation Comet Lake PCH-LP USB 3.1 xHCI Host Controller
00:14.2 RAM memory: Intel Corporation Comet Lake PCH-LP Shared SRAM
00:14.3 Network controller: Intel Corporation Comet Lake PCH-LP CNVi WiFi
00:15.0 Serial bus controller: Intel Corporation Serial IO I2C Host Controller
00:15.1 Serial bus controller: Intel Corporation Comet Lake Serial IO I2C Host Controller
00:16.0 Communication controller: Intel Corporation Comet Lake Management Engine Interface
00:17.0 SATA controller: Intel Corporation Comet Lake SATA AHCI Controller
00:19.0 Serial bus controller: Intel Corporation Comet Lake Serial IO I2C Host Controller
00:1c.0 PCI bridge: Intel Corporation Comet Lake PCI Express Root Port #8 (rev f0)
00:1d.0 PCI bridge: Intel Corporation Comet Lake PCI Express Root Port #13 (rev f0)
00:1f.0 ISA bridge: Intel Corporation Comet Lake PCH-LP LPC Premium Controller/eSPI Controller
00:1f.3 Audio device: Intel Corporation Comet Lake PCH-LP cAVS
00:1f.4 SMBus: Intel Corporation Comet Lake PCH-LP SMBus Host Controller
00:1f.5 Serial bus controller: Intel Corporation Comet Lake SPI (flash) Controller
00:1f.6 Ethernet controller: Intel Corporation Ethernet Connection (10) I219-V
01:00.0 Unassigned class [ff00]: Realtek Semiconductor Co., Ltd. RTS525A PCI Express Card Reader (rev 01)
02:00.0 Non-Volatile memory controller: MAXIO Technology (Hangzhou) Ltd. NVMe SSD Controller MAP1202 (DRAM-less) (rev 01)
Bus 001 Device 001: ID 1d6b:0002 Linux Foundation 2.0 root hub
Bus 001 Device 002: ID 0bda:565c Realtek Semiconductor Corp. Integrated_Webcam_HD
Bus 001 Device 003: ID 8087:0026 Intel Corp. AX201 Bluetooth
Bus 002 Device 001: ID 1d6b:0003 Linux Foundation 3.0 root hub
[sudo] password for j: 
# dmidecode 3.5
Getting SMBIOS data from sysfs.
SMBIOS 3.2.0 present.

Handle 0x0001, DMI type 1, 27 bytes
System Information
	Manufacturer: Dell Inc.
	Product Name: Latitude 5510
	Version: Not Specified
	Serial Number: J4K3M53
	UUID: 4c4c4544-0034-4b10-8033-cac04f4d3533
	Wake-up Type: Power Switch
	SKU Number: 09A1
	Family: Latitude

Handle 0x0002, DMI type 2, 15 bytes
Base Board Information
	Manufacturer: Dell Inc.
	Product Name: 08PHDH
	Version: A00
	Serial Number: /J4K3M53/CNCMK0008B0B11/
	Asset Tag: Not Specified
	Features:
		Board is a hosting board
		Board is replaceable
	Location In Chassis: Not Specified
	Chassis Handle: 0x0003
	Type: Motherboard
	Contained Object Handles: 0

Handle 0x0004, DMI type 10, 6 bytes
On Board Device Information
	Type: Video
	Status: Enabled
	Description: "Intel HD Graphics"

Handle 0x0006, DMI type 12, 5 bytes
System Configuration Options
	Option 1: Default string

Handle 0x0007, DMI type 15, 35 bytes
System Event Log
	Area Length: 4 bytes
	Header Start Offset: 0x0000
	Header Length: 2 bytes
	Data Start Offset: 0x0002
	Access Method: Indexed I/O, one 16-bit index port, one 8-bit data port
	Access Address: Index 0x046A, Data 0x046C
	Status: Invalid, Not Full
	Change Token: 0x00000000
	Header Format: No Header
	Supported Log Type Descriptors: 6
	Descriptor 1: End of log
	Data Format 1: OEM-specific
	Descriptor 2: End of log
	Data Format 2: OEM-specific
	Descriptor 3: End of log
	Data Format 3: OEM-specific
	Descriptor 4: End of log
	Data Format 4: OEM-specific
	Descriptor 5: End of log
	Data Format 5: OEM-specific
	Descriptor 6: End of log
	Data Format 6: OEM-specific

Handle 0x000E, DMI type 32, 20 bytes
System Boot Information
	Status: No errors detected

Handle 0x001C, DMI type 16, 23 bytes
Physical Memory Array
	Location: System Board Or Motherboard
	Use: System Memory
	Error Correction Type: None
	Maximum Capacity: 32 GB
	Error Information Handle: Not Provided
	Number Of Devices: 2

Handle 0x001D, DMI type 17, 84 bytes
Memory Device
	Array Handle: 0x001C
	Error Information Handle: Not Provided
	Total Width: 64 bits
	Data Width: 64 bits
	Size: 8 GB
	Form Factor: SODIMM
	Set: None
	Locator: DIMM A
	Bank Locator: Not Specified
	Type: DDR4
	Type Detail: Synchronous
	Speed: 2933 MT/s
	Manufacturer: 0198000080CE
	Serial Number: BE249E40
	Asset Tag: 07241900
	Part Number: KF3200C20S4/8G      
	Rank: 1
	Configured Memory Speed: 2667 MT/s
	Minimum Voltage: 1.2 V
	Maximum Voltage: 1.2 V
	Configured Voltage: 1.2 V
	Memory Technology: DRAM
	Memory Operating Mode Capability: Volatile memory
	Firmware Version: Not Specified
	Module Manufacturer ID: Bank 2, Hex 0x98
	Module Product ID: Unknown
	Memory Subsystem Controller Manufacturer ID: Unknown
	Memory Subsystem Controller Product ID: Unknown
	Non-Volatile Size: None
	Volatile Size: 8 GB
	Cache Size: None
	Logical Size: None

Handle 0x001E, DMI type 17, 84 bytes
Memory Device
	Array Handle: 0x001C
	Error Information Handle: Not Provided
	Total Width: 64 bits
	Data Width: 64 bits
	Size: 8 GB
	Form Factor: SODIMM
	Set: None
	Locator: DIMM B
	Bank Locator: Not Specified
	Type: DDR4
	Type Detail: Synchronous
	Speed: 2933 MT/s
	Manufacturer: 0198000080CE
	Serial Number: AB144DF4
	Asset Tag: 07241900
	Part Number: KF3200C20S4/8G      
	Rank: 1
	Configured Memory Speed: 2667 MT/s
	Minimum Voltage: 1.2 V
	Maximum Voltage: 1.2 V
	Configured Voltage: 1.2 V
	Memory Technology: DRAM
	Memory Operating Mode Capability: Volatile memory
	Firmware Version: Not Specified
	Module Manufacturer ID: Bank 2, Hex 0x98
	Module Product ID: Unknown
	Memory Subsystem Controller Manufacturer ID: Unknown
	Memory Subsystem Controller Product ID: Unknown
	Non-Volatile Size: None
	Volatile Size: 8 GB
	Cache Size: None
	Logical Size: None

Handle 0xF036, DMI type 41, 11 bytes
Onboard Device
	Reference Designation: Onboard - Other
	Type: Other
	Status: Enabled
	Type Instance: 1
	Bus Address: 0000:00:00.0

Handle 0xF037, DMI type 41, 11 bytes
Onboard Device
	Reference Designation: Onboard - Video
	Type: Video
	Status: Enabled
	Type Instance: 1
	Bus Address: 0000:00:02.0

Handle 0xF038, DMI type 41, 11 bytes
Onboard Device
	Reference Designation: Onboard - Other
	Type: Other
	Status: Enabled
	Type Instance: 2
	Bus Address: 0000:00:04.0

Handle 0xF039, DMI type 41, 11 bytes
Onboard Device
	Reference Designation: Onboard - Other
	Type: Other
	Status: Enabled
	Type Instance: 3
	Bus Address: 0000:00:08.0

Handle 0xF03A, DMI type 41, 11 bytes
Onboard Device
	Reference Designation: Onboard - Other
	Type: Other
	Status: Enabled
	Type Instance: 4
	Bus Address: 0000:00:12.0

Handle 0xF03B, DMI type 41, 11 bytes
Onboard Device
	Reference Designation: Onboard - Other
	Type: Other
	Status: Enabled
	Type Instance: 5
	Bus Address: 0000:00:14.0

Handle 0xF03C, DMI type 41, 11 bytes
Onboard Device
	Reference Designation: Onboard - Other
	Type: Other
	Status: Enabled
	Type Instance: 6
	Bus Address: 0000:00:14.2

Handle 0xF03D, DMI type 41, 11 bytes
Onboard Device
	Reference Designation: Onboard - Ethernet
	Type: Ethernet
	Status: Enabled
	Type Instance: 1
	Bus Address: 0000:00:14.3

Handle 0xF03E, DMI type 41, 11 bytes
Onboard Device
	Reference Designation: Onboard - Other
	Type: Other
	Status: Enabled
	Type Instance: 7
	Bus Address: 0000:00:15.0

Handle 0xF03F, DMI type 41, 11 bytes
Onboard Device
	Reference Designation: Onboard - Other
	Type: Other
	Status: Enabled
	Type Instance: 8
	Bus Address: 0000:00:15.1

Handle 0xF040, DMI type 41, 11 bytes
Onboard Device
	Reference Designation: Onboard - Other
	Type: Other
	Status: Enabled
	Type Instance: 9
	Bus Address: 0000:00:16.0

Handle 0xF041, DMI type 41, 11 bytes
Onboard Device
	Reference Designation: Onboard - SATA
	Type: SATA Controller
	Status: Enabled
	Type Instance: 1
	Bus Address: 0000:00:17.0

Handle 0xF042, DMI type 41, 11 bytes
Onboard Device
	Reference Designation: Onboard - Other
	Type: Other
	Status: Enabled
	Type Instance: 10
	Bus Address: 0000:00:19.0

Handle 0xF043, DMI type 41, 11 bytes
Onboard Device
	Reference Designation: Onboard - Other
	Type: Other
	Status: Enabled
	Type Instance: 11
	Bus Address: 0000:00:1f.0

Handle 0xF044, DMI type 41, 11 bytes
Onboard Device
	Reference Designation: Onboard - Sound
	Type: Sound
	Status: Enabled
	Type Instance: 1
	Bus Address: 0000:00:1f.3

Handle 0xF045, DMI type 41, 11 bytes
Onboard Device
	Reference Designation: Onboard - Other
	Type: Other
	Status: Enabled
	Type Instance: 12
	Bus Address: 0000:00:1f.4

Handle 0xF046, DMI type 41, 11 bytes
Onboard Device
	Reference Designation: Onboard - Other
	Type: Other
	Status: Enabled
	Type Instance: 13
	Bus Address: 0000:00:1f.5

Handle 0xF047, DMI type 41, 11 bytes
Onboard Device
	Reference Designation: Onboard - Ethernet
	Type: Ethernet
	Status: Enabled
	Type Instance: 2
	Bus Address: 0000:00:1f.6

sudo: hwinfo: command not found
j@j-Latitude-5510:~$ 

j@j-Latitude-5510:~$ sudo lshw -short
H/W path          Device          Class          Description
============================================================
                                  system         Latitude 5510 (09A1)
/0                                bus            08PHDH
/0/0                              memory         64KiB BIOS
/0/1c                             memory         16GiB System Memory
/0/1c/0                           memory         8GiB SODIMM DDR4 Synchronous 29
/0/1c/1                           memory         8GiB SODIMM DDR4 Synchronous 29
/0/40                             memory         256KiB L1 cache
/0/41                             memory         1MiB L2 cache
/0/42                             memory         6MiB L3 cache
/0/43                             processor      Intel(R) Core(TM) i5-10210U CPU
/0/100                            bridge         Comet Lake-U v1 4c Host Bridge/
/0/100/2          /dev/fb0        display        CometLake-U GT2 [UHD Graphics]
/0/100/4                          generic        Xeon E3-1200 v5/E3-1500 v5/6th 
/0/100/8                          generic        Xeon E3-1200 v5/v6 / E3-1500 v5
/0/100/12                         generic        Comet Lake Thermal Subsytem
/0/100/14                         bus            Comet Lake PCH-LP USB 3.1 xHCI 
/0/100/14/0       usb1            bus            xHCI Host Controller
/0/100/14/0/6                     multimedia     Integrated_Webcam_HD
/0/100/14/0/a                     communication  AX201 Bluetooth
/0/100/14/1       usb2            bus            xHCI Host Controller
/0/100/14.2                       memory         RAM memory
/0/100/14.3       wlo1            network        Comet Lake PCH-LP CNVi WiFi
/0/100/15                         bus            Serial IO I2C Host Controller
/0/100/15.1                       bus            Comet Lake Serial IO I2C Host C
/0/100/16                         communication  Comet Lake Management Engine In
/0/100/17                         storage        Comet Lake SATA AHCI Controller
/0/100/19                         bus            Comet Lake Serial IO I2C Host C
/0/100/1c                         bridge         Comet Lake PCI Express Root Por
/0/100/1c/0       mmc0            bus            RTS525A PCI Express Card Reader
/0/100/1c/0/544c  /dev/mmcblk0    disk           125GB USD00
/0/100/1d                         bridge         Comet Lake PCI Express Root Por
/0/100/1d/0       /dev/nvme0      storage        NX-512 2280
/0/100/1d/0/0     hwmon3          disk           NVMe disk
/0/100/1d/0/2     /dev/ng0n1      disk           NVMe disk
/0/100/1d/0/1     /dev/nvme0n1    disk           512GB NVMe disk
/0/100/1d/0/1/1   /dev/nvme0n1p1  volume         1074MiB Windows FAT volume
/0/100/1d/0/1/2   /dev/nvme0n1p2  volume         475GiB EXT4 volume
/0/100/1f                         bridge         Comet Lake PCH-LP LPC Premium C
/0/100/1f/0                       system         PnP device PNP0c02
/0/100/1f/1                       system         PnP device PNP0b00
/0/100/1f/2                       input          PnP device PNP0303
/0/100/1f/3                       generic        PnP device DLL09a1
/0/100/1f/4                       system         PnP device PNP0c02
/0/100/1f/5                       system         PnP device PNP0c02
/0/100/1f/6                       system         PnP device PNP0c02
/0/100/1f/7                       system         PnP device PNP0c02
/0/100/1f.3       card0           multimedia     Comet Lake PCH-LP cAVS
/0/100/1f.3/0     input16         input          HDA Intel PCH Headphone Mic
/0/100/1f.3/1     input17         input          HDA Intel PCH HDMI/DP,pcm=3
/0/100/1f.3/2     input18         input          HDA Intel PCH HDMI/DP,pcm=7
/0/100/1f.3/3     input19         input          HDA Intel PCH HDMI/DP,pcm=8
/0/100/1f.4                       bus            Comet Lake PCH-LP SMBus Host Co
/0/100/1f.5                       bus            Comet Lake SPI (flash) Controll
/0/100/1f.6       eno2            network        Ethernet Connection (10) I219-V
/1                                power          DELL 10X1J03
/2                input0          input          Lid Switch
/3                input1          input          Power Button
/4                input10         input          DELL09A1:00 0488:121F Touchpad
/5                input11         input          DELL09A1:00 0488:121F UNKNOWN
/6                input12         input          Intel HID events
/7                input13         input          Intel HID 5 button array
/8                input14         input          Dell WMI hotkeys
/9                input15         input          Video Bus
/a                input2          input          Sleep Button
/b                input3          input          AT Translated Set 2 keyboard
/c                input5          input          PS/2 Generic Mouse
/d                input9          input          DELL09A1:00 0488:121F Mouse
j@j-Latitude-5510:~$ 

