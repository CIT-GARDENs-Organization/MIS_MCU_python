<div align="center">
<img src="https://github.com/user-attachments/assets/099b80dd-a6a5-4a14-940f-06401dadf024" width="200" alt="GARDENs logo" />
<h1>MIS MCU source code<br>(Python)</h1>

English | [**Japanese**](https://github.com/CIT-GARDENs-Organization/MIS_MCU_python/blob/main/docs/README.ja.md)
</div>

## Summary 
This repository provides the foundation for the python source code to be implemented in the MIS MCU of GARDENs.
By branching out from this base to each mission, the following objectives are achieved.

- **Improved development efficiency**  
- **Clarification of responsibilities**  
- **Streamlined testing and operations through unified behavior**  


## How to implement a mission
1. `main.py` **Line 19** → Set `SELF_DEVICE_ID` to the Device ID of your MIS MCU
   - Refer to [**IICD memory map**](https://github.com/CIT-GARDENs-Organization/MIS_MCU_source/blob/main/docs/memory_map.png)
2. `main.py` **Line 20** → Enter the serial port name in `SERIAL_PORT` as a string
   - If `None`, automatic acquisition and CLI selection functions are available
3. `SmfQueue.py` → List the **type of data to be saved, address, and mission flag** in the class variable of the `DataType` class
   - Comply with [**IICD memory map**](https://github.com/CIT-GARDENs-Organization/MIS_MCU_source/blob/main/docs/memory_map.png)
4. `Mission.py` → Write **command ID and corresponding function** in `_mission_list` of `Mission` class
5. `Mission.py` → Implement **mission method** in `Mission` class

## Restrictions & Others
### **Rules for saving SMF data**
- The name of the file to be saved should be an arbitrary string, an underscore (`_`), and three 2-digit numbers with zeros padded with underscores.

``` txt
save fine name example
- OK)
   - photo_00_01_00.png
   - 0D_00_00.bin
   - _00_FF_00
- NG)
   - photo_00_01.png // Missing digit
   - binary_00_0D_0.bin // Missing digit
   - data00_FF_00.bin // Missing underscore
```
- 
   - The first field is the number of times the mission was performed.
   - The second field is the number of files generated for each mission.
   - The third field is the cutout location for cutout photos.
   - For files that are not photos or are not photos, the third field is fixed at `00`.
   - **If the format is not followed, the header will be `FF FF FF`.**
   - **There is no problem on the satellite even if the above is not followed, but please note that if the format is not correct, it may not be possible to smoothly restore the data with the GARDENs ground station software that will be implemented in the future.**
- The photo to be saved is `append()` to `smf_data` of the `MissionExecute` class.
```py
- ex)
   - self._smf_data.append(DataType.EXAMPLE_PHOTO_THUMB, ["./photo/thumb/0.png", "./photo/thumb/1.png"])
   - self._smf_data.append(DataType.EXAMPLE_PHOTO_THUMB, path_list)
```


## Future updates (Worker: GARDENs)
1. Transition from print to syslog
   - Currently, print is used to monitor operations, but real-time monitoring is not possible during satellite testing and operation, so in past satellites, logs were output externally using the syslog module.
   - This will be followed this time as well, but since no specific output format has been determined, we will transition to syslog, which outputs all data in a unified format, as soon as it is decided.
   - Once the rules are decided, we will notify each organization.


## Additional Notes
1. I created a development function `DevReadData` to read saved photos from SMF, so please use it if you want to check the contents of SMF.

2. To deepen the understanding of the operation, three sample missions and the BOSS PIC simulator software have been provided.Feel free to try running them before starting the development of each mission.

[BOSS PIC simulater](https://github.com/CIT-GARDENs-Organization/BOSS_PIC_simulator)

| CMD ID     | Used Parameters         | Explanation                                                                                |
|:-----------|:------------            |:------------                                                                               |
| 00         | XX __ __ __ __ __ __ __ | Wait for X seconds.                                                                        |
| 01         | _X __ __ __ __ __ __ __ | Take Xs images.                                                                   |
