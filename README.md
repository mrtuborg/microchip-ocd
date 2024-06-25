# microchip-oce
Utility to provide On-Chip-Debugging and firmware flashing trough the command line or any other configurable IDEs

## Picoce Script Usage Guide

The Picoce script is designed to manage Docker containers for MPLAB tools, facilitating the execution of MPLAB tools (`ipe`, `mdb`, or a `shell`) within a Docker environment. It ensures single-instance execution through locking, logs its operations, and handles cleanup efficiently.

## Table of Contents
- [Prerequisites](#prerequisites)
- [Usage](#usage)
- [Arguments](#arguments)
- [Options](#options)
- [HOW-TO: Firmware UPLOAD](#how-to-firmware-upload)
- [HOW-TO: Run On-Chip-Debugging for the prepared firmware](#how-to-run-on-chip-debugging-for-the-prepared-firmware)
- [Features](#features)
- [Cleanup and Exit](#cleanup-and-exit)

### Prerequisites
- Docker
- Python 3.x

### Usage

Run the script from the command line with the following syntax:

```shell
python picoce.py mdb [configuration_file] [firmware_elf_file] [options]
python picoce.py ipe [firmware_hex_file] [options]
```

### Arguments
 * **tool**: The MPLAB tool to use (ipe, mdb, shell).
 * **firmware_hex_file**: The binary file in HEX format to upload for ipe utility
 * **configuration_file**, **firmware_elf_file**: MDB requires a configuration file to specify the target device, programmer, and communication and firmware file in ELF-format.


### Options
 * --image-name: Docker container name (default: mplabx-container).
 * --image-tag: Docker image tag (default: v6.20.1).
 * --lock_duration: Process lock duration in seconds (default: 0). Makes possible to block OCD adapter to be used by another process.

### HOW-TO: Firmware UPLOAD
Make sure that the target device is connected to the computer and the ICD/OCD programmer is connected to the target device.
To upload the software to the target device, you need to run the following command:
```shell
 build$ ./picoce.py ipe firmware_app.hex
```

You will get following output from the IPE utility:
```shell
Starting version 247.3-7+deb11u4
DFP Version Used : PIC32MK-GP_DFP,1.6.144,Microchip
*****************************************************
Connecting to MPLAB ICD 4
Currently loaded versions:
Application version...........02.01.00
Boot version..................01.00.00
FPGA version..................01.00.14
PCB version...................3
Script version................00.06.71
Script build number...........74cdf38a4d
Tool pack version ............2.3.1809
Target voltage detected
Target device PIC32MK1024GPK064 found.
Device Revision Id  = 0xB2
Device Id = 0x8b0e053
Num0 = 003a0046
Num1 = 50505907
*****************************************************
Calculating memory ranges for operation...
Erasing...
The following memory area(s) will be programmed:
program memory: start address = 0x1d080000, end address = 0x1d0807ff
program memory: start address = 0x1d081000, end address = 0x1d0aefff
configuration memory
boot config memory
Programming/Verify complete
ICD4 Program Report
2024-05-29, 15:49:05
Device Type:PIC32MK1024GPK064
Program Succeeded.
Operation Succeeded
Lock file removed.
````
If the output is similar to the one above, the software was successfully uploaded to the target device.

### HOW-TO: Run On-Chip-Debugging for the prepared firmware

To debug the software, you need to run the following command:
```
build$ ./picoce.py mdb "mdb_myBoard.conf firmware_app.elf"
```
As an example of mdb_myBoard.conf file you can find in this repository. It contains the information for Microchip Debugger on which target device is used, which programmer is used, and which communication interface is used.

You will see how the debugger is started and the output will be similar to the uploading, but will be finished in debugger console, provided by the Microchip MDP debugging utility:

```shell
>
```

You can use the following commands to control the debugger:
- `run` - start the execution of the software
- `halt` - stop the execution of the software
- `step` - execute the next instruction
- `break` - set the breakpoint
- `continue` - continue the execution of the software
- `quit` - exit the debugger

For any additional information about the debugger, please refer to the [Microchip MDB documentation](https://onlinedocs.microchip.com/pr/GUID-EB8052B1-A215-4F5C-BAE4-F2871856E4B4-en-US-2/index.html?GUID-4AF0D947-8290-442B-89A9-C2AFD1235234).



# Features
 * Lock Mechanism: Prevents concurrent script execution.
 * Logging: Operations are logged for troubleshooting.
 * Signal Handling: Graceful exit and cleanup on signals.
 * Docker Execution: Runs MPLAB tools in a Docker container.

# Cleanup and Exit
The script releases its lock file upon exit or interruption, ensuring clean subsequent runs.

For more details, check the operation logs in `~/.picoce.log.`