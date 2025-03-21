<div align="center">
    <img src="https://github.com/user-attachments/assets/099b80dd-a6a5-4a14-940f-06401dadf024" width="200" alt="GARDENs logo" />
   <h1>MIS MCU source</h1>
    
🌏
English | [**日本語**](https://github.com/CIT-GARDENs-Organization/MIS_MCU_source/blob/main/README.ja.md)

</div>

## Summary 
This repository provides the foundation for the source code to be implemented in the MIS MCU of GARDENs.
By branching out from this base to each mission, the following objectives are achieved.

- **Improved development efficiency**  
- **Clarification of responsibilities**  
- **Streamlined testing and operations through unified behavior**  

---

## Implementation Method  
1. **Line 19** of main.py → Set SELF_DEVICE_ID to the Device ID of your MIS MCU.
   | Devie ID  |Device Name|
   |:------    | :-------- |
   |6          | APRS PIC  |
   |7          | CAM MCU   |
   |8          | CHO MCU   |
   |9          | SATO PIC  |
   |A          | NAKA PIC  |
   |B          | BHU PIC   |
3. **Line 20** of main.py → Set SERIAL_PORT to the serial port name as a string.
   - If set to None, automatic detection and CLI selection functionality will be available. 
4. DataCopy.py → Enumerate **the types of data to be stored and their addresses** in the class variables of the DataType class.
   - Must comply with the **IICD memory map**.
5. Mission.py → In the MissionExecute class, define **command IDs and their corresponding functions** in _mission_list.  
6. Mission.py → Implement **the behavior of the corresponding functions** within the MissionExecute class.  

---

## Constraints & Others  

### **Files and Methods That Must Not Be Modified**  
- The processing in main.py ・ DataCopy.py must not be modified (`print()` functions can be freely added or removed).
- The execute_mission() method in the ExecuteMission class of Mission.py.

### **SMF Data Storage Rules**  
- Append to smf_data in the MissionExecute class.
  
python
  ex) self._smf_data.append(DataType.EXAMPLE_PHOTO_THUMB, ["./photo/thumb/0.png", "./photo/thumb/1.png"])
  ex) self._smf_data.append(DataType.EXAMPLE_PHOTO_THUMB, path_list)

### Device Continuation Function
- The MIS MCU is designed to shut down after executing the mission and copying data to the SMF.
- If there is a need to **keep the device running for a certain period after mission execution**, return the **duration in seconds** as an int from the mission function.
- If this feature is not used, do not write a return statement.

---

## Upcoming Updates (Assigned to: GARDENs)
1. Migration from print to syslog
   - Currently, print is used to monitor operations, but during satellite testing and operations, real-time monitoring is not possible. Therefore, in previous models, the syslog module was used to output logs externally.
   - This will follow the same approach as before, but since the specific output format has not yet been defined, we will transition to using syslog for unified output once the format is decided.
   - Once the rules are finalized, they will be communicated to each respective organization.
2. Implementation of the SMF Copy Function
   - Currently, the SMF copy is simulated with the following print output, but in the future, the actual functionality will be developed, and a unified SMF copy function will be implemented.
```
Start data copy thread
Start copy to SMF
        -> Data type: EXAMPLE_PHOTO_THUMB
                -> ./photo/thumb/0.png
                -> ./photo/thumb/1.png
                -> ./photo/thumb/2.png
                -> ./photo/thumb/3.png
End copy to SMF
```

## Additional Notes
To deepen the understanding of the operation, three sample missions and the BOSS PIC simulator software have been provided.
Feel free to try running them before starting the development of each mission.

[BOSS PIC simulater](https://github.com/CIT-GARDENs-Organization/BOSS_PIC_simulator)

| CMD ID     | Used Parameters         | Explanation                                                                                |
|:-----------|:------------            |:------------                                                                               |
| 00         | XX __ __ __ __ __ __ __ | Wait for X seconds.                                                                        |
| 01         | _X __ __ __ __ __ __ __ | Save X thumbnail images.                                                                   |
| 02         | XX XX __ __ __ __ __ __ |Save one thumbnail image and keep the device running for X seconds after mission execution. |
